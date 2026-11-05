"""[2번 담당] 결제 관련 위험 신호 탐지기

예시로 1개만 들어 있습니다. 같은 형식으로 탐지기를 추가하면 자동으로 등록됩니다.
"""
import re

from app.detectors.registry import detector, from_seller  # noqa: F401
from app.models import Message, Signal

# 안전결제 거부 표현을 정규식 하나로 통합 (#43)
# (결제 수단)(조사)? (강조)? (거부 표현) 순서로 이어지면 탐지
# - "안\s" / "안$" : "안 해요"는 잡고 "안내 드릴게요"의 "안내"는 잡지 않기 위함
# - 조사 목록에 "도"가 없으므로 "안전결제도 가능해요"는 잡지 않음
REFUSAL_RE = re.compile(
    r"(안전\s*(결제|거래)|번개\s*페이|안심\s*결제)(은|는|로는|으로는)?\s*(절대\s*|좀\s*)?"
    r"(안\s|안$|안해|안 해|안돼|안 돼|안되|안 되|말고|거절|싫|하지\s*않|하지\s*마|안\s*받|못\s*해|어려워|불가)"
)


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록 (전략 패턴 개선)
@detector
def detect_safe_payment_refusal(messages: list[Message]) -> list[Signal]:
    """판매자가 안전결제를 거부하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        found = REFUSAL_RE.search(m["text"])
        if found:
            signals.append({
                "code": "SAFE_PAYMENT_REFUSAL",
                "signal": "안전결제 거부",
                "message_index": m.get("index", i),
                "match": found.group(),
                "evidence": m["text"],
                "weight": 2,
                "advice": "플랫폼 안전결제를 요청하세요. 거부한다면 거래를 다시 생각해 보세요.",
            })
    return signals


# 띄어쓰기와 무관하게 잡히도록 정규식 사용 (\s* = 공백 0개 이상)
PRESSURE_PATTERNS = [
    r"오늘\s*입금",
    r"오늘\s*안(에|으로)\s*입금",   # "오늘 안에", "오늘 안으로" 둘 다
    r"빨리\s*입금",
    r"(?<![가-힣])선\s*입금",       # 앞에 한글이 붙으면 제외 → "우선 입금"은 잡지 않음 (messenger.py와 같은 방식)
    r"먼저\s*입금",
]
# 이 표현이 들어간 문장은 재촉이 아니라 입금 확인 안내 → 제외 (#43)
PRESSURE_EXCLUDE = ["확인했"]

# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_payment_pressure(messages: list[Message]) -> list[Signal]:
    """판매자가 입금을 재촉하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        if any(w in m["text"] for w in PRESSURE_EXCLUDE):
            continue
        for p in PRESSURE_PATTERNS:
            found = re.search(p, m["text"])
            if found:
                signals.append({
                    "code": "PAYMENT_PRESSURE",
                    "signal": "빠른 입금 요구",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "입금을 서두르지 마세요. 물건과 판매자 정보를 먼저 확인하세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals


BANK_TRANSFER_ONLY_PATTERNS = ["계좌로만", "계좌이체만", "이체로만", "현금으로만"]
# "계좌이체만 아니면 다 돼요"처럼 오히려 다른 방법을 허용하는 문장은 제외 (#43)
BANK_TRANSFER_EXCLUDE = ["아니면"]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_bank_transfer_only(messages: list[Message]) -> list[Signal]:
    """판매자가 계좌이체(현금)로만 거래하자고 고집하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        if any(w in m["text"] for w in BANK_TRANSFER_EXCLUDE):
            continue
        for p in BANK_TRANSFER_ONLY_PATTERNS:
            if p in m["text"]:
                signals.append({
                    "code": "BANK_TRANSFER_ONLY",
                    "signal": "계좌이체만 요구",
                    "message_index": m.get("index", i),
                    "match": p,
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "계좌이체만 고집한다면 플랫폼 안전결제를 요청하세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals
