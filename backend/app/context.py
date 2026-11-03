"""[3번 담당] 문맥 처리 — 탐지기가 찾은 신호 중 문맥상 위험하지 않은 것을 걸러냄

TODO(3번):
- 부정·허용 표현 처리 ("안전결제도 가능해요")
"""
from app.models import Message, Signal

QUESTION_ENDINGS = ("나요", "까요")   # 질문으로 끝나는 말
REQUEST_WORDS = ["말고"]             # 질문 모양이어도 사실상 요구인 말


def is_question(text: str) -> bool:
    """'?'로 끝나거나 '~나요', '~까요'로 끝나면 질문문"""
    t = text.strip()
    if t.endswith("?"):
        return True
    t = t.rstrip(".!~ ")              # 끝의 문장부호는 무시
    return t.endswith(QUESTION_ENDINGS)


def is_request(text: str) -> bool:
    """'안전결제 말고 계좌로 하면 안될까요?' 처럼 질문 모양의 요구"""
    return any(w in text for w in REQUEST_WORDS)


# [수업 적용] 2강 List Comprehension — 조건에 맞는 신호만 남기기
def apply_context(messages: list[Message], signals: list[Signal]) -> list[Signal]:
    text_of = {m["index"]: m["text"] for m in messages}   # 번호 → 문장

    def keep(s: Signal) -> bool:
        text = text_of.get(s["message_index"], s["evidence"])
        return not is_question(text) or is_request(text)

    return [s for s in signals if keep(s)]