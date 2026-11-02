"""결제 관련 탐지기 테스트 (2번)"""
import pytest

from app.pipeline import analyze


def codes(text):
    return [s["code"] for s in analyze(text)["signals"]]


@pytest.mark.parametrize("text", [
    "판매자: 오늘 안에 입금하시면 바로 보내드려요",
    "판매자: 오늘안에 입금해주세요",
    "판매자: 선입금 부탁드려요",
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
