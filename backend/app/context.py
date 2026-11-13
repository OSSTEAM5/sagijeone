"""[3번 담당] 문맥 처리 — 탐지기가 찾은 신호 중 문맥상 위험하지 않은 것을 걸러냄

TODO(3번):
- 부정·허용 표현 처리 ("안전결제도 가능해요")
"""
import re

from app.models import Message, Signal

# [수업 적용] 5강 객체 참조·가변성 — 바뀌면 안 되는 값은 리스트 대신 불변 튜플로 둠
QUESTION_ENDINGS = ("나요", "까요")   # 질문으로 끝나는 말
REQUEST_WORDS = ["말고"]             # 질문 모양이어도 사실상 요구인 말


# [수업 적용] 2강 Function Annotations — 입력(str)과 결과(bool) 형식을 타입 힌트로 명시
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


# [수업 적용] 2강 map/filter 대신 list comprehension — 빈 문장을 걸러내는 filter 역할
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
# [수업 적용] 5강 참조로서의 함수 매개변수 — 받은 리스트는 고치지 않고 새 리스트를 돌려줌
def apply_context(messages: list[Message], signals: list[Signal]) -> list[Signal]:
    text_of = {m["index"]: m["text"] for m in messages}   # 번호 → 문장

    # [수업 적용] 4강 Closures — 안쪽 함수 keep()이 바깥 함수의 text_of를 기억해서 씀
    # (값을 읽기만 하고 바꾸지 않으므로 nonlocal 선언이 필요 없음 — 4강 변수 범위 규칙)
    def keep(s: Signal) -> bool:
        text = text_of.get(s["message_index"], s["evidence"])
        # 메시지 전체가 아니라, 신호가 걸린 문장만 질문인지 확인 (#32)
        sentence = sentence_with_match(text, s.get("match", ""))
        return not is_question(sentence) or is_request(sentence)

    return [s for s in signals if keep(s)]