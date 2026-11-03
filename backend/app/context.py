"""[3번 담당] 문맥 처리 — 탐지기가 찾은 신호 중 문맥상 위험하지 않은 것을 걸러냄

TODO(3번):
- 부정·허용 표현 처리 ("안전결제도 가능해요")
"""
import re

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


def split_sentences(text: str) -> list[str]:
    """'.', '?', '!' 뒤에 띄어쓰기가 오면 문장을 나눔
    '안전결제는 안 해요. 괜찮나요?' → ['안전결제는 안 해요.', '괜찮나요?']
    (띄어쓰기를 기준으로 해서 'daangn.com' 같은 주소 속 '.'은 나누지 않음)
    """
    return [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]


def sentence_with_match(text: str, match: str) -> str:
    """탐지기가 찾은 표현(match)이 들어 있는 문장만 골라냄. 못 찾으면 메시지 전체"""
    if match:
        for sentence in split_sentences(text):
            if match in sentence:
                return sentence
    return text


# [수업 적용] 2강 List Comprehension — 조건에 맞는 신호만 남기기
def apply_context(messages: list[Message], signals: list[Signal]) -> list[Signal]:
    text_of = {m["index"]: m["text"] for m in messages}   # 번호 → 문장

    def keep(s: Signal) -> bool:
        text = text_of.get(s["message_index"], s["evidence"])
        # 메시지 전체가 아니라, 신호가 걸린 문장만 질문인지 확인 (#32)
        sentence = sentence_with_match(text, s.get("match", ""))
        return not is_question(sentence) or is_request(sentence)

    return [s for s in signals if keep(s)]