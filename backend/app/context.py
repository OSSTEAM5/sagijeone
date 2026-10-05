"""[3번 담당] 문맥 처리 — 지금은 받은 신호를 그대로 돌려주는 뼈대

TODO(3번):
- 질문문 제외 ("~나요?", "~되요?")
- 부정·허용 표현 처리 ("안전결제도 가능해요")
"""
from app.models import Message, Signal


def apply_context(messages: list[Message], signals: list[Signal]) -> list[Signal]:
    return signals
