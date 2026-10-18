from app.pipeline import analyze

def test_risky_conversation():
    r = analyze("판매자: 안전결제는 안 해요")
    assert r["level"] != "특이 신호 없음"

def test_normal_conversation():
    r = analyze("판매자: 안전결제도 가능해요")
    assert r["level"] == "특이 신호 없음"

def test_buyer_question_is_not_flagged():
    r = analyze("구매자: 혹시 안전결제 안 되나요?\n판매자: 아니요 됩니다")
    assert r["signals"] == []