"""[1번 담당] 대화 문장에서 전화번호·계좌번호·URL 뽑기

4번의 사기 이력 탐지기와 OCR 결과 정리에서 사용합니다.
"""
import re
from collections.abc import Callable

# 정규식 패턴을 상수로 분리 — 패턴만 고치면 함수는 그대로 둘 수 있음
# 010-1234-5678 / 010 1234 5678 / 010.1234.5678 / 01012345678
PHONE_PATTERN = re.compile(r"(?<!\d)01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)")

# 123-45-678901 처럼 하이픈으로 나눈 숫자 묶음 3~4개, 또는 하이픈 없이 10~14자리
ACCOUNT_PATTERN = re.compile(r"(?<![\d-])(?:\d{2,6}(?:-\d{2,6}){2,3}|\d{10,14})(?![\d-])")

# [수업 적용] 5강 객체 참조·가변성 — 바뀌면 안 되는 설정값은 리스트 대신 불변 튜플로 둠
# 국내 계좌번호는 숫자만 세면 10~14자리 → 2026-10-31(8자리) 같은 날짜는 제외됨
ACCOUNT_DIGITS = (10, 14)

# https://… / www.… / daangn-pay.com 처럼 주소만 쓴 경우
URL_PATTERN = re.compile(
    r"https?://[^\s]+"
    r"|www\.[^\s]+"
    r"|(?<![\w@.-])[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*"
    r"\.(?:com|net|org|kr|co\.kr|io|me|ly|xyz|shop|site|link|info|biz|app)"
    r"(?:/[^\s]*)?(?![\w.-])"
)

# 문장 끝에 붙은 문장부호는 URL이 아님 (예: "여기로 오세요 https://bit.ly/abc.")
URL_TRAILING = ".,!?)]}'\"…"


# [수업 적용] 2강 Function Annotations — 입력(str)과 결과(list[str]) 형식을 타입 힌트로 명시
def extract_phones(text: str) -> list[str]:
    """문장에서 휴대폰 번호 뽑기  '번호 010-1234-5678' → ['010-1234-5678']"""
    return PHONE_PATTERN.findall(text)


# [수업 적용] 2강 map/filter 대신 list comprehension — 전화번호·날짜를 걸러내는 filter 역할
def extract_accounts(text: str) -> list[str]:
    """문장에서 계좌번호 뽑기 — 전화번호 형식과 날짜처럼 짧은 숫자는 제외"""
    return [m for m in ACCOUNT_PATTERN.findall(text)
            if not PHONE_PATTERN.fullmatch(m)
            and ACCOUNT_DIGITS[0] <= len(m.replace("-", "")) <= ACCOUNT_DIGITS[1]]


def extract_urls(text: str) -> list[str]:
    """문장에서 URL 뽑기  '여기요 https://bit.ly/abc' → ['https://bit.ly/abc']"""
    return [url.rstrip(URL_TRAILING) for url in URL_PATTERN.findall(text)]


# [수업 적용] 2강 First-Class Function — 함수를 딕셔너리 값으로 저장
# [수업 적용] 3강 함수 지향 전략 — 추출 방식마다 클래스 대신 함수 하나 (새 추출기는 여기에 추가)
EXTRACTORS: dict[str, Callable[[str], list[str]]] = {
    "phones": extract_phones,
    "accounts": extract_accounts,
    "urls": extract_urls,
}


def extract_all(text: str) -> dict[str, list[str]]:
    """세 추출기를 한 번에 실행  → {'phones': [...], 'accounts': [...], 'urls': [...]}"""
    return {name: extract(text) for name, extract in EXTRACTORS.items()}
