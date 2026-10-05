"""탐지기 등록소

[수업 적용] 4강 Decorator로 개선한 전략 패턴
- 강의의 @promotion 예제처럼, @detector를 붙인 함수가 detectors 리스트에 자동 등록됨
- 탐지기를 추가할 때 이 파일이나 main.py를 고칠 필요가 없음
- [수업 적용] 3강 함수 지향 전략 — 탐지 전략마다 클래스 대신 함수 하나
"""
from typing import Callable

from app.models import Message, Signal

Detector = Callable[[list[Message]], list[Signal]]

detectors: list[Detector] = []


def detector(func: Detector) -> Detector:
    """탐지 함수를 detectors 리스트에 등록하고 그대로 반환"""
    detectors.append(func)
    return func


def from_seller(messages: list[Message]) -> list[Message]:
    """판매자(또는 화자 미상) 발언만 고르기 — 구매자의 질문을 위험 신호로 잡지 않기 위함"""
    return [m for m in messages if m["speaker"] != "buyer"]
