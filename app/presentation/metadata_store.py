import time
import uuid
from typing import Any, Dict, Optional

_STORE: Dict[str, Dict[str, Any]] = {}
_TS: Dict[str, float] = {}
_TTL_SECONDS = 900  # 15 minutes


def store(metadata: Dict[str, Any]) -> str:
    token = uuid.uuid4().hex
    _STORE[token] = metadata
    _TS[token] = time.time()
    _gc()
    return token


def retrieve(token: str) -> Optional[Dict[str, Any]]:
    md = _STORE.get(token)
    if md is None:
        return None
    if time.time() - _TS.get(token, 0) > _TTL_SECONDS:
        # expired
        _STORE.pop(token, None)
        _TS.pop(token, None)
        return None
    return md


def _gc() -> None:
    now = time.time()
    expired = [k for k, ts in _TS.items() if now - ts > _TTL_SECONDS]
    for k in expired:
        _STORE.pop(k, None)
        _TS.pop(k, None)
