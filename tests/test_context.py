from app.pipeline import analyze


def test_question_with_mark_is_not_flagged():
    r = analyze("판매자: 안전결제 안 되나요?")
    assert r["signals"] == []


def test_question_without_mark_is_not_flagged():
    r = analyze("판매자: 안전결제 안 되나요")
    assert r["signals"] == []


def test_refusal_is_still_flagged():
    r = analyze("판매자: 안전결제는 안 해요")
    assert len(r["signals"]) == 1


def test_malgo_request_is_still_flagged():
    r = analyze("판매자: 안전결제 말고 계좌로 하면 안될까요?")
    assert len(r["signals"]) == 1


# ---- #32: 거부 + 질문이 한 메시지에 섞인 경우 ----
def test_refusal_then_question_is_flagged():
    r = analyze("판매자: 안전결제는 안 해요. 괜찮나요?")
    assert [s["code"] for s in r["signals"]] == ["SAFE_PAYMENT_REFUSAL"]


def test_refusal_then_question_with_exclamation_is_flagged():
    r = analyze("판매자: 안전결제는 안 해요! 그래도 사실 건가요?")
    assert [s["code"] for s in r["signals"]] == ["SAFE_PAYMENT_REFUSAL"]


def test_greeting_then_question_is_not_flagged():
    """앞 문장은 평범하고, 신호가 걸린 문장이 질문이면 여전히 거름"""
    r = analyze("판매자: 안녕하세요. 안전결제 안 되나요?")
    assert r["signals"] == []


def test_url_dot_is_not_split():
    """주소 속 '.'에서 문장을 나누면 안 됨"""
    r = analyze("판매자: 결제는 https://daangn-pay.com/order 로 해주세요. 괜찮죠?")
    assert [s["code"] for s in r["signals"]] == ["URL_LOOKALIKE"]