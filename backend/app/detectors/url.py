"""[4번 담당] URL 위험 신호 탐지기
URL이 있다는 것만으로 위험하다고 하지 않는다.
공식 도메인은 통과시키고, 아래 경우에만 신호를 만든다.
- IP 주소로 된 링크
- 단축 URL
- 공식 사이트 이름을 넣은 다른 주소 (사칭 의심)
- 공식 도메인과 철자가 비슷한 주소
"""
import csv
import ipaddress #아이피 주소 판별용
import re #정규표현식
from pathlib import Path #파일 다루기
from difflib import SequenceMatcher #문자열 비슷한지 0~1로 계산
from urllib.parse import urlparse #url을 부분별로 쪼개는 도구

from app.detectors.registry import detector #데코레이터
from app.models import Message, Signal #데이터 형식

# URL 위치 : backend/app/detectors/url.py -> parents[2] = backend폴더
DATA_DIR = Path(__file__).resolve().parents[2] / "data" 

def load_domains(filename: str) -> set[str]:
    """csv 파일의 domain 열을 읽어서 집합으로 변환"""
    with open(DATA_DIR / filename, encoding="utf-8-sig") as f:
        return {row["domain"].strip().lower() for row in csv.DictReader(f) if row["domain"].strip()}
#  {"domain": "daangn.com", "service": "당근", "category": "중고거래", ...}


OFFICIAL_DOMAINS = load_domains("official_domains.csv")
SHORTENERS = load_domains("shorteners.csv")

# [수업 적용] 5강 객체 참조·가변성 — 바뀌면 안 되는 목록은 frozenset으로
# 공식 사이트 이름(도메인 맨 앞부분)만 모은 것: daangn, bunjang, kakaopay, ...
# "bunjang-safe-pay.shop"처럼 공식 이름을 다른 주소에 끼워 넣은 경우를 찾는 데 씀
BRAND_TO_DOMAIN = {d.split(".")[0]: d for d in OFFICIAL_DOMAINS}

# 공식 도메인에는 없지만 사기 주소에 자주 붙여 쓰는 결제 서비스 이름 (#82 표본: naverpay-safe.shop)
# → 앞부분이 이 이름으로 시작하면 사칭으로 봄: naverpay, naverpaysafe, npay-check ...
# ※ "tossbank"처럼 실제로 있는 다른 서비스와 겹치지 않도록 결제 서비스 이름만 넣음
PAY_ALIASES = {
    "naverpay": "naver.com", "npay": "naver.com",
    "bunjangpay": "bunjang.co.kr", "bungaepay": "bunjang.co.kr", "bgpay": "bunjang.co.kr",
    "daangnpay": "daangn.com", "karrotpay": "daangn.com",
    "tosspay": "toss.im",
}
BRAND_TO_DOMAIN.update({k: v for k, v in PAY_ALIASES.items() if v in OFFICIAL_DOMAINS})
BRAND_NAMES = frozenset(BRAND_TO_DOMAIN)

# 주소처럼 보이는 3가지
# 1) http:// 또는 https:// 로 시작   2) www. 로 시작
# 3) "kream.co.kr", "bunjang-safe-pay.shop/order" 처럼 앞부분 없이 쓴 주소
#    → 아무 "단어.단어"나 잡지 않도록, 끝이 아래 목록(최상위 도메인)일 때만 주소로 봄
TLDS = ("com|net|org|kr|shop|xyz|top|site|online|store|info|io|me|im|ly|do|gl|"
        "link|click|app|live|vip|cc|co|biz|pro")
URL_PATTERN = re.compile(
    r"https?://[^\s]+"
    r"|www\.[^\s]+"
    rf"|(?<![\w@.])[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:{TLDS})(?![a-z0-9-])(?:/[^\s]*)?",
    re.IGNORECASE,   # "Bunjang-Pay.SHOP"처럼 대문자가 섞여도 찾음
)


def refang(text: str) -> str:
    """보안 글에서 쓰는 '무력화된 주소'를 원래 모양으로: hxxps://a[.]shop → https://a.shop"""
    return re.sub(r"hxxp", "http", text, flags=re.IGNORECASE).replace("[.]", ".")


def extract_urls(text: str) -> list[str]:
    """
    문장에서 URL만 뽑기
    "여기로 거래해요 https://bit.ly/a" → ["https://bit.ly/a"]
    "kream.co.kr에서 확인하세요"       → ["kream.co.kr"]
    """
    return URL_PATTERN.findall(refang(text))


def brand_in_host(host: str) -> str | None:
    """
    주소를 '.'과 '-'로 잘라서, 조각 중에 공식 사이트 이름이 그대로 있으면 그 공식 도메인을 돌려줌
    'bunjang-safe-pay.shop' → 'bunjang.co.kr'
    'naverpay-safe.shop'    → 'naver.com'     (결제 서비스 이름 PAY_ALIASES)
    'kakaobank.com'         → None  (조각 'kakaobank'는 'kakao'와 다른 이름 → 예전 오탐 방지)
    """
    for token in re.split(r"[.\-]", host):
        if token in BRAND_NAMES:
            return BRAND_TO_DOMAIN[token]
        for alias in PAY_ALIASES:           # "naverpaysafe"처럼 결제 서비스 이름 뒤에 글자를 붙인 경우
            if token.startswith(alias) and alias in BRAND_TO_DOMAIN:
                return BRAND_TO_DOMAIN[alias]
    return None


def get_host(url: str) -> str:
    """
    URL에서 사이트 이름만 꺼내기
    'https://pay.daangn.com/abc' → 'pay.daangn.com'
    """
    if not url.startswith("http"):
        url = "http://" + url
    return urlparse(url).hostname or ""


def registered_domain(host: str) -> str:
    """
    주소의 진짜 주인: 'pay.daangn.com' → 'daangn.com'
    "daangn.com.safe-pay.xyz" → "safe-pay.xyz"
    """
    parts = host.split(".")
    if len(parts) >= 3 and parts[-1] == "kr" and parts[-2] in {"co", "or", "go", "ac", "ne"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_ip(host: str) -> bool:
    """IP 주소인지 확인"""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False

def check_url(url: str) -> tuple[str, str, int, str] | None:
    """
    URL 하나 검사 → (code, 신호 이름, weight, 권장 행동) 또는 None
    1. 공식 도메인 인지
    2. IP주소인지
    3. 단축 URL인지
    4. 공식 이름인지, 철자 비슷한지 판별
    위에서 걸리면 검사 X
    """
    host = get_host(url)
    domain = registered_domain(host)

    if domain in OFFICIAL_DOMAINS:          # 공식 사이트는 통과
        return None
    if is_ip(host):                         # IP 주소
        return ("URL_IP_ADDRESS", "IP 주소로 된 링크", 2,
                "정상 서비스는 숫자 주소를 거의 쓰지 않아요. 접속하지 마세요.")
    if domain in SHORTENERS:                # 단축 URL
        return ("URL_SHORTENER", "단축 URL", 1,
                "실제 주소가 가려져 있어요. 원래 주소를 확인한 뒤 접속하세요.")
    for official in OFFICIAL_DOMAINS:       # 사칭 / 비슷한 주소
        if official in host:
            return ("URL_IMPERSONATION", "공식 사이트 사칭 의심", 3,
                    f"{official}이 아닌 주소예요. 결제 정보를 입력하지 마세요.")
        if SequenceMatcher(None, domain, official).ratio() >= 0.8:
            return ("URL_LOOKALIKE", "공식 사이트와 비슷한 주소", 3,
                    f"{official}과 비슷하지만 다른 주소예요. 주소를 다시 확인하세요.")
    official = brand_in_host(host)          # 공식 이름 + 다른 단어: bunjang-safe-pay.shop
    if official:
        return ("URL_IMPERSONATION", "공식 사이트 사칭 의심", 3,
                f"{official}이 아닌 주소예요. 결제 정보를 입력하지 마세요.")
    return None



# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록 (전략 패턴 개선)
@detector
def detect_suspicious_url(messages: list[Message]) -> list[Signal]:
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":          # 구매자가 보낸 링크는 검사하지 않음
            continue
        for url in extract_urls(m["text"]):
            result = check_url(url)
            if result:
                code, name, weight, advice = result
                signals.append({
                    "code": code,
                    "signal": name,
                    "message_index": m.get("index", i),
                    "match": url,
                    "evidence": m["text"],
                    "weight": weight,
                    "advice": advice,
                })
    return signals