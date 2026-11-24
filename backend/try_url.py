"""URL 탐지기 확인용 스크립트 (커밋하지 않아도 됨)
실행: backend 폴더에서  py try_url.py
"""
from app.detectors import detectors
from app.detectors.url import OFFICIAL_DOMAINS, SHORTENERS, check_url
from app.pipeline import analyze

print("=== 1. CSV 목록이 읽혔나? ===")
print("공식 도메인:", OFFICIAL_DOMAINS)
print("단축 URL   :", SHORTENERS)

print("\n=== 2. @detector로 등록됐나? ===")
names = [d.__name__ for d in detectors]
print("등록된 탐지기:", names)
print("URL 탐지기 등록:", "OK" if "detect_suspicious_url" in names else "실패")

print("\n=== 3. URL 하나씩 판정 ===")
cases = [
    ("https://www.daangn.com/articles/123", None),                  # 공식 → 통과
    ("https://m.bunjang.co.kr/products/1", None),                   # 공식(.co.kr) → 통과
    ("https://www.google.com", None),                               # 관련 없음 → 통과
    ("https://bit.ly/3abcd", "URL_SHORTENER"),                       # 단축 URL
    ("http://123.45.67.89/login", "URL_IP_ADDRESS"),                 # IP 주소
    ("https://daangn.com.safe-pay.xyz/pay", "URL_IMPERSONATION"),    # 사칭
    ("https://www.kakaobank.com", None),                             # 정상 관련 회사 → 통과해야 함 (오탐 확인용)
    ("https://daangn-pay.com", "URL_LOOKALIKE"),                     # 비슷한 주소 → 잡아야 함
]
for url, expected in cases:
    result = check_url(url)
    code = result[0] if result else None
    mark = "OK  " if code == expected else "실패"
    print(f"[{mark}] {url:42} → {code}")

print("\n=== 4. 전체 흐름(analyze)에서 확인 ===")
conversations = [
    "판매자: 여기서 결제해주세요 https://daangn.com.safe-pay.xyz/pay",
    "판매자: 판매글 링크예요 https://www.daangn.com/articles/123",
    "구매자: 이 링크 맞나요? https://bit.ly/abc",
]
for text in conversations:
    r = analyze(text)
    print(f"{text}\n   → 등급: {r['level']} / 신호: {[s['signal'] for s in r['signals']]}")
