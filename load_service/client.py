import logging
import os
from math import isfinite
from uuid import uuid4

import grpc
from dotenv import load_dotenv
from google.protobuf.empty_pb2 import Empty

from proto import load_pb2, load_pb2_grpc

logger = logging.getLogger(__name__)


class LoadClient:
    def __init__(self, target, timeout=2.0):
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("Дедлайн gRPC должен быть положительным числом")
        self.timeout = timeout
        self.channel = grpc.insecure_channel(target)
        self.stub = load_pb2_grpc.LoadServiceStub(self.channel)

    @classmethod
    def from_env(cls):
        load_dotenv()
        return cls(
            os.getenv("LOAD_SERVICE_TARGET", "127.0.0.1:50051"),
            float(os.getenv("LOAD_SERVICE_TIMEOUT", "2")),
        )

    def close(self):
        self.channel.close()

    def _call(self, method, request, request_id):
        request_id = request_id or uuid4().hex
        logger.info("grpc rpc=%s request_id=%s", method, request_id)
        try:
            return getattr(self.stub, method)(
                request, timeout=self.timeout, metadata=(("x-request-id", request_id),),
            )
        except grpc.RpcError as exc:
            logger.warning("grpc rpc=%s request_id=%s status=%s", method, request_id, exc.code().name)
            raise

    def rank_specialists(self, category_id, *, request_id=None):
        return self._call("RankSpecialists", load_pb2.RankSpecialistsRequest(category_id=category_id), request_id)

    def get_dashboard(self, *, request_id=None):
        return self._call("GetDashboard", Empty(), request_id)

    def get_department_load(self, *, request_id=None):
        return self._call("GetDepartmentLoad", Empty(), request_id)

    def get_overdue_requests(self, *, request_id=None):
        return self._call("GetOverdueRequests", Empty(), request_id)
