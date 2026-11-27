"""[3번 담당] 오탐·미탐 측정 스크립트 (이슈 #72)

사용법 (저장소 맨 위 폴더에서):
    py scripts/measure.py

하는 일
1. 표본 파일(docs/samples.md, docs/samples_blind/*.md)에서 대화와 기대 결과를 읽는다
2. 대화마다 analyze()를 돌린다
3. 오탐률·미탐률, 신호 종류별 잡은 수/놓친 수, 틀린 대화 목록을 docs/measurement.md에 표로 저장한다

용어
- 오탐: 정상 대화인데 신호가 하나라도 나옴
- 미탐: 위험 대화인데 신호가 하나도 안 나옴
"""
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.pipeline import analyze  # noqa: E402

SAMPLE_FILES = [ROOT / "docs" / "samples.md", *sorted((ROOT / "docs" / "samples_blind").glob("*.md"))]
OUT = ROOT / "docs" / "measurement.md"

# 표본에 한글로 적힌 기대 신호 → 탐지기 코드
# 표본을 낸 사람마다 부르는 이름이 조금씩 달라서 비슷한 이름을 모두 적어 둔다.
# 여기에 없는 이름은 "아직 탐지기가 없는 신호"로 따로 센다.
LABEL_TO_CODE = {
    "안전결제 거부": "SAFE_PAYMENT_REFUSAL",
    "빠른 입금 요구": "PAYMENT_PRESSURE",
    "선입금 요구": "PAYMENT_PRESSURE",
    "계좌이체만 요구": "BANK_TRANSFER_ONLY",
    "외부 메신저 이동 유도": "EXTERNAL_MESSENGER",
    "외부 메신저 유도": "EXTERNAL_MESSENGER",
    "공식 사이트와 비슷한 주소": "URL_LOOKALIKE",
    "공식 사이트 사칭 의심": "URL_IMPERSONATION",
    "공식 사이트 사칭": "URL_IMPERSONATION",
    "단축 URL": "URL_SHORTENER",
    "IP 주소로 된 링크": "URL_IP_ADDRESS",
    "IP 주소 링크": "URL_IP_ADDRESS",
    "선입금 재촉": "PAYMENT_PRESSURE",
    "추가 입금 요구": "EXTRA_PAYMENT",
    "수수료 명목 추가 입금 요구": "EXTRA_PAYMENT",
    "보증금 명목 추가 입금 유도": "EXTRA_PAYMENT",
    "결제 후 대금 보관료 요구": "EXTRA_PAYMENT",
    "환불을 조건으로 추가 송금 유도": "EXTRA_PAYMENT",
    "예금주 불일치": "ACCOUNT_NAME_MISMATCH",
    "타인 명의 계좌": "ACCOUNT_NAME_MISMATCH",
    "타인 명의 계좌 유도": "ACCOUNT_NAME_MISMATCH",
    "수령 전 구매확정 요구": "PURCHASE_CONFIRM_FIRST",
    # 결제 링크는 URL 탐지기 4종 중 하나라도 잡으면 맞힌 것으로 본다
    "가짜 결제 링크": "URL_ANY",
    "판매자가 보낸 결제 링크": "URL_ANY",
    "가짜 고객센터 링크": "URL_ANY",
    "가짜 배송조회 링크": "URL_ANY",
    "링크에서 로그인·인증 요구": "LINK_CREDENTIAL",
    "가짜 안전결제 피싱 링크": "URL_ANY",
    "직거래 파기 후 선입금 유도": "PAYMENT_PRESSURE",
    "개인정보 및 재인증 요구": "LINK_CREDENTIAL",
    "환불 미끼": "EXTRA_PAYMENT",
    "물건 수령 전 구매확정 요구": "PURCHASE_CONFIRM_FIRST",
}
URL_CODES = {"URL_LOOKALIKE", "URL_IMPERSONATION", "URL_SHORTENER", "URL_IP_ADDRESS"}
CODE_NAME = {
    "SAFE_PAYMENT_REFUSAL": "안전결제 거부",
    "PAYMENT_PRESSURE": "빠른 입금 요구",
    "BANK_TRANSFER_ONLY": "계좌이체만 요구",
    "EXTERNAL_MESSENGER": "외부 메신저 이동 유도",
    "URL_LOOKALIKE": "공식 사이트와 비슷한 주소",
    "URL_IMPERSONATION": "공식 사이트 사칭 의심",
    "URL_SHORTENER": "단축 URL",
    "URL_IP_ADDRESS": "IP 주소로 된 링크",
    "EXTRA_PAYMENT": "추가 입금 요구",
    "ACCOUNT_NAME_MISMATCH": "예금주 불일치",
    "PURCHASE_CONFIRM_FIRST": "수령 전 구매확정 요구",
    "LINK_CREDENTIAL": "링크에서 로그인·인증 요구",
    "URL_ANY": "의심 링크 (URL 탐지기 중 하나)",
}

# samples.md 형식:  ## N01. 정상 — 기본 정상 대화
HEAD_MAIN = re.compile(r"^## ([NR]\d+)\. (정상|위험)")
# samples_blind 형식: ## T-정윤재-01 | 위험 | 기대 신호: 외부 메신저 유도, 추가 입금 요구
HEAD_BLIND = re.compile(r"^## (\S+)\s*\|\s*(정상|위험)\s*\|\s*기대 신호:\s*(.*)$")
# 대화 한 줄 (``` 상자 없이 바로 적은 표본도 읽기 위해 사용)
CHAT_LINE = re.compile(r"^(구매자|판매자)\s*:")


# [수업 적용] 2강 Function Annotations — 표본 한 개를 dict로, 여러 개를 list[dict]로 돌려준다고 타입 힌트로 명시
def read_samples(path: Path) -> list[dict]:
    """표본 파일 하나에서 {번호, 구분, 대화, 기대 코드, 미지원 신호}를 읽는다."""
    samples: list[dict] = []
    cur = None
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        m_main, m_blind = HEAD_MAIN.match(line), HEAD_BLIND.match(line)
        if m_main or m_blind:
            m = m_main or m_blind
            cur = {"id": m.group(1), "kind": m.group(2), "lines": [],
                   "expected": set(), "unsupported": [], "file": path.name}
            if m_blind:
                # [수업 적용] 2강 지능형 리스트(List Comprehension) — 쉼표로 나눈 이름에서 빈칸·'없음' 제거
                labels = [x.strip() for x in m_blind.group(3).split(",") if x.strip() and x.strip() != "없음"]
                cur["expected"] = {LABEL_TO_CODE[x] for x in labels if x in LABEL_TO_CODE}
                cur["unsupported"] = [x for x in labels if x not in LABEL_TO_CODE]
            samples.append(cur)
            in_code = False
            continue
        if cur is None:
            continue
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or CHAT_LINE.match(line):
            cur["lines"].append(line)
        elif line.startswith("| 신호 |"):
            # samples.md 의 "| 신호 | 기대 | 실제 |" 줄에서 기대 칸의 `코드`만 꺼낸다
            expected_cell = line.split("|")[2]
            cur["expected"] = set(re.findall(r"`([A-Z_]+)`", expected_cell))
    return [s for s in samples if s["lines"]]


def measure(samples: list[dict]) -> dict:
    """모든 표본에 analyze()를 돌리고 숫자를 센다."""
    caught, missed, extra = Counter(), Counter(), Counter()
    unsupported = Counter()
    wrong = []
    fp = fn = 0
    for s in samples:
        result = analyze("\n".join(s["lines"]))
        # [수업 적용] 2강 Set 컴프리헨션 — 실제로 나온 신호 코드만 모음 (중복 제거)
        actual = {sig["code"] for sig in result["signals"]}
        if "URL_ANY" in s["expected"]:
            # "결제 링크"처럼 링크 종류를 정하지 않은 기대 신호는 실제로 나온 URL 신호로 바꿔서 비교
            found = actual & URL_CODES
            s["expected"] = (s["expected"] - {"URL_ANY"}) | (found or {"URL_ANY"})
        s["actual"], s["level"] = actual, result["level"]

        is_fp = s["kind"] == "정상" and bool(actual)
        is_fn = s["kind"] == "위험" and not actual
        fp += is_fp
        fn += is_fn

        for code in s["expected"]:
            (caught if code in actual else missed)[code] += 1
        for code in actual - s["expected"]:
            extra[code] += 1
        unsupported.update(s["unsupported"])

        if is_fp or is_fn or actual != s["expected"]:
            wrong.append(s)

    normal = [s for s in samples if s["kind"] == "정상"]
    risky = [s for s in samples if s["kind"] == "위험"]
    return {"normal": len(normal), "risky": len(risky), "fp": fp, "fn": fn,
            "caught": caught, "missed": missed, "extra": extra,
            "unsupported": unsupported, "wrong": wrong}


def pct(a: int, b: int) -> str:
    return f"{a / b * 100:.1f}%" if b else "-"


def names(codes) -> str:
    return ", ".join(f"{CODE_NAME.get(c, c)}" for c in sorted(codes)) or "없음"


def to_markdown(r: dict, files: list[Path]) -> str:
    out = [
        "# 오탐·미탐 측정 결과 (이슈 #72)",
        "",
        f"- 측정일: {date.today().isoformat()}",
        f"- 표본 파일: {', '.join(f'`{p.relative_to(ROOT).as_posix()}`' for p in files)}",
        "- 다시 만들기: 저장소 맨 위 폴더에서 `py scripts/measure.py`",
        "",
        "## 요약",
        "",
        "| 항목 | 값 | 뜻 |",
        "|---|---|---|",
        f"| 전체 대화 | {r['normal'] + r['risky']}개 | 정상 {r['normal']}개 / 위험 {r['risky']}개 |",
        f"| **오탐률** | **{pct(r['fp'], r['normal'])}** ({r['fp']}/{r['normal']}) | 정상 대화 중 신호가 나온 비율 |",
        f"| **미탐률** | **{pct(r['fn'], r['risky'])}** ({r['fn']}/{r['risky']}) | 위험 대화 중 신호를 하나도 못 잡은 비율 |",
        "",
        "## 신호 종류별",
        "",
        "| 신호 | 코드 | 잡은 수 | 놓친 수 | 기대 안 했는데 나온 수 |",
        "|---|---|---|---|---|",
    ]
    for code, name in CODE_NAME.items():
        out.append(f"| {name} | `{code}` | {r['caught'][code]} | {r['missed'][code]} | {r['extra'][code]} |")

    if r["unsupported"]:
        out += ["", "## 아직 탐지기가 없는 신호", "",
                "표본에는 적혀 있지만 지금 코드에 탐지기가 없어서 위 표에서 뺀 신호입니다.", "",
                "| 신호 이름 (표본에 적힌 그대로) | 나온 횟수 |", "|---|---|"]
        out += [f"| {name} | {n} |" for name, n in r["unsupported"].most_common()]

    out += ["", "## 틀린 대화 목록", ""]
    if not r["wrong"]:
        out.append("틀린 대화가 없습니다.")
    else:
        out += ["| 번호 | 구분 | 기대 | 실제 | 왜 틀렸나 |", "|---|---|---|---|---|"]
        for s in r["wrong"]:
            if s["kind"] == "정상" and s["actual"]:
                why = "오탐"
            elif s["kind"] == "위험" and not s["actual"]:
                why = "미탐"
            else:
                why = "신호가 다름"
            exp = names(s["expected"]) if s["expected"] or not s["unsupported"] else ""
            if s["unsupported"]:
                exp += (" + " if exp else "") + f"탐지기 없음: {', '.join(s['unsupported'])}"
            out.append(f"| {s['id']} | {s['kind']} | {exp} | {names(s['actual'])} | {why} |")
    out.append("")
    return "\n".join(out)


def main() -> None:
    files = [p for p in SAMPLE_FILES if p.exists()]
    # [수업 적용] 2강 지능형 리스트 — 여러 파일의 표본을 한 리스트로 펼침
    per_file = {p: read_samples(p) for p in files}
    for p, found in per_file.items():
        mark = "" if found else "  ← 대화를 하나도 못 읽음! 파일 형식 확인 필요"
        print(f"{p.name}: {len(found)}개{mark}")
    samples = [s for found in per_file.values() for s in found]
    r = measure(samples)
    OUT.write_text(to_markdown(r, files), encoding="utf-8")

    print(f"대화 {len(samples)}개 측정 (정상 {r['normal']} / 위험 {r['risky']})")
    print(f"오탐률 {pct(r['fp'], r['normal'])}  미탐률 {pct(r['fn'], r['risky'])}  틀린 대화 {len(r['wrong'])}개")
    print(f"결과 저장: {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
