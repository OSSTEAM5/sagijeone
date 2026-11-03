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