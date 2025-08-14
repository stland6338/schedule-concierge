"""OAuth state store abstraction.

Allows swapping in Redis or other distributed store later.
"""
from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, List, Tuple, Callable
import time


class StateStore(Protocol):
    def put(self, state: str, code_verifier: str, created_at: float) -> None: ...
    def pop(self, state: str) -> Optional[Dict[str, Any]]: ...
    def prune(self) -> None: ...
    def size(self) -> int: ...


class MemoryStateStore:
    def __init__(self, ttl_seconds: int = 600, max_entries: int = 50, time_provider: Optional[Callable[[], float]] = None):
        self._data: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.time_provider = time_provider or time.time

    def put(self, state: str, code_verifier: str, created_at: float) -> None:
        self.prune()
        self._data[state] = {"code_verifier": code_verifier, "created_at": created_at}
        self.prune()

    def pop(self, state: str) -> Optional[Dict[str, Any]]:
        self.prune()
        return self._data.pop(state, None)

    def prune(self) -> None:
        now_ts = self.time_provider()
        # Expiry
        expired = [k for k, v in self._data.items() if now_ts - v["created_at"] > self.ttl_seconds]
        for k in expired:
            self._data.pop(k, None)
        # Enforce cap
        while len(self._data) > self.max_entries:
            oldest_key = min(self._data.items(), key=lambda kv: kv[1]["created_at"])[0]
            self._data.pop(oldest_key, None)

    def size(self) -> int:
        return len(self._data)

    @property
    def raw(self):  # pragma: no cover
        return self._data


class RedisStateStore:
    """Redis-backed implementation.

    Uses individual keys with TTL plus a sorted set to enforce capacity.
    Key layout:
      sc:oauth:state:<state> -> value: code_verifier (string) (TTL applied)
      sc:oauth:states (sorted set) -> member=state, score=created_at timestamp

    prune() will:
      - Remove oldest entries if ZCARD exceeds max_entries
      - Remove set members whose key no longer exists (expired naturally)
    """
    STATE_KEY_PREFIX = "sc:oauth:state:"
    STATE_INDEX_KEY = "sc:oauth:states"

    def __init__(self, redis_client, ttl_seconds: int = 600, max_entries: int = 50):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries

    def put(self, state: str, code_verifier: str, created_at: float) -> None:
        pipe = self.redis.pipeline()
        pipe.set(self.STATE_KEY_PREFIX + state, code_verifier, ex=self.ttl_seconds)
        pipe.zadd(self.STATE_INDEX_KEY, {state: created_at})
        pipe.execute()
        self.prune()

    def pop(self, state: str) -> Optional[Dict[str, Any]]:
        key = self.STATE_KEY_PREFIX + state
        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        pipe.zrem(self.STATE_INDEX_KEY, state)
        val, *_ = pipe.execute()
        if val is None:
            return None
        return {"code_verifier": val.decode() if isinstance(val, bytes) else val, "created_at": time.time()}  # created_at not strictly needed

    def prune(self) -> None:
        # Capacity enforcement
        size = self.redis.zcard(self.STATE_INDEX_KEY)
        if size and size > self.max_entries:
            # remove oldest surplus
            surplus = size - self.max_entries
            oldest: List[bytes] = self.redis.zrange(self.STATE_INDEX_KEY, 0, surplus - 1) or []
            if oldest:
                pipe = self.redis.pipeline()
                for member in oldest:
                    state = member.decode() if isinstance(member, bytes) else member
                    pipe.delete(self.STATE_KEY_PREFIX + state)
                    pipe.zrem(self.STATE_INDEX_KEY, state)
                pipe.execute()
        # Clean dangling index members whose key expired
        # (sample small batch to avoid heavy scans)
        members: List[bytes] = self.redis.zrange(self.STATE_INDEX_KEY, 0, -1)
        if members:
            pipe = self.redis.pipeline()
            to_remove: List[str] = []
            for m in members:
                state = m.decode() if isinstance(m, bytes) else m
                if not self.redis.exists(self.STATE_KEY_PREFIX + state):
                    to_remove.append(state)
            if to_remove:
                for s in to_remove:
                    pipe.zrem(self.STATE_INDEX_KEY, s)
                pipe.execute()

    def size(self) -> int:
        return int(self.redis.zcard(self.STATE_INDEX_KEY) or 0)

    @property
    def raw(self):  # pragma: no cover
        # Returns list of states (debug)
        members = self.redis.zrange(self.STATE_INDEX_KEY, 0, -1)
        return [m.decode() if isinstance(m, bytes) else m for m in members]
