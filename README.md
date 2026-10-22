# ТехОчередь

Система учёта заявок технического отдела на подготовку коммерческих предложений.
Лабораторные по курсу «Технологии сетевого программирования», группа 6402: Зайцев Виктор, Коршиков Егор.

## ЛР1 — слой работы с БД

PostgreSQL + SQLAlchemy 2.0, миграции через Alembic.

Запуск:

```
docker compose up -d db
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
`kuznetsov@techqueue.ru` / `spec123`, `volkov@techqueue.ru` / `spec123`.

### Запуск в Docker (Gunicorn + Nginx)

```
docker compose up --build -d
docker compose exec api python seed.py
docker compose logs api
```

Поднимаются три сервиса:

- `db` — PostgreSQL, с хоста доступен на порту 5433;
- `api` — FastAPI под Gunicorn с двумя воркерами Uvicorn, при старте применяет миграции, порт 8000;
- `nginx` — обратный прокси на порту 80: `/` отдаёт статическую страницу, `/api/` проксирует в `api`.

Адреса:

- http://localhost/ — статика от Nginx;
- http://localhost/api/docs — Swagger через прокси;
- http://localhost:8000/docs — Swagger напрямую.

Gunicorn под Windows не запускается, поэтому для локальной разработки по-прежнему `uvicorn api.main:app --reload`.

### Эндпоинты заявок, дашборда и уведомлений

| Метод и путь | Кто | Что делает |
|---|---|---|
| `GET /requests?deal_id=&stage=` | все | заявки: head — все, manager — по своим сделкам, specialist — назначенные ему |
| `GET /requests/my` | specialist | «Мои заявки» по приоритету и возрасту |
| `POST /requests` | manager | заявка по своей сделке |
| `GET`, `PATCH`, `DELETE /requests/{id}` | manager сделки, head | specialist может открыть свою заявку и поменять только `result_url` |
| `POST /requests/{id}/stage` | по ролям | смена стадии, тело `{"to": "in_work"}` |
| `GET /requests/{id}/history` | кто видит заявку | история стадий |
| `GET /requests/{id}/suggest` | head | подбор специалистов по компетенции и загрузке |
| `GET /requests/{id}/assignees` | кто видит заявку | исполнители |
| `PUT /requests/{id}/assignees` | head | назначить, тело `{"main_id": 6, "co_ids": [5]}` |
| `DELETE /requests/{id}/assignees/{specialist_id}` | head | снять исполнителя |
| `POST /requests/{id}/reassign` | head | передать роль основного исполнителя, тело `{"main_id": 6}` |
| `GET /dashboard` | head | просрочки, медианы, готовые КП без презентации, загрузка отдела |
| `GET /settings`, `PUT /settings/{key}` | head | нормативы, тело `{"value": ...}` |
| `POST /scheduler/snapshot`, `POST /scheduler/check-overdue` | head | ручной запуск задач Планировщика |
| `GET /notifications?unread=true`, `POST /notifications/{id}/read` | все | свои уведомления |

### Postman

Коллекция `postman/techqueue.postman_collection.json`, переменная `base_url` — адрес API:
`http://localhost:8000` напрямую или `http://localhost/api` через Nginx.
Запросы логина сами сохраняют токен в переменную `token`, остальные запросы его подставляют.
Коллекцию можно прогнать целиком через Runner, перед этим лучше выполнить `python seed.py`.
Папки Requests, Assignees, Stages, Dashboard и Notifications проходят сценарий целиком: менеджер создаёт заявку,
руководитель подбирает и назначает исполнителей, специалист ведёт её до «КП готово», менеджер получает уведомление
и закрывает заявку.

Из консоли:

```
npx newman run postman/techqueue.postman_collection.json --env-var base_url=http://localhost/api
```

### Примеры curl

```
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" -d "{\"email\": \"test@techqueue.ru\", \"full_name\": \"Test Testov\", \"password\": \"qwerty1\"}"

curl -X POST localhost:8000/auth/login -d "username=ivanova@techqueue.ru&password=manager123"

curl localhost:8000/auth/me -H "Authorization: Bearer <токен>"

curl localhost:8000/deals -H "Authorization: Bearer <токен>"

curl -X POST localhost:8000/deals -H "Authorization: Bearer <токен>" -H "Content-Type: application/json" -d "{\"title\": \"Cooling tower pumps\", \"client_name\": \"HimProm\", \"amount\": 1500000, \"budget_status\": \"stated\", \"tz_percent\": 30}"
```

Через Nginx (после `seed.py` новая заявка получит id 15):

```
curl -X POST localhost/api/requests -H "Authorization: Bearer <токен менеджера>" -H "Content-Type: application/json" -d "{\"deal_id\": 2, \"category_id\": 2, \"title\": \"Air dryer\"}"

curl localhost/api/requests/15/suggest -H "Authorization: Bearer <токен руководителя>"

curl -X PUT localhost/api/requests/15/assignees -H "Authorization: Bearer <токен руководителя>" -H "Content-Type: application/json" -d "{\"main_id\": 6, \"co_ids\": [5]}"

curl -X POST localhost/api/requests/15/stage -H "Authorization: Bearer <токен специалиста>" -H "Content-Type: application/json" -d "{\"to\": \"in_work\"}"

curl localhost/api/dashboard -H "Authorization: Bearer <токен руководителя>"
```
