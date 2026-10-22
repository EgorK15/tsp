# ТехОчередь

Система учёта заявок технического отдела на подготовку коммерческих предложений.
Лабораторные по курсу «Технологии сетевого программирования», группа 6402: Зайцев Виктор, Коршиков Егор.

## ЛР1 — слой работы с БД

PostgreSQL + SQLAlchemy 2.0, миграции через Alembic.

Запуск:

```
docker compose up -d
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python seed.py
python demo.py
```

Вместо докера можно использовать локальный PostgreSQL: создать пользователя и базу `techqueue`
(пароль `techqueue`) или поменять `DATABASE_URL` в `.env`.

`seed.py` очищает таблицы и заливает тестовые данные, `demo.py` прогоняет сценарии работы с БД
и печатает результат в консоль.

## Миграции

В проекте две миграции: `0001` — основные таблицы, `0002` — служебные (`load_snapshots`,
`notifications`, `settings`).

```
alembic history
alembic downgrade -1
alembic upgrade head
```

После `downgrade -1` служебные таблицы удаляются, а пользователи, сделки и заявки остаются.
`seed.py` чистит все таблицы, поэтому перед ним нужно вернуться на `head`.

## ЛР2 — REST API

FastAPI, Pydantic, JWT. Запуск API локально (БД должна быть поднята):

```
uvicorn api.main:app --reload
```

Документация Swagger: http://localhost:8000/docs

Перед запуском в `.env` должны быть `JWT_SECRET` и `JWT_EXPIRE_MINUTES` (см. `.env.example`).

Тестовые пользователи после `seed.py`: `head@techqueue.ru` / `head123`, `ivanova@techqueue.ru` / `manager123`,
`kuznetsov@techqueue.ru` / `spec123`.

### Postman

Коллекция `postman/techqueue.postman_collection.json`, переменная `base_url` — адрес API.
Запросы логина сами сохраняют токен в переменную `token`, остальные запросы его подставляют.
Коллекцию можно прогнать целиком через Runner, перед этим лучше выполнить `python seed.py`.

### Примеры curl

```
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" -d "{\"email\": \"test@techqueue.ru\", \"full_name\": \"Test Testov\", \"password\": \"qwerty1\"}"

curl -X POST localhost:8000/auth/login -d "username=ivanova@techqueue.ru&password=manager123"

curl localhost:8000/auth/me -H "Authorization: Bearer <токен>"

curl localhost:8000/deals -H "Authorization: Bearer <токен>"

curl -X POST localhost:8000/deals -H "Authorization: Bearer <токен>" -H "Content-Type: application/json" -d "{\"title\": \"Cooling tower pumps\", \"client_name\": \"HimProm\", \"amount\": 1500000, \"budget_status\": \"stated\", \"tz_percent\": 30}"
```
