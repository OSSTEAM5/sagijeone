"""결제 관련 탐지기 테스트 (2번)"""
import pytest

from app.pipeline import analyze


def codes(text):
    return [s["code"] for s in analyze(text)["signals"]]


@pytest.mark.parametrize("text", [
    "판매자: 오늘 안에 입금하시면 바로 보내드려요",
    "판매자: 오늘안에 입금해주세요",
    "판매자: 선입금 부탁드려요",
    "판매자: 오늘 안으로 입금해주세요",         # #43 미탐 수정
])
def test_payment_pressure_detected(text):
    assert "PAYMENT_PRESSURE" in codes(text)


@pytest.mark.parametrize("text", [
    "판매자: 계좌이체로만 거래해요",
    "판매자: 계좌로만 받아요",
    "판매자: 현금으로만 거래합니다",
])
def test_bank_transfer_only_detected(text):
    assert "BANK_TRANSFER_ONLY" in codes(text)


@pytest.mark.parametrize("text", [
    "판매자: 계좌이체도 되고 안전결제도 돼요",
    "구매자: 계좌이체로만 해야 하나요?",
])
def test_bank_transfer_only_not_detected(text):
    assert codes(text) == []


# ---- #43 결제 탐지기 표현 보강 + 오탐 수정 ----

@pytest.mark.parametrize("text", [
    "판매자: 안전결제는 하지 않아요",
    "판매자: 안전거래는 절대 안 해요",
    "판매자: 번개페이 안돼요",
    "판매자: 안전결제는 어려워요",
    "판매자: 안전결제 불가합니다",
    "판매자: 안전결제는 안 해요",               # 기존 표현도 계속 잡히는지
    "판매자: 안전결제 말고 계좌로 주세요",
])
def test_safe_payment_refusal_detected(text):
    assert "SAFE_PAYMENT_REFUSAL" in codes(text)


@pytest.mark.parametrize("text", [
    "판매자: 안전결제도 가능해요",
    "판매자: 안전결제 안내 드릴게요",
])
def test_safe_payment_refusal_not_detected(text):
    assert codes(text) == []


@pytest.mark.parametrize("text", [
    "판매자: 오늘 입금 확인했어요, 내일 발송할게요",   # 입금 확인 안내
    "판매자: 우선 입금 확인되면 보내드릴게요",         # "우선"의 "선 입금"
    "판매자: 계좌이체만 아니면 다 돼요",               # 오히려 허용
])
def test_review_false_positive_fixed(text):
    assert codes(text) == []
