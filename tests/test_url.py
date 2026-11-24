"""URL 탐지기 테스트 (4번)"""
import pytest

from app.detectors.url import extract_urls
from app.pipeline import analyze


def codes(text):
    return [s["code"] for s in analyze(text)["signals"]]


@pytest.mark.parametrize("text, expected", [
    ("여기로 거래해요 https://bit.ly/a", ["https://bit.ly/a"]),
    ("kream.co.kr에서 확인하세요", ["kream.co.kr"]),                         # http 없이 쓴 주소
    ("pay-safe.shop/order/1 여기서 결제", ["pay-safe.shop/order/1"]),
    ("hxxps://pay-safe[.]shop/order 여기서", ["https://pay-safe.shop/order"]),  # 무력화된 주소
])
def test_extract_urls(text, expected):
    assert extract_urls(text) == expected


@pytest.mark.parametrize("text", [
    "배터리 1.5배 오래가요",
    "메일은 seller@naver.com 으로 주세요",
    "사진.png 보내드렸어요",
])
def test_extract_urls_not_url(text):
    assert extract_urls(text) == []


@pytest.mark.parametrize("text, code", [
    # 공식 이름 + 다른 단어로 만든 가짜 주소 (#76 블라인드 표본 T-정윤재-03)
    ("판매자: https://bunjang-safe-pay.shop/order/2231 여기서 결제하시면 돼요", "URL_IMPERSONATION"),
    ("판매자: bunjang-safe-pay.shop/order/2231 여기서 결제하시면 돼요", "URL_IMPERSONATION"),
    ("판매자: hxxps://bunjang-safe-pay[.]shop/order/2231 여기서 결제하시면 돼요", "URL_IMPERSONATION"),
    ("판매자: https://safe-daangn.xyz/pay 로 결제해 주세요", "URL_IMPERSONATION"),
    # 기존 동작 유지
    ("판매자: https://daangn-pay.com/order", "URL_LOOKALIKE"),
    ("판매자: https://daangn.com.safe-pay.net/checkout", "URL_IMPERSONATION"),
    ("판매자: hxxps://naverpay-safe[.]shop/pay/33019 여기로 결제하세요", "URL_IMPERSONATION"),  # #82 T-박태민-07
    ("판매자: https://naverpaysafe.shop/pay 결제 링크예요", "URL_IMPERSONATION"),
    ("판매자: https://tosspay-check.site/order 로 결제해 주세요", "URL_IMPERSONATION"),
])
def test_fake_url_detected(text, code):
    assert code in codes(text)


@pytest.mark.parametrize("text", [
    "판매자: kream.co.kr 들어가서 제 거래 내역 캡처해 드릴게요",   # 진짜 공식 주소 (T-정윤재-10)
    "판매자: https://www.kakaobank.com/ 여기 참고하세요",          # 예전 오탐
    "판매자: https://www.naver.com 검색해 보세요",                 # 진짜 공식 주소
    "판매자: https://pay.naver.com 에서 결제 내역 확인하세요",      # 공식 도메인의 하위 주소
    "판매자: https://www.daangn.com",
    "구매자: bunjang-safe-pay.shop 이거 맞는 주소예요?",            # 구매자가 보낸 링크
])
def test_fake_url_not_detected(text):
    assert codes(text) == []
