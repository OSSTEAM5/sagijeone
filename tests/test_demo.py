"""[3번 담당] 중간 발표 시연 대화 고정 테스트 (이슈 #44)

docs/demo_conversations.md 의 대화 3개가 항상 같은 결과를 내는지 확인합니다.
코드가 바뀌어 시연 결과가 달라지면 여기서 바로 실패합니다.
"""
import pytest

from app.pipeline import analyze

NORMAL = """구매자: 안녕하세요, 아이패드 아직 있나요?
판매자: 네 있어요!
구매자: 혹시 안전결제 되나요?
판매자: 네 안전결제로 하셔도 돼요.
구매자: 좋아요, 결제할게요."""

CAUTION = """구매자: 자전거 아직 판매 중이세요?
판매자: 네, 문의가 많아서 오늘 입금하시는 분께 드릴게요.
구매자: 직거래는 안 되나요?
판매자: 거리가 멀어서 택배로만 가능해요."""

MULTI_RISK = """구매자: 갤럭시 버즈 아직 있나요?
판매자: 네 있어요. 안전결제는 안 해요, 수수료가 아까워서요.
판매자: 여기 말고 카톡으로 얘기해요. 아이디 abc123 이에요.
판매자: 결제는 이 링크로 해주세요 https://daangn-pay.com/order
구매자: 아 네..."""

# (대화, 기대 level, 기대 신호 code 목록)
DEMO_CASES = [
    (NORMAL, "특이 신호 없음", set()),
    (CAUTION, "주의", {"PAYMENT_PRESSURE"}),
    (MULTI_RISK, "여러 위험 신호", {"SAFE_PAYMENT_REFUSAL", "EXTERNAL_MESSENGER", "URL_LOOKALIKE"}),
]


@pytest.mark.parametrize(
    "text, expected_level, expected_codes",
    DEMO_CASES,
    ids=["정상", "주의", "여러 위험"],
)
def test_demo_conversation(text, expected_level, expected_codes):
    r = analyze(text)
    codes = {s["code"] for s in r["signals"]}

    assert r["level"] == expected_level
    assert codes == expected_codes


def test_multi_risk_has_three_or_more_kinds():
    """여러 위험 대화는 서로 다른 신호가 3종류 이상이어야 함"""
    r = analyze(MULTI_RISK)
    assert len({s["code"] for s in r["signals"]}) >= 3


def test_normal_buyer_question_not_flagged():
    """구매자의 '안전결제 되나요?' 질문은 신호로 잡히면 안 됨 (오탐 없음)"""
    r = analyze(NORMAL)
    assert r["signals"] == []
