import asyncio
import logging
from functools import partial

import aio_pika
from pydantic import ValidationError

from events.contract import BINDING, DEAD_EXCHANGE, DEAD_QUEUE, EXCHANGE, QUEUE, QUEUE_ARGUMENTS, NotificationEvent
from notification_service.messages import render

logger = logging.getLogger(__name__)
# Библиотеки пишут трейсбек на каждый разрыв; о потере и восстановлении соединения сообщают колбэки ниже.
logging.getLogger("aiormq").setLevel(logging.CRITICAL)
logging.getLogger("aio_pika").setLevel(logging.CRITICAL)

PREFETCH = 10


async def declare_topology(channel):
    """Та же топология, что объявляет публикатор: кто бы ни подключился первым, очередь уже есть."""
    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    dead_exchange = await channel.declare_exchange(DEAD_EXCHANGE, aio_pika.ExchangeType.FANOUT, durable=True)
    dead_queue = await channel.declare_queue(DEAD_QUEUE, durable=True)
    await dead_queue.bind(dead_exchange)
    queue = await channel.declare_queue(QUEUE, durable=True, arguments=QUEUE_ARGUMENTS)
    await queue.bind(exchange, routing_key=BINDING)
    return queue


async def handle(message, hub):
    request_id = (message.headers or {}).get("x-request-id", "-")
    try:
        event = NotificationEvent.model_validate_json(message.body)
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, error["loc"])) or "body" for error in exc.errors())
        logger.error("rejected message_id=%s request_id=%s, invalid: %s", message.message_id, request_id, fields)
        await message.reject(requeue=False)
        return
    notice = render(event)
    try:
        sessions = await hub.send(event.user_id, notice)
    except Exception:
        logger.exception("delivery failed notification_id=%s request_id=%s", event.notification_id, request_id)
        await message.reject(requeue=False)
        return
    await message.ack()
    logger.info("event=%s notification_id=%s user_id=%s sessions=%d request_id=%s text=%s", message.routing_key,
                event.notification_id, event.user_id, sessions, request_id, notice["text"])


def on_close(connection, exc=None):
    if exc is not None and not isinstance(exc, asyncio.CancelledError):
        logger.warning("rabbitmq connection lost, reconnecting: %r", exc)


def on_reconnect(connection):
    logger.info("reconnected to rabbitmq, consuming queue=%s", QUEUE)


async def consume_forever(url, hub, retry_delay=3):
    """Подписка на очередь уведомлений. После первого подключения переподключение берёт на себя connect_robust."""
    while True:
        try:
            connection = await aio_pika.connect_robust(url)
        except (aio_pika.exceptions.AMQPConnectionError, OSError) as exc:
            logger.warning("rabbitmq unavailable, retry in %ds: %r", retry_delay, exc)
            await asyncio.sleep(retry_delay)
            continue
        connection.close_callbacks.add(on_close)
        connection.reconnect_callbacks.add(on_reconnect)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=PREFETCH)
            queue = await declare_topology(channel)
            await queue.consume(partial(handle, hub=hub))
            logger.info("consuming queue=%s", QUEUE)
            await asyncio.Future()
