"""[4번 담당] URL 위험 신호 탐지기 — 지금은 빈 탐지기(항상 신호 없음)"""
from app.detectors.registry import detector
from app.models import Message, Signal


@detector
def detect_suspicious_url(messages: list[Message]) -> list[Signal]:
    # TODO(4번): 단축 URL, 공식 도메인 사칭, IP 주소 URL 검사
    return []
