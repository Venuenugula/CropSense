import json
import os
import base64
from collections.abc import MutableMapping


class _MemoryBackend:
    def __init__(self):
        self._data = {}

    def get(self, namespace: str, uid: int):
        return self._data.get(namespace, {}).get(str(uid))

    def set(self, namespace: str, uid: int, value: dict):
        ns = self._data.setdefault(namespace, {})
        ns[str(uid)] = dict(value)

    def delete(self, namespace: str, uid: int):
        ns = self._data.get(namespace, {})
        ns.pop(str(uid), None)

    def has(self, namespace: str, uid: int) -> bool:
        return self.get(namespace, uid) is not None


class _RedisBackend:
    def __init__(self, url: str):
        import redis

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, namespace: str) -> str:
        return f"state:{namespace}"

    def get(self, namespace: str, uid: int):
        raw = self._client.hget(self._key(namespace), str(uid))
        return _decode_obj(json.loads(raw)) if raw else None

    def set(self, namespace: str, uid: int, value: dict):
        payload = json.dumps(_encode_obj(value), ensure_ascii=False)
        self._client.hset(self._key(namespace), str(uid), payload)

    def delete(self, namespace: str, uid: int):
        self._client.hdel(self._key(namespace), str(uid))

    def has(self, namespace: str, uid: int) -> bool:
        return self._client.hexists(self._key(namespace), str(uid))


def _build_backend():
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return _MemoryBackend()
    try:
        backend = _RedisBackend(redis_url)
        # lightweight connectivity check; fallback keeps bot usable.
        backend._client.ping()
        return backend
    except Exception as e:
        print(f"State store fallback to memory: {e}")
        return _MemoryBackend()


_BACKEND = _build_backend()


def _encode_obj(value):
    if isinstance(value, bytes):
        return {"__bytes__": True, "b64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {k: _encode_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode_obj(v) for v in value]
    return value


def _decode_obj(value):
    if isinstance(value, dict):
        if value.get("__bytes__") and "b64" in value:
            return base64.b64decode(value["b64"])
        return {k: _decode_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_obj(v) for v in value]
    return value


class _StateProxy(MutableMapping):
    def __init__(self, store: "StateStore", uid: int):
        self._store = store
        self._uid = uid

    def _load(self) -> dict:
        return self._store._backend.get(self._store.namespace, self._uid) or {}

    def _save(self, data: dict):
        self._store._backend.set(self._store.namespace, self._uid, data)

    def __getitem__(self, key):
        return self._load()[key]

    def __setitem__(self, key, value):
        data = self._load()
        data[key] = value
        self._save(data)

    def __delitem__(self, key):
        data = self._load()
        del data[key]
        self._save(data)

    def __iter__(self):
        return iter(self._load())

    def __len__(self):
        return len(self._load())

    def pop(self, key, default=None):
        data = self._load()
        value = data.pop(key, default)
        self._save(data)
        return value

    def update(self, *args, **kwargs):
        data = self._load()
        data.update(*args, **kwargs)
        self._save(data)


class StateStore:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self._backend = _BACKEND

    def __contains__(self, uid: int) -> bool:
        return self._backend.has(self.namespace, uid)

    def __getitem__(self, uid: int):
        if uid not in self:
            raise KeyError(uid)
        return _StateProxy(self, uid)

    def __setitem__(self, uid: int, value: dict):
        self._backend.set(self.namespace, uid, value)

    def get(self, uid: int, default=None):
        value = self._backend.get(self.namespace, uid)
        return value if value is not None else default

    def setdefault(self, uid: int, default=None):
        if uid not in self:
            self._backend.set(self.namespace, uid, default or {})
        return _StateProxy(self, uid)

    def pop(self, uid: int, default=None):
        value = self._backend.get(self.namespace, uid)
        self._backend.delete(self.namespace, uid)
        return value if value is not None else default


def create_state_store(namespace: str) -> StateStore:
    return StateStore(namespace)
