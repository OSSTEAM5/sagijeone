"""[4번 담당] 외부 메신저 이동 유도 탐지기

판매자가 플랫폼 채팅 밖(카톡, 오픈채팅, 텔레그램, 라인, 문자)으로
대화를 옮기자고 하는 표현을 찾습니다.
플랫폼 밖으로 나가면 거래 기록이 남지 않아 피해 확인이 어려워집니다.
"""
import re

from app.detectors.registry import detector
from app.models import Message, Signal

# 메신저 이름을 일부러 바꿔 쓴 표기까지 포함 (플랫폼 감지를 피하려는 경우)
# (?<![가-힣]) : 앞에 한글이 붙으면 제외 → "온라인", "아이라인", "생산라인" 오탐 방지
KAKAO = r"(카톡|카카오톡|카카오|ㅋㅌ|ㅋㅋㅇㅌ|카\s*[.\-_·]\s*톡|[kK]\s*톡)"
LINE = r"(라인|라\s*[.\-_·]\s*인|LINE)"                       # 소문자 line은 일반 단어라 제외
TELEGRAM = r"(텔레그램|텔레|텔그|ㅌㄹㄱㄹ|ㅌㄹ|telegram|Telegram)"
MESSENGER = r"(?<![가-힣])(" + KAKAO + "|" + LINE + "|" + TELEGRAM + ")"

# 아이디처럼 생긴 영문·숫자: 4글자 이상 + 영문과 숫자가 둘 다 섞임
# → "iPhone"(숫자 없음), "010-1234-5678"(영문 없음) 같은 오탐 방지
MESSENGER_ID = r"(?=[A-Za-z0-9_.\-]*\d)(?=[A-Za-z0-9_.\-]*[A-Za-z])[A-Za-z0-9_.\-]{4,}"
# 숫자 없는 영문 아이디(abcdseller): 영어 단어(iPhone 등)와 구분이 안 돼서
# 메신저 이름 + 아이디 + 연락/추가가 "한 문장에 다 있을 때만" 잡음
WORD_ID = r"[A-Za-z][A-Za-z0-9_.\-]{4,}"

MESSENGER_PATTERNS = [
    MESSENGER + r"\s*(아이디|ID|id|으로|주세요|주시면|추가|친추)",           # "카톡 아이디", "라인으로", "텔레 추가"
    MESSENGER + r"\s*(아이디\s*)?[:：]?\s*" + MESSENGER_ID,               # "ㅋㅌ ABCD1234", "라인 abc_12", "텔그 abcd12"
    MESSENGER + r"\s*" + WORD_ID + r"\s*(으로|로)?\s*(연락(?!처)|추가|친추|주세요|주시면)",  # "카톡 abcdseller로 연락주세요"
    r"(?<![A-Za-z0-9])" + MESSENGER_ID + r"\s*(으로|로)\s*(연락(?!처)|추가|친추|톡)",  # "ABCD1234로 연락주세요"
    r"오픈\s*(채팅|톡|카톡)",
    r"open\.kakao\.com",
    r"텔레그램|telegram|t\.me/",
    r"문자\s*(로\s*)?(연락|주세요|주시면|드릴|얘기|보내)",   # "문자 주세요"도 포함 (docs/scam_patterns.md 조사)
    r"개인\s*(연락처|번호|톡|메신저)",                        # "개인 연락처로 얘기해요"
]
# [수업 적용] 2강 First-Class Function — 정규식을 미리 컴파일해 리스트(값)로 관리
COMPILED = [re.compile(p) for p in MESSENGER_PATTERNS]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록 (전략 패턴 개선)
@detector
def detect_external_messenger(messages: list[Message]) -> list[Signal]:
    """판매자가 외부 메신저로 대화를 옮기자고 하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        for pattern in COMPILED:
            found = pattern.search(m["text"])
            if found:
                signals.append({
                    "code": "EXTERNAL_MESSENGER",
                    "signal": "외부 메신저 이동 유도",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "플랫폼 채팅 안에서 거래하세요. 외부 메신저에서는 거래 기록이 보호되지 않아요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals
