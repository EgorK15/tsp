from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from api.routers import auth, categories, deals, requests, users

app = FastAPI(title="ТехОчередь")

for router in [auth.router, users.router, categories.router, deals.router, requests.router]:
    app.include_router(router)


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Нарушено ограничение БД: " + str(exc.orig).split("\n")[0]})


@app.get("/ping")
def ping():
    return {"status": "ok"}
