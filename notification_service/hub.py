from fastapi import WebSocket, WebSocketDisconnect


class Hub:
    """Точка доставки уведомлений подключённым клиентам."""

    def __init__(self):
        self.sessions: dict[int, set[WebSocket]] = {}

    def connect(self, user_id, websocket):
        self.sessions.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id, websocket):
        sockets = self.sessions.get(user_id)
        if sockets is not None:
            sockets.discard(websocket)
            if not sockets:
                del self.sessions[user_id]

    async def send(self, user_id, notice):
        """Отправляет уведомление всем сеансам пользователя и возвращает их число."""
        delivered = 0
        for websocket in tuple(self.sessions.get(user_id, ())):
            try:
                await websocket.send_json(notice)
            except (OSError, RuntimeError, WebSocketDisconnect):
                self.disconnect(user_id, websocket)
            else:
                delivered += 1
        return delivered
