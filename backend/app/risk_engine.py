"""[5번 담당] Risk Engine — 신호들을 종합해 등급과 권장 행동을 만든다

점수는 위험 신호의 정도를 표현할 뿐, 사기 확률이 아닙니다.
"""
from app.models import Signal

NOTICE = "이 결과는 위험 신호를 알려드릴 뿐, 판매자가 사기꾼이라는 뜻은 아닙니다."


def build_result(signals: list[Signal]) -> dict:
    score = sum(s["weight"] for s in signals)
    kinds = {s["signal"] for s in signals}

    if not signals:
        level = "특이 신호 없음"
    elif len(kinds) >= 2 or score >= 4:   # 서로 다른 신호가 함께 나타나면 상향 (복합 신호)
        level = "여러 위험 신호"
    else:
        level = "주의"

    advice = list(dict.fromkeys(s["advice"] for s in signals))   # 순서 유지하며 중복 제거
    return {"level": level, "score": score, "signals": signals, "advice": advice, "notice": NOTICE}
