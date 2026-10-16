"""[2번 담당] 결제 관련 위험 신호 탐지기

예시로 1개만 들어 있습니다. 같은 형식으로 탐지기를 추가하면 자동으로 등록됩니다.
"""
from app.detectors.registry import detector, from_seller  # noqa: F401
from app.models import Message, Signal

REFUSAL_PATTERNS = ["안전결제 안", "안전결제는 안", "안전결제 말고", "안전결제는 말고", "안전결제 거절"]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록 (전략 패턴 개선)
@detector
def detect_safe_payment_refusal(messages: list[Message]) -> list[Signal]:
    """판매자가 안전결제를 거부하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        for p in REFUSAL_PATTERNS:
            if p in m["text"]:
                signals.append({
                    "code": "SAFE_PAYMENT_REFUSAL",
                    "signal": "안전결제 거부",
                    "message_index": m.get("index", i),
                    "match": p,
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "플랫폼 안전결제를 요청하세요. 거부한다면 거래를 다시 생각해 보세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals


# TODO(2번): detect_payment_pressure (빠른 입금 요구)
# TODO(2번): detect_bank_transfer_only (계좌이체만 요구)
