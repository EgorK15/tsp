import logging
import os
import queue
import threading

import pika
from dotenv import load_dotenv

from events.contract import BINDING, DEAD_EXCHANGE, DEAD_QUEUE, EXCHANGE, QUEUE, QUEUE_ARGUMENTS

logger = logging.getLogger(__name__)
# pika пишет каждый шаг подключения; о сбоях сообщает сам публикатор.
logging.getLogger("pika").setLevel(logging.CRITICAL)


def declare_topology(channel):
    """Exchange, очередь сервиса уведомлений и очередь отклонённых сообщений; повторное объявление ничего не меняет."""
    channel.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    channel.exchange_declare(DEAD_EXCHANGE, exchange_type="fanout", durable=True)
    channel.queue_declare(DEAD_QUEUE, durable=True)
    channel.queue_bind(DEAD_QUEUE, DEAD_EXCHANGE)
    channel.queue_declare(QUEUE, durable=True, arguments=QUEUE_ARGUMENTS)
    channel.queue_bind(QUEUE, EXCHANGE, routing_key=BINDING)


class EventPublisher:
    """Публикует события в RabbitMQ из своего потока: запрос не ждёт брокер, при сбое отправка повторяется."""

    def __init__(self, url, retry_delay=2.0, max_events=10_000):
        self.parameters = pika.URLParameters(url)
        self.parameters.connection_attempts = 1
        self.parameters.socket_timeout = 3
        self.retry_delay = retry_delay
        self.events = queue.Queue(maxsize=max_events)
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._run, name="event-publisher", daemon=True)
        self.connection = None
        self.channel = None

    @classmethod
    def from_env(cls):
        load_dotenv()
        return cls(os.getenv("RABBITMQ_URL", "amqp://techqueue:techqueue@localhost:5672/"))

    def start(self):
        self.thread.start()
        return self

    def publish(self, notification_event, request_id=None):
        try:
            self.events.put_nowait((notification_event, request_id))
        except queue.Full:
            logger.error("event dropped, buffer is full: notification_id=%s", notification_event.notification_id)

    def close(self, timeout=5.0):
        """Отправляет накопленное, но ждёт не дольше timeout, затем поток закрывает соединение."""
        self.stopping.set()
        self.thread.join(timeout)

    def _run(self):
        try:
            self._connect()
        except (pika.exceptions.AMQPError, OSError) as exc:
            logger.warning("rabbitmq unavailable at start, will retry on first event: %r", exc)
        item = None
        while True:
            if item is None:
                try:
                    item = self.events.get(timeout=1)
                except queue.Empty:
                    if self.stopping.is_set():
                        break
                    self._keepalive()
                    continue
            if self._send(*item):
                item = None
            elif self.stopping.is_set():
                logger.error("rabbitmq unavailable on shutdown, %d events not published", self.events.qsize() + 1)
                break
            else:
                self.stopping.wait(self.retry_delay)
        self._disconnect()

    def _send(self, notification_event, request_id):
        routing_key = notification_event.routing_key
        try:
            if self.channel is None or not self.channel.is_open:
                self._connect()
            self.channel.basic_publish(
                EXCHANGE, routing_key, notification_event.model_dump_json().encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=str(notification_event.notification_id),
                    headers={"x-request-id": request_id or "-"},
                ),
                mandatory=True,
            )
        except pika.exceptions.UnroutableError:
            logger.error("event=%s notification_id=%s has no queue, dropped",
                         routing_key, notification_event.notification_id)
            return True
        except (pika.exceptions.AMQPError, OSError) as exc:
            logger.warning("rabbitmq unavailable, retry in %.0fs: %r", self.retry_delay, exc)
            self._disconnect()
            return False
        logger.info("published event=%s notification_id=%s user_id=%s request_id=%s", routing_key,
                    notification_event.notification_id, notification_event.user_id, request_id or "-")
        return True

    def _connect(self):
        self.connection = pika.BlockingConnection(self.parameters)
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()
        declare_topology(self.channel)
        logger.info("connected to rabbitmq %s:%s", self.parameters.host, self.parameters.port)

    def _keepalive(self):
        # Пока событий нет, соединение всё равно обслуживает heartbeat, иначе брокер его закроет.
        if self.connection is not None and self.connection.is_open:
            try:
                self.connection.process_data_events(time_limit=0)
            except (pika.exceptions.AMQPError, OSError):
                self._disconnect()

    def _disconnect(self):
        connection, self.connection, self.channel = self.connection, None, None
        if connection is not None and connection.is_open:
            try:
                connection.close()
            except (pika.exceptions.AMQPError, OSError):
                pass
