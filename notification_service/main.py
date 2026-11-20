import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from api.security import decode_token
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


@app.websocket("/ws/notifications")
async def notifications(websocket: WebSocket, token: str = ""):
    try:
        user_id = decode_token(token)
    except (KeyError, ValueError, TypeError):
        user_id = None

    await websocket.accept()
    if user_id is None or user_id <= 0:
        await websocket.close(code=4401)
        return

    hub = websocket.app.state.hub
    hub.connect(user_id, websocket)
    try:
        while True:
            if (await websocket.receive())["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(user_id, websocket)
