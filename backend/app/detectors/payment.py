"""[2번 담당] 결제 관련 위험 신호 탐지기

예시로 1개만 들어 있습니다. 같은 형식으로 탐지기를 추가하면 자동으로 등록됩니다.
"""
import re

from app.detectors.registry import detector, from_seller  # noqa: F401
from app.models import Message, Signal

# 안전결제 거부 표현을 정규식 하나로 통합 (#43)
# (결제 수단)(조사)? (강조)? (거부 표현) 순서로 이어지면 탐지
# - "안\s" / "안$" : "안 해요"는 잡고 "안내 드릴게요"의 "안내"는 잡지 않기 위함
# - 조사 목록에 "도"가 없으므로 "안전결제도 가능해요"는 잡지 않음
REFUSAL_RE = re.compile(
    r"(안전\s*(결제|거래)|번개\s*페이|안심\s*결제)(은|는|로는|으로는)?\s*(절대\s*|좀\s*)?"
    r"(안\s|안$|안해|안 해|안돼|안 돼|안되|안 되|말고|거절|싫|하지\s*않|하지\s*마|안\s*받|못\s*해|어려워|불가)"
)

# 중간에 다른 말이 끼는 문장 (#57)
# 예) "안전결제는 수수료 때문에 안 해요", "안전결제는 좀 번거로워서 안 해요"
# - 결제 수단과 거부 표현 사이에 글자 15개까지 허용 (문장부호 . ? ! , 는 넘지 않음)
# - (?!\s*(로|으로)) : "안전결제로 해주세요"처럼 안전결제를 원하는 문장은 시작부터 제외
# - (?![가-힣](은|는)\s) : 사이에 "직거래는", "네고는"처럼 다른 대상이 나오면 끊기
#   → "안전결제 되고요 네고는 안 돼요"의 "안 돼요"는 네고 얘기라 잡지 않음
# - (?!도) : "안전결제도 되는데 ..."처럼 허용하는 문장은 시작부터 제외
# - (?!면\s) : "안전결제 하실 거면 오늘은 안 돼요"처럼 조건(~면) 뒤의 말은 거부로 보지 않음
# - 거부 표현은 위와 같지만, "안내"를 잡지 않도록 "안" 뒤에 공백·끝을 요구하는 규칙은 그대로
REFUSAL_GAP_RE = re.compile(
    r"(안전\s*(결제|거래)|번개\s*페이|안심\s*결제)(?!도)(?!\s*(로|으로))(?:(?!면\s)(?![가-힣](은|는)\s)[^.?!,]){0,15}?"
    r"(안\s|안$|안해|안 해|안돼|안 돼|안되|안 되|거절|싫|하지\s*않|하지\s*마|안\s*받|못\s*해|어려워|불가)"
)
# 거부가 아니라 "해도 되고 안 해도 돼요"처럼 선택을 맡기는 문장은 제외 (#57)
REFUSAL_EXCLUDE = ["해도 돼", "해도 되", "해도돼", "해도되"]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록 (전략 패턴 개선)
@detector
def detect_safe_payment_refusal(messages: list[Message]) -> list[Signal]:
    """판매자가 안전결제를 거부하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        if any(w in m["text"] for w in REFUSAL_EXCLUDE):
            continue
        found = REFUSAL_RE.search(m["text"]) or REFUSAL_GAP_RE.search(m["text"])
        if found:
            signals.append({
                "code": "SAFE_PAYMENT_REFUSAL",
                "signal": "안전결제 거부",
                "message_index": m.get("index", i),
                "match": found.group(),
                "evidence": m["text"],
                "weight": 2,
                "advice": "플랫폼 안전결제를 요청하세요. 거부한다면 거래를 다시 생각해 보세요.",
            })
    return signals


# 띄어쓰기와 무관하게 잡히도록 정규식 사용 (\s* = 공백 0개 이상)
PRESSURE_PATTERNS = [
    r"오늘\s*입금",
    r"오늘\s*안(에|으로)\s*입금",   # "오늘 안에", "오늘 안으로" 둘 다
    r"빨리\s*입금",
    r"(?<![가-힣])선\s*입금",       # 앞에 한글이 붙으면 제외 → "우선 입금"은 잡지 않음 (messenger.py와 같은 방식)
    r"먼저\s*입금",
    r"오늘\s*(까지|중으로|중에)\s*입금",               # "오늘까지 입금해주세요"
    r"입금(은|는)?\s*오늘\s*(까지|안에|안으로|중으로)",  # "입금 오늘까지 해주셔야 해요" (#57, 순서가 바뀐 문장)
    # ---- 블라인드 표본 미탐 보강 ----
    # 시간을 못 박는 재촉: "20분 안에 입금 주세요", "1시간 내로 송금 안 되면"
    r"\d+\s*(분|시간)\s*(안|내|이내)\S*\s*[^.?!,]{0,12}?(입금|송금|결제|보내|주시|주셔)",
    # 안 보내면 다른 사람에게 넘기겠다는 압박: "결제 안 하시면 다음 분께 넘길게요"
    r"(안|못)\s*(주시|하시|보내시|입금하시|송금하시)면[^.?!]{0,12}?(다른|다음)\s*(분|사람)",
    # 먼저 보내는 사람에게 팔겠다는 경쟁 유도: "먼저 입금하시는 분께 드려요"
    r"(먼저|빨리)\s*(보내|입금|송금|결제)\S*\s*분(께|한테|에게)",
    r"(?<!택배는\s)(?<!택배\s)(?<!발송\s)(?<!배송\s)\d+\s*시\s*마감",   # "3시 마감이에요" ("택배는 3시 마감"은 제외)
]
# 이 표현이 들어간 문장은 재촉이 아니라 입금 확인 안내 → 제외 (#43)
PRESSURE_EXCLUDE = ["확인했"]

# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_payment_pressure(messages: list[Message]) -> list[Signal]:
    """판매자가 입금을 재촉하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        if any(w in m["text"] for w in PRESSURE_EXCLUDE):
            continue
        for p in PRESSURE_PATTERNS:
            found = re.search(p, m["text"])
            if found:
                signals.append({
                    "code": "PAYMENT_PRESSURE",
                    "signal": "빠른 입금 요구",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "입금을 서두르지 마세요. 물건과 판매자 정보를 먼저 확인하세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals


BANK_TRANSFER_ONLY_PATTERNS = ["계좌로만", "계좌이체만", "이체로만", "현금으로만",
                               "무통장입금으로만", "무통장 입금으로만", "무통장으로만"]   # #71
# "계좌이체만 아니면 다 돼요"처럼 오히려 다른 방법을 허용하는 문장은 제외 (#43)
BANK_TRANSFER_EXCLUDE = ["아니면"]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_bank_transfer_only(messages: list[Message]) -> list[Signal]:
    """판매자가 계좌이체(현금)로만 거래하자고 고집하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        if any(w in m["text"] for w in BANK_TRANSFER_EXCLUDE):
            continue
        for p in BANK_TRANSFER_ONLY_PATTERNS:
            if p in m["text"]:
                signals.append({
                    "code": "BANK_TRANSFER_ONLY",
                    "signal": "계좌이체만 요구",
                    "message_index": m.get("index", i),
                    "match": p,
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "계좌이체만 고집한다면 플랫폼 안전결제를 요청하세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals


# ---- #71 추가 입금 요구 ----
# 이미 입금한 구매자에게 수수료·환불·오류 등을 핑계로 돈을 한 번 더 보내게 하는 수법
# - "다시/한 번 더/재" + 입금·송금·결제 : "다시 입금해 주셔야 해요", "재결제"
# - 입금·송금·결제 + "다시/한 번 더" + 하다·완료 : "결제를 한 번 더 완료하셔야 해요"
# - "추가 입금", "추가로 3천원 송금", "3천원 더 보내주셔야"
EXTRA_PAYMENT_PATTERNS = [
    r"(다시|한\s*번\s*더|(?<![가-힣])재)\s*(입금|송금|결제)",   # "현재 결제"의 "재"는 제외
    r"(입금|송금|결제)(을|를)?\s*(다시|한\s*번\s*더)\s*(해|하|완료|진행|보내)",   # "입금 다시 확인해 볼게요"는 제외
    r"추가\s*(로)?[^.?!,]{0,8}?(입금|송금|결제)",                       # "추가로 3천원 송금해 주셔야"
    r"\d+\s*(천|만)?\s*원\s*(만)?\s*더\s*(입금|송금|결제|보내)",           # "3천원 더 보내주셔야"
    r"\d+\s*(천|만)\s*(\d+\s*(천|백)\s*)?원?\s*다시\s*(보내|넣어)",       # "5만 2천원 다시 보내주세요"
    r"(보관료|보증금|인증비|인증금|해제비|등록비)[^.?!]{0,20}?(넣어|입금|송금|보내)",   # "보증금은 계좌로 넣어주시면"
]
# 환불·반환을 미끼로 돈을 더 보내게 하는 말 (아래 목록은 EXTRA_PAYMENT_EXCLUDE와 상관없이 검사)
# - "돌려받으시려면 ... 보내주셔야": 돈을 돌려받으려면 먼저 더 보내라는 요구
# - "넣어주시면 ... 돌려드려요"   : 지금 더 넣으면 나중에 돌려주겠다는 약속
REFUND_BAIT_PATTERNS = [
    r"(환불|반환|돌려)\s*받\S*[^.?!]{0,20}?(보내|입금|송금|넣어)\s*주셔야",
    r"(넣어\s*주|넣고|입금해\s*주|송금해\s*주)\S*[^.?!,]{0,20}?(돌려|환불|반환)\s*(해\s*)?드",   # "보내주시면(반품) 환불해 드려요"는 제외
]
# 판매자가 돈을 돌려주는 말("다시 입금해 드릴게요")은 추가 입금 요구가 아님
# ("부탁드려요"는 요구라서 제외하면 안 됨 → "해 드려요"처럼 앞에 "해"가 붙은 것만)
EXTRA_PAYMENT_EXCLUDE = ["드릴게", "드릴께", "해 드려요", "해드려요", "해 드렸", "해드렸"]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_extra_payment(messages: list[Message]) -> list[Signal]:
    """판매자가 이미 입금한 구매자에게 추가 입금을 요구하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        # 판매자가 돌려주는 말이면 일반 패턴은 건너뛰고, 환불 미끼 패턴만 검사
        returning = any(w in m["text"] for w in EXTRA_PAYMENT_EXCLUDE)
        patterns = REFUND_BAIT_PATTERNS if returning else EXTRA_PAYMENT_PATTERNS + REFUND_BAIT_PATTERNS
        for p in patterns:
            found = re.search(p, m["text"])
            if found:
                signals.append({
                    "code": "EXTRA_PAYMENT",
                    "signal": "추가 입금 요구",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 3,        # 실제 피해로 바로 이어지는 수법
                    "advice": "추가 입금을 요구하면 더 보내지 마세요. 이미 보낸 돈은 은행과 경찰(112)에 바로 신고하세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals


# ---- #71 예금주 불일치 ----
# 판매자 본인이 아닌 다른 사람 명의 계좌로 입금하게 하는 수법 (대포통장)
# - "예금주/명의" 뒤에 "달라요/다른" : "예금주 이름이 달라요"
# - 가족·지인 + 계좌/명의              : "가족 계좌라", "어머니 명의로"
# - "제 명의 계좌로 보내주시면 돼요"는 본인 계좌라 잡지 않음 (목록에 "제"가 없음)
ACCOUNT_NAME_MISMATCH_PATTERNS = [
    r"(예금주|명의)[^.?!]{0,8}?(달라|다르|다른)",
    r"(가족|엄마|어머니|아빠|아버지|부모님|와이프|아내|남편|동생|누나|언니|오빠|지인|친구|사촌)\s*(의\s*)?(계좌|명의|통장)",
    r"(다른\s*사람|타인)\s*(의\s*)?(계좌|명의|통장)",
]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_account_name_mismatch(messages: list[Message]) -> list[Signal]:
    """판매자가 본인이 아닌 다른 사람 명의 계좌로 입금하라고 하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        for p in ACCOUNT_NAME_MISMATCH_PATTERNS:
            found = re.search(p, m["text"])
            if found:
                signals.append({
                    "code": "ACCOUNT_NAME_MISMATCH",
                    "signal": "예금주 불일치",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 2,
                    "advice": "판매자 이름과 예금주가 다르면 입금하지 마세요. 판매자 본인 명의 계좌인지 확인하세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals


# ---- 블라인드 표본 미탐 보강: 앞말을 받아서 하는 안전결제 거부 ----
# 구매자: "안전결제로 해도 될까요?" → 판매자: "그건 수수료가 붙어서 제가 손해예요"
# 판매자 문장에 "안전결제"가 없어도, 바로 앞 구매자 말이 안전결제·앱 결제를 물었으면 거부로 봄
SAFE_PAYMENT_ASK_RE = re.compile(r"안전\s*(결제|거래)|번개\s*페이|안심\s*(결제|거래)|앱\s*(에서|으로)")
REFUSAL_REPLY_RE = re.compile(
    r"^(그건|그거는|그거|그건요|앱은|앱으로는)[^.?!]{0,20}?"
    r"(수수료|손해|비싸|번거|정산이?\s*늦|안\s*돼|안\s*해|어려워|못\s*해|불가)"
)


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_safe_payment_refusal_reply(messages: list[Message]) -> list[Signal]:
    """구매자가 안전결제를 물었는데 판매자가 '그건 ~'으로 받아서 거부하는 표현"""
    signals = []
    last_buyer = ""     # 바로 앞 구매자 말 (판매자 답이 무엇을 가리키는지 알기 위함)
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":
            last_buyer = m["text"]
            continue
        found = REFUSAL_REPLY_RE.search(m["text"].strip())
        if found and SAFE_PAYMENT_ASK_RE.search(last_buyer):
            signals.append({
                "code": "SAFE_PAYMENT_REFUSAL",
                "signal": "안전결제 거부",
                "message_index": m.get("index", i),
                "match": found.group(),
                "evidence": m["text"],
                "weight": 2,
                "advice": "플랫폼 안전결제를 요청하세요. 거부한다면 거래를 다시 생각해 보세요.",
            })
        last_buyer = ""     # 판매자가 한 번 답하면 앞말 연결은 끝
    return signals


# ---- 블라인드 표본 미탐 보강: 물건 받기 전 구매확정 요구 ----
# 안전결제는 구매확정을 눌러야 판매자에게 돈이 넘어가므로, 받기 전에 확정을 재촉하면 위험
PURCHASE_CONFIRM_FIRST_PATTERNS = [
    r"(구매\s*)?확정[^.?!]{0,8}?(먼저|미리|부터)",
    r"(먼저|미리)[^.?!]{0,8}?(구매\s*)?확정",
    r"(받기|도착하기|수령하기)\s*전에?[^.?!]{0,10}?확정",
]


# [수업 적용] 4강 Decorator — @detector로 탐지기 자동 등록
@detector
def detect_purchase_confirm_first(messages: list[Message]) -> list[Signal]:
    """판매자가 물건을 받기 전에 구매확정을 먼저 눌러 달라고 하는 표현"""
    signals = []
    for i, m in enumerate(messages):
        if m["speaker"] == "buyer":     # 구매자 발언은 검사하지 않음
            continue
        for p in PURCHASE_CONFIRM_FIRST_PATTERNS:
            found = re.search(p, m["text"])
            if found:
                signals.append({
                    "code": "PURCHASE_CONFIRM_FIRST",
                    "signal": "수령 전 구매확정 요구",
                    "message_index": m.get("index", i),
                    "match": found.group(),
                    "evidence": m["text"],
                    "weight": 3,        # 확정하면 안전결제 보호가 끝나 바로 피해로 이어짐
                    "advice": "물건을 받고 확인하기 전에는 구매확정을 누르지 마세요.",
                })
                break   # 한 문장에서 같은 신호는 한 번만
    return signals

