import json
import os
import threading

import redis
from dotenv import load_dotenv

load_dotenv()


class RedisCache:
    """
    Redis-backed cache with automatic thread-safe in-memory fallback.

    When Redis is unavailable (startup or later failure), all operations
    degrade silently to an in-memory dict. The fallback has no TTL —
    entries live until the process exits. This is acceptable for dev/test;
    in production Redis should always be reachable.
    """

    def __init__(self):
        self.default_ttl = int(os.getenv("REDIS_TTL", 3600))
        self._use_redis = False
        self._client: redis.Redis | None = None
        self._fallback: dict = {}
        self._lock = threading.Lock()
        self._connect()

    def _connect(self) -> None:
        try:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            self._client = client
            self._use_redis = True
        except Exception:
            self._use_redis = False

    def _try_redis(self, fn):
        if not self._use_redis:
            return None
        try:
            return fn(self._client)
        except Exception:
            self._use_redis = False
            return None

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    def set_data(self, key: str, value, ttl: int | None = None) -> None:
        """Store value. Uses default_ttl unless ttl is explicitly provided."""
        actual_ttl = ttl if ttl is not None else self.default_ttl
        serialized = json.dumps(value, default=str)

        result = self._try_redis(lambda c: c.set(key, serialized, ex=actual_ttl))
        if result is None:
            with self._lock:
                self._fallback[key] = value

    def get_data(self, key: str):
        raw = self._try_redis(lambda c: c.get(key))
        if raw is not None:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return None

        with self._lock:
            return self._fallback.get(key)

    def delete_data(self, key: str) -> None:
        self._try_redis(lambda c: c.delete(key))
        with self._lock:
            self._fallback.pop(key, None)

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a Redis glob pattern. Returns count deleted."""
        if not self._use_redis:
            with self._lock:
                to_delete = [k for k in self._fallback if self._match_glob(k, pattern)]
                for k in to_delete:
                    del self._fallback[k]
            return len(to_delete)

        deleted = 0
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor, match=pattern, count=100)
            if keys:
                self._client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        return deleted

    def exists(self, key: str) -> bool:
        result = self._try_redis(lambda c: bool(c.exists(key)))
        if result is not None:
            return result
        with self._lock:
            return key in self._fallback

    @property
    def is_redis_available(self) -> bool:
        return self._use_redis

    # ── Glob helper for in-memory fallback ───────────────────────────────────

    @staticmethod
    def _match_glob(key: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(key, pattern)


redis_cache = RedisCache()
