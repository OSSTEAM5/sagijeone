"""팀 전체가 약속한 데이터 형식 (10/18 형식 확정)

- Message: 1번(입력 처리)이 만들고, 2·3·4번이 사용
- Signal : 2·4번(탐지기)이 만들고, 3번(문맥)·5번(Risk Engine)·6번(화면)이 사용

규칙: 필드 추가는 OK, 이름 변경·삭제는 금지 (다른 사람 코드가 깨짐)
"""
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

Speaker = Literal["seller", "buyer", "unknown"]


# [수업 적용] 2강 Function Annotations — 형식을 타입 힌트로 명시해서
# 탐지 함수 시그니처를 (messages: list[Message]) -> list[Signal] 로 통일
class Message(TypedDict):
    index: int         # 몇 번째 메시지인지 (0부터)
    speaker: Speaker   # 판매자 / 구매자 / 알 수 없음
    text: str          # 한 사람이 보낸 한 줄


class Signal(TypedDict):
    code: str          # 코드에서 비교할 때 쓰는 영문 이름 (예: "SAFE_PAYMENT_REFUSAL")
    signal: str        # 화면에 보여줄 한글 이름 (예: "안전결제 거부")
    message_index: int # 근거가 몇 번째 메시지인지 (Message의 index)
    match: str         # 탐지기가 실제로 찾은 표현 (예: "안전결제는 안")
    evidence: str      # 근거가 된 원문 문장
    weight: int        # 위험 정도: 1 참고 / 2 주의 / 3 강한 신호
    advice: str        # 사용자에게 권할 행동


# ---- API 요청/응답 형식 (6번 프론트엔드가 보는 JSON) ----
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, examples=["판매자: 안전결제는 수수료 때문에 안 해요"])


class SignalOut(BaseModel):
    code: str = ""             # 새 필드는 기본값을 둬서, 아직 안 바꾼 탐지기가 있어도 에러가 나지 않게 함
    signal: str
    message_index: int = -1
    match: str = ""
    evidence: str
    weight: int
    advice: str


class AnalyzeResponse(BaseModel):
    level: str                      # "특이 신호 없음" / "주의" / "여러 위험 신호"
    score: int                      # 위험 정도 표현용 점수 (사기 확률이 아님)
    signals: list[SignalOut]        # 발견된 위험 신호와 근거
    advice: list[str]               # 권장 행동 (중복 제거)
    notice: str                     # 단정하지 않는다는 안내 문구
