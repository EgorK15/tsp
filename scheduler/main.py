import argparse
import logging
import signal
import threading
from datetime import datetime, timedelta, timezone

import grpc

from load_service.client import LoadClient
from scheduler import jobs

logger = logging.getLogger("scheduler")

JOBS = {"snapshot": jobs.take_snapshot, "check-overdue": jobs.check_overdue}
PERIODS = {"snapshot": timedelta(days=1), "check-overdue": timedelta(hours=1)}
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def next_run(now, period):
    """Ближайшая граница периода по UTC строго после now: начало следующего часа или суток."""
    return EPOCH + ((now - EPOCH) // period + 1) * period


def run_job(name, client):
    """Выполняет задачу; ошибку только логирует, повтор — в следующий штатный запуск."""
    try:
        JOBS[name](client)
        return True
    except grpc.RpcError as exc:
        logger.error("job=%s failed status=%s", name, exc.code().name)
    except Exception:
        logger.exception("job=%s failed", name)
    return False


def run_forever(client, stop):
    now = datetime.now(timezone.utc)
    due = {name: next_run(now, period) for name, period in PERIODS.items()}
    while not stop.is_set():
        name = min(due, key=due.get)
        logger.info("next job=%s at=%s", name, due[name].isoformat())
        if stop.wait(max((due[name] - datetime.now(timezone.utc)).total_seconds(), 0)):
            break
        run_job(name, client)
        due[name] = next_run(max(datetime.now(timezone.utc), due[name]), PERIODS[name])


def main():
    parser = argparse.ArgumentParser(description="Планировщик: снимок загрузки раз в сутки, проверка просрочек раз в час, по UTC")
    parser.add_argument("--once", choices=JOBS, help="выполнить одну задачу сразу и выйти")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    client = LoadClient.from_env()
    try:
        if args.once:
            raise SystemExit(0 if run_job(args.once, client) else 1)
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        run_forever(client, stop)
        logger.info("Scheduler stopped")
    finally:
        client.close()


if __name__ == "__main__":
    main()
