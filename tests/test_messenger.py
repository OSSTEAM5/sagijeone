"""외부 메신저 이동 유도 탐지기 테스트 (4번)"""
import pytest

from app.pipeline import analyze


def codes(text):
    return [s["code"] for s in analyze(text)["signals"]]


@pytest.mark.parametrize("text", [
    "판매자: 카톡 아이디 알려드릴게요 거기서 얘기해요",
    "판매자: 카카오톡으로 연락 주세요",
    "판매자: 오픈채팅 링크 드릴게요",
    "판매자: 텔레그램으로 오시면 사진 더 보내드려요",
    "판매자: 라인 아이디 abc123 입니다",
    "판매자: 문자로 연락 주세요",
])
def test_messenger_detected(text):
    assert "EXTERNAL_MESSENGER" in codes(text)


@pytest.mark.parametrize("text", [
    "구매자: 카톡으로 연락 가능할까요?",            # 구매자 발언
    "판매자: 카톡 프사 보시면 실물 사진 있어요",     # 이동 유도 아님
    "판매자: 온라인으로 결제하시면 돼요",            # '라인으로' 오탐 방지
    "판매자: 여기 채팅으로 계속 얘기해요",
])
def test_messenger_not_detected(text):
    assert "EXTERNAL_MESSENGER" not in codes(text)
