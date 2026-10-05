"""[2번 담당] 결제 관련 위험 신호 탐지기

예시로 1개만 들어 있습니다. 같은 형식으로 탐지기를 추가하면 자동으로 등록됩니다.
"""
from app.detectors.registry import detector, from_seller
from app.models import Message, Signal

REFUSAL_PATTERNS = ["안전결제 안", "안전결제는 안", "안전결제 말고", "안전결제는 말고", "안전결제 거절"]


@detector
def detect_safe_payment_refusal(messages: list[Message]) -> list[Signal]:
    """판매자가 안전결제를 거부하는 표현"""
    return [
        {
            "signal": "안전결제 거부",
            "evidence": m["text"],
            "weight": 2,
            "advice": "플랫폼 안전결제를 요청하세요. 거부한다면 거래를 다시 생각해 보세요.",
        }
        for m in from_seller(messages)
        if any(p in m["text"] for p in REFUSAL_PATTERNS)
    ]


# TODO(2번): detect_payment_pressure (빠른 입금 요구)
# TODO(2번): detect_bank_transfer_only (계좌이체만 요구)
# TODO(2번): detect_external_messenger (외부 메신저 이동)
