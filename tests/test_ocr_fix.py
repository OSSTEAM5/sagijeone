"""OCR 오타 보정 테스트 (4번)"""
import pytest

from app.input.ocr_fix import fix_ocr_typos
from app.pipeline import analyze


def codes(text):
    return [s["code"] for s in analyze(text)["signals"]]


@pytest.mark.parametrize("wrong, right", [
    ("카록 아이디 알려드릴게요", "카톡 아이디 알려드릴게요"),
    ("카카오록으로 연락 주세요", "카카오톡으로 연락 주세요"),
    ("안전걸제는 안 해요", "안전결제는 안 해요"),
    ("계솨로만 받아요", "계좌로만 받아요"),
])
def test_typos_are_fixed(wrong, right):
    assert fix_ocr_typos(wrong) == right


def test_normal_text_is_unchanged():
    text = "안녕하세요 아이패드 아직 있나요? 네 있어요"
    assert fix_ocr_typos(text) == text


# 실험에서 놓쳤던 문장이 이제 탐지되는지
def test_ocr_typo_messenger_is_detected():
    assert "EXTERNAL_MESSENGER" in codes("판매자: 카록 아이디 fake_seller로 연락 주세요")


def test_ocr_typo_refusal_is_detected():
    assert "SAFE_PAYMENT_REFUSAL" in codes("판매자: 안전걸제는 안 해요")
