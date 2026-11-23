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


# ---- #57 중간에 말이 끼는 문장 ----

@pytest.mark.parametrize("text, code", [
    ("판매자: 안전결제는 수수료 때문에 안 해요", "SAFE_PAYMENT_REFUSAL"),
    ("판매자: 안전결제는 좀 번거로워서 안 해요", "SAFE_PAYMENT_REFUSAL"),
    ("판매자: 입금 오늘까지 해주셔야 해요", "PAYMENT_PRESSURE"),
])
def test_gap_expression_detected(text, code):
    assert code in codes(text)


@pytest.mark.parametrize("text", [
    "판매자: 안전결제 하시면 수수료는 제가 낼게요",
    "판매자: 안전결제 안내 드릴게요",
    "판매자: 안전결제 안 해도 되고 해도 돼요",
    # #68 리뷰: 판매자가 오히려 안전결제를 원하는 문장
    "판매자: 안전결제로 해주세요, 직거래는 안 돼요",
    "판매자: 안전결제로만 거래하고 직거래는 안 해요",
    "판매자: 안전결제 되고요 네고는 안 돼요",
    "판매자: 안전결제 수수료는 제가 안 받을게요",
])
def test_gap_expression_not_detected(text):
    assert codes(text) == []
