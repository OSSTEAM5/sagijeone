"""[4번 담당] 외부 메신저 이동 유도 탐지기

판매자가 플랫폼 채팅 밖(카톡, 오픈채팅, 텔레그램, 라인, 문자)으로
대화를 옮기자고 하는 표현을 찾습니다.
플랫폼 밖으로 나가면 거래 기록이 남지 않아 피해 확인이 어려워집니다.
"""
import re

from app.detectors.registry import detector
from app.models import Message, Signal

# (?<![가-힣]) : 앞에 한글이 붙어 있으면 제외 → "온라인으로"의 "라인으로"를 잡지 않기 위함
MESSENGER_PATTERNS = [
    r"(?<![가-힣])(카톡|카카오톡)\s*(아이디|ID|id|으로|주세요|주시면|추가|친추)",
    r"오픈\s*(채팅|톡|카톡)",
    r"open\.kakao\.com",
    r"텔레그램|telegram|t\.me/",
    r"(?<![가-힣])라인\s*(아이디|ID|id|으로)",
    r"문자로\s*(연락|주세요|주시면|드릴|얘기|보내)",
]
# [수업 적용] 2강 First-Class Function — 정규식을 미리 컴파일해 리스트(값)로 관리
COMPILED = [re.compile(p) for p in MESSENGER_PATTERNS]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록 (전략 패턴 개선)
@detector
def detect_external_messenger(messages: list[Message]) -> list[Signal]:
    """판매자가 외부 메신저로 대화를 옮기자고 하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        for pattern in COMPILED:
            found = pattern.search(m["text"])
            if found:
                signals.append({
                    "code": "EXTERNAL_MESSENGER",
                    "signal": "외부 메신저 이동 유도",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "플랫폼 채팅 안에서 거래하세요. 외부 메신저에서는 거래 기록이 보호되지 않아요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals
