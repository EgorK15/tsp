import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from time import perf_counter

import grpc
from sqlalchemy import text

from db.crud.settings import get_all_settings
from db.database import SessionLocal
from load_service import analytics, calculations
from proto import load_pb2_grpc

logger = logging.getLogger(__name__)


class LoadService(load_pb2_grpc.LoadServiceServicer):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def _read(self, context, calculate, *args):
        request_id = dict(context.invocation_metadata()).get("x-request-id", "-")
        started = perf_counter()
        try:
            with self.session_factory() as session:
                session.execute(text("SET TRANSACTION READ ONLY"))
                result = calculate(session, get_all_settings(session), datetime.now(timezone.utc), *args)
        except Exception:
            logger.exception("rpc=%s request_id=%s failed", calculate.__name__, request_id)
            context.abort(grpc.StatusCode.INTERNAL, "Load calculation failed")
        logger.info("rpc=%s request_id=%s elapsed_ms=%.1f", calculate.__name__, request_id,
                    (perf_counter() - started) * 1000)
        return result

    def RankSpecialists(self, request, context):
        if request.category_id <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "category_id must be positive")
        return self._read(context, calculations.rank_specialists, request.category_id)

    def GetDashboard(self, request, context):
        return self._read(context, analytics.get_dashboard)

    def GetDepartmentLoad(self, request, context):
        return self._read(context, analytics.department_load)

    def GetOverdueRequests(self, request, context):
        return self._read(context, analytics.overdue_requests)


def create_server(session_factory):
    server = grpc.server(ThreadPoolExecutor(max_workers=4))
    load_pb2_grpc.add_LoadServiceServicer_to_server(LoadService(session_factory), server)
    return server


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    address = os.getenv("LOAD_SERVICE_BIND", "[::]:50051")
    server = create_server(SessionLocal)
    server.add_insecure_port(address)
    server.start()
    logger.info("Load Service listening on %s", address)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=3).wait()


if __name__ == "__main__":
    main()
