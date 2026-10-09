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
