"""
HISTORY MANAGEMENT (Redis + LangChain)
======================================
3 ta level:

  L1) Short-term  -> RedisChatMessageHistory: protita message Redis list e save.
  L2) Window      -> WindowedRedisHistory: sesh N ta message LLM ke dey (cost control).
  L3) Long-term   -> UserProfileStore: user er standing preference (budget, brand,
                     size) alada Redis hash e -- eta history te na rekhe prompt e inject kora hoy.

Key naming convention:
  chat:{session_id}            -> message list (langchain-redis manage kore)
  profile:{user_id}            -> user preference hash
"""

from typing import Dict, List, Optional

import redis
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_community.chat_message_histories import RedisChatMessageHistory

from app.config import settings

# Ekta shared connection pool -- prottek request e notun connection kholar dorkar nei
_redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


# --------------------------------------------------------------------------
# L1 + L2 : Windowed Redis chat history
# --------------------------------------------------------------------------
class WindowedRedisHistory(BaseChatMessageHistory):
    """
    RedisChatMessageHistory ke wrap kore.
    - add_messages() -> shob message Redis e jay (audit/analytics er jonno full log thake)
    - messages       -> shudhu sesh `window` ta message ferot dey (LLM cost control)
    """

    def __init__(self, session_id: str, window: Optional[int] = None, ttl: Optional[int] = None):
        self.session_id = session_id
        self.window = window or settings.HISTORY_WINDOW
        self._inner = RedisChatMessageHistory(
            session_id=session_id,
            url=settings.REDIS_URL,          # `redis_url` নয়, `url`
            key_prefix="chat:",              # key হবে chat:{session_id}
            ttl=ttl if ttl is not None else settings.HISTORY_TTL,
        )

    @property
    def messages(self) -> List[BaseMessage]:
        msgs = self._inner.messages
        return msgs[-self.window:] if self.window else msgs

    @property
    def full_messages(self) -> List[BaseMessage]:
        """Window chhara pura history -- UI te dekhano ba summarize korar jonno."""
        return self._inner.messages

    def add_messages(self, messages: List[BaseMessage]) -> None:
        self._inner.add_messages(messages)

    def clear(self) -> None:
        self._inner.clear()


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """RunnableWithMessageHistory ei factory ta call kore."""
    return WindowedRedisHistory(session_id=session_id)


def clear_session(session_id: str) -> None:
    get_session_history(session_id).clear()


def get_full_history(session_id: str) -> List[Dict[str, str]]:
    """UI te render korar jonno serializable form."""
    h = WindowedRedisHistory(session_id=session_id)
    return [{"role": m.type, "content": m.content} for m in h.full_messages]


# --------------------------------------------------------------------------
# L3 : Long-term user profile (session er baireo tike thake)
# --------------------------------------------------------------------------
class UserProfileStore:
    """
    Ekhane persistent preference rakha hoy -- jemon 'budget 5000', 'brand Aura pochondo'.
    Eta history er moto expire hoy na, tai purono session shesh holeo agent user ke 'mone rakhe'.
    """

    @staticmethod
    def _key(user_id: str) -> str:
        return f"profile:{user_id}"

    @classmethod
    def get(cls, user_id: str) -> Dict[str, str]:
        return _redis_client.hgetall(cls._key(user_id)) or {}

    @classmethod
    def set(cls, user_id: str, **fields) -> None:
        clean = {k: str(v) for k, v in fields.items() if v is not None}
        if clean:
            _redis_client.hset(cls._key(user_id), mapping=clean)

    @classmethod
    def clear(cls, user_id: str) -> None:
        _redis_client.delete(cls._key(user_id))

    @classmethod
    def as_prompt_text(cls, user_id: str) -> str:
        data = cls.get(user_id)
        if not data:
            return "No saved preferences yet."
        return "; ".join(f"{k}={v}" for k, v in data.items())


def ping_redis() -> bool:
    try:
        return _redis_client.ping()
    except Exception:
        return False
