import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from dotenv import load_dotenv
from fastapi import FastAPI

from notification_service.consumer import consume_forever
from notification_service.hub import Hub

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://techqueue:techqueue@localhost:5672/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Потребитель очереди и Hub живут в одном процессе и одном цикле событий: реестр сеансов в памяти."""
    app.state.hub = Hub()
    consumer = asyncio.create_task(consume_forever(RABBITMQ_URL, app.state.hub))
    try:
        yield
    finally:
        consumer.cancel()
        with suppress(asyncio.CancelledError):
            await consumer


app = FastAPI(title="Notification Service", lifespan=lifespan)
