import logging
import os
from contextlib import asynccontextmanager
from uuid import uuid4

import grpc
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from api.routers import auth, categories, dashboard, deals, notifications, requests, settings, users
from load_service.client import LoadClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

GRPC_ERRORS = {
    grpc.StatusCode.UNAVAILABLE: (503, "Сервис загрузки недоступен"),
    grpc.StatusCode.DEADLINE_EXCEEDED: (504, "Сервис загрузки не ответил вовремя"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Один клиент сервиса загрузки на воркер: канал открывается при старте и закрывается при остановке."""
    app.state.load_client = LoadClient.from_env()
    try:
        yield
    finally:
        app.state.load_client.close()


app = FastAPI(title="ТехОчередь", root_path=os.getenv("ROOT_PATH", ""), lifespan=lifespan)

for router in [auth.router, users.router, categories.router, deals.router, requests.router,
               dashboard.router, settings.router, notifications.router]:
    app.include_router(router)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    request.state.trace_id = uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.trace_id
    return response


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Нарушено ограничение БД: " + str(exc.orig).split("\n")[0]})


@app.exception_handler(grpc.RpcError)
def grpc_error_handler(request: Request, exc: grpc.RpcError):
    status_code, detail = GRPC_ERRORS.get(exc.code(), (502, "Ошибка сервиса загрузки"))
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.get("/ping")
def ping():
    return {"status": "ok"}
