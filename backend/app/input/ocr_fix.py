"""[4번 담당] OCR 오타 보정 — 캡처에서 읽은 글자 중 자주 틀리는 단어를 바로잡기

OCR 실험(docs/ocr_experiment.md)에서 "카톡"을 "카록"으로 읽어
외부 메신저 유도 신호를 놓쳤습니다. 탐지 전에 이런 오타를 고칩니다.

규칙: 실제로 쓰이는 단어는 넣지 않습니다. (정상 문장이 바뀌면 안 됨)
      → 위험 신호와 관련된 단어의 '틀린 모양'만 넣습니다.
"""

# [수업 적용] 2강 Function Annotations — 오타 목록 형식(dict[str, str])을 타입 힌트로 명시
# 새 오타는 딕셔너리에 한 줄만 추가하면 됨 (긴 단어부터 고치도록 순서대로 적기)
# 왼쪽: OCR이 잘못 읽은 모양, 오른쪽: 원래 단어
OCR_TYPOS: dict[str, str] = {
    "카카오록": "카카오톡",   # 긴 단어를 먼저 고쳐야 "카록"보다 먼저 처리됨
    "카록": "카톡",           # 실험에서 실제로 나온 오타 (톡 → 록)
    "안전걸제": "안전결제",
    "안전결재": "안전결제",
    "계솨": "계좌",
    "게좌": "계좌",
}


def fix_ocr_typos(text: str) -> str:
    """OCR_TYPOS에 있는 틀린 단어를 원래 단어로 바꾼 문장을 돌려줌"""
    for wrong, right in OCR_TYPOS.items():
        text = text.replace(wrong, right)
    return text
