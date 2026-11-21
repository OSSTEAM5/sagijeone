"""전체 흐름을 연결하는 곳 (5번 관리)

(4번 OCR 오타 보정) → 1번 파서 → 2·4번 탐지기 → 3번 문맥 처리 → 5번 Risk Engine
각자 형식만 지키면, 내부 구현이 바뀌어도 이 파일은 바뀌지 않습니다.
"""
from app.context import apply_context
from app.detectors import detectors
from app.input.chat_parser import parse_chat
from app.input.ocr_fix import fix_ocr_typos
from app.risk_engine import build_result


def analyze(text: str) -> dict:
    text = fix_ocr_typos(text)          # 캡처에서 읽은 글자 오타 보정 (카록 → 카톡)
    messages = parse_chat(text)
    # [수업 적용] 2강 Higher-Order Function — 함수 리스트를 돌며 호출
    signals = [s for detect in detectors for s in detect(messages)]
    signals = apply_context(messages, signals)
    return build_result(signals)
