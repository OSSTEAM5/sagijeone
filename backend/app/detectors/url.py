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

URL_PATTERN = r"https?://[^\s]+|www\.[^\s]+"


def extract_urls(text: str) -> list[str]:
    """
    문장에서 URL만 뽑기
    "여기로 거래해요 https://bit.ly/a" → ["https://bit.ly/a"]
    """
    return re.findall(URL_PATTERN, text)


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
        name = official.split(".")[0]
        # TODO(4번): 오탐 수정 — kakaobank.com 같은 정상 사이트도 여기 걸림
        if name in host:
            return ("URL_IMPERSONATION", "공식 사이트 사칭 의심", 3,
                    f"{official}이 아닌 주소예요. 결제 정보를 입력하지 마세요.")
        if SequenceMatcher(None, domain, official).ratio() >= 0.8:
            return ("URL_LOOKALIKE", "공식 사이트와 비슷한 주소", 3,
                    f"{official}과 비슷하지만 다른 주소예요. 주소를 다시 확인하세요.")
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