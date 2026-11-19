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

## ЛР3 — gRPC: сервис загрузки и планировщик

Подбор исполнителей, дашборд руководителя и расчёты для фоновых задач выполняет отдельный процесс — Load Service.
FastAPI и Scheduler обращаются к нему по gRPC (HTTP/2), общий контракт — `proto/load.proto`. Load Service только читает
PostgreSQL, снимки загрузки и уведомления в отдельной транзакции записывают Scheduler или ручные HTTP-ручки.

```
Postman → Nginx → api (FastAPI) ──gRPC──┐
                                        ├──→ load-service ──→ PostgreSQL (чтение)
                  scheduler ────gRPC────┘
```

| RPC | Кто вызывает |
|---|---|
| `RankSpecialists` | `GET /requests/{id}/suggest` |
| `GetDashboard` | `GET /dashboard` |
| `GetDepartmentLoad` | Scheduler раз в сутки (00:00 UTC) и `POST /scheduler/snapshot` |
| `GetOverdueRequests` | Scheduler раз в час и `POST /scheduler/check-overdue` |

К сервисам ЛР2 добавились два:

- `load-service` — gRPC-сервер `python -m load_service.server`, порт 50051 доступен только внутри сети Compose;
- `scheduler` — `python -m scheduler.main`, один экземпляр, расписание по UTC.

```
docker compose up --build -d
docker compose exec api python seed.py
docker compose ps
```

Разовый запуск задач Планировщика без ожидания расписания:

```
docker compose exec scheduler python -m scheduler.main --once snapshot
docker compose exec scheduler python -m scheduler.main --once check-overdue
```

Сначала выполняется RPC, потом в отдельной транзакции записывается весь результат. Если RPC не прошёл, в базу ничего не
пишется; если не записалась одна строка, откатывается вся пачка.

### Логи и request ID

Каждый ответ API содержит заголовок `X-Request-ID`. Тот же идентификатор уходит в metadata gRPC-вызова и попадает в логи
клиента (`api`) и сервера (`load-service`):

```
docker compose logs api load-service | findstr <X-Request-ID>
```

### Ошибки сервиса загрузки

| gRPC | HTTP | Когда |
|---|---|---|
| `UNAVAILABLE` | 503 | сервис остановлен, соединения нет |
| `DEADLINE_EXCEEDED` | 504 | ответа нет за `LOAD_SERVICE_TIMEOUT` секунд (по умолчанию 2): сервис завис или его адрес ещё ищется |
| остальные | 502 | ошибка расчёта, подробности только в логах `load-service` |

Права и наличие заявки API проверяет до вызова, поэтому 401/403/404 приходят без RPC. Остальные ручки при недоступном
сервисе загрузки работают как обычно.

```
docker compose stop load-service     # подбор и дашборд → 503, первые запросы после остановки могут дать 504
docker compose start load-service    # через несколько секунд снова 200
docker compose pause load-service    # сервис «завис» → 504 через 2 секунды
docker compose unpause load-service
```

### Без Docker

Нужны PostgreSQL и `LOAD_SERVICE_TARGET=127.0.0.1:50051` в `.env` (см. `.env.example`). Каждую команду — в отдельной консоли:

```
python -m load_service.server
uvicorn api.main:app --reload
python -m scheduler.main --once snapshot
```

Python-модули в `proto/` сгенерированы из `proto/load.proto`, после изменения контракта:

```
pip install -r requirements-grpc-dev.txt
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. proto/load.proto
```

## ЛР4 — уведомления через RabbitMQ и WebSocket

```text
API / Scheduler → PostgreSQL → публикация после коммита
                               → RabbitMQ → Notification Service → Nginx → WebSocket-клиент
```

API и Scheduler записывают уведомления в PostgreSQL. После коммита публикатор отправляет событие в RabbitMQ с
`x-request-id`. Сервис уведомлений читает очередь, формирует текст и отправляет сообщение во все открытые
WebSocket-сеансы получателя. Клиент при подключении и после обрыва загружает непрочитанное через REST, а повторы
фильтрует по ID уведомления в пределах одного запуска.

### Запуск

Из корня проекта при запущенном Docker Desktop:

```powershell
docker compose up --build -d
docker compose restart nginx
docker compose ps
```

Для показа на **пустой или одноразовой тестовой базе** выполни `docker compose exec api python seed.py`.
`seed.py` очищает таблицы перед заполнением.

- Swagger — http://localhost/api/docs, переменная Postman `base_url` — `http://localhost/api`.
- RabbitMQ Management — http://localhost:15672, демо-логин и пароль `techqueue`. Exchange `techqueue.events`
  направляет события `request.*` в очередь `notifications`. Сообщения, которые потребитель отклоняет без повтора,
  попадают в `notifications.dead` через `techqueue.dead`.
- WebSocket — `ws://localhost/ws/notifications?token=...`. Токен выдаёт `POST /api/auth/login`.
  Недействительный токен закрывает соединение с кодом `4401`.

### Сценарий показа

Установи зависимости для локального клиента командой `python -m pip install -r requirements.txt`. В разных
терминалах запусти три клиента. Каждый спросит пароль отдельно.

```powershell
python notify_client.py --email head@techqueue.ru
python notify_client.py --email kuznetsov@techqueue.ru
python notify_client.py --email ivanova@techqueue.ru
```

Пароли по порядку — `head123`, `spec123`, `manager123`. Для другого адреса Nginx добавь
`--base http://localhost:ПОРТ`, без суффикса `/api`.

1. В Postman войди как Иванова и создай заявку для её сделки. Тело для демобазы — `{"deal_id":2,"category_id":2,"title":"Демо WebSocket"}`.
   У руководителя появится уведомление о новой заявке.
2. Войди как руководитель. Назначь Кузнецова через `PUT /requests/{id}/assignees` с телом `{"main_id":5,"co_ids":[]}`.
   Уведомление придёт Кузнецову. Два его сеанса получат одно и то же сообщение.
3. Кузнецов переводит заявку в `in_work`, затем в `ready` через `POST /requests/{id}/stage` с телом `{"to":"in_work"}`
   или `{"to":"ready"}`. Иванова получает уведомление о готовом КП.
4. Возьми заголовок `X-Request-ID` из ответа на назначение и сопоставь строку `published` от API со строкой
   `event=request.assigned` от сервиса уведомлений. Поле `sessions` показывает число доставок в WebSocket-сеансы.

```powershell
docker compose logs api notification-service | Select-String -SimpleMatch 'X-Request-ID из ответа'
```

### Как проверить восстановление

- Останови сервис уведомлений командой `docker compose stop notification-service`. Создай новую заявку и назначь
  исполнителя. В RabbitMQ Management у `notifications` вырастет счётчик Ready. После
  `docker compose start notification-service` очередь разберётся, клиент переподключится и увидит пропущенные записи.
- Останови брокер командой `docker compose stop rabbitmq`. Назначение продолжит работать через API, а в логе API
  появится повтор публикации. После `docker compose start rabbitmq` сообщение уйдёт в очередь и дойдёт до клиента.
- Если контейнер `notification-service` **пересоздали**, выполни `docker compose restart nginx`, чтобы прокси
  заново разрешил внутренний адрес сервиса.
