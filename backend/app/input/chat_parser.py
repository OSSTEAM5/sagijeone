"""[1번 담당] 붙여넣은 채팅 텍스트 → messages

지금은 최소 기능만 있는 뼈대입니다. 1번 담당자가 형식을 늘려가며 완성합니다.
"""
import re

from app.models import Message

SPEAKER_MAP = {"판매자": "seller", "구매자": "buyer"}


def parse_prefixed(text: str) -> list[Message] | None:
    """'판매자: 내용' / '구매자: 내용' 형식. 형식이 다르면 None"""
    messages: list[Message] = []
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        m = re.match(r"^\s*(판매자|구매자)\s*[:：]\s*(.+)$", line)
        if not m:
            return None
        messages.append({"speaker": SPEAKER_MAP[m.group(1)], "text": m.group(2).strip()})
    return messages or None


def parse_plain(text: str) -> list[Message]:
    """화자 정보가 없는 텍스트 — 항상 성공하는 마지막 파서"""
    return [{"speaker": "unknown", "text": line.strip()}
            for line in text.splitlines() if line.strip()]


# [수업 적용] 2·3강 First-Class Function — 파서 함수를 리스트로 관리하고 순서대로 시도
# TODO(1번): parse_kakao_export 등 형식 추가
PARSERS = [parse_prefixed, parse_plain]


def parse_chat(text: str) -> list[Message]:
    for parser in PARSERS:
        result = parser(text)
        if result:
            return result
    return []
