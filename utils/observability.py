import json
import logging
import time
import uuid


logger = logging.getLogger("cropsense")


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_event(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=False))


class Timer:
    def __init__(self):
        self._start = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)
