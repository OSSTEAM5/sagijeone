"""[1번 담당] OCR 실험 — 채팅 캡처 → 텍스트 → parse_chat()

서비스에 붙이기 전 실험용 코드입니다. (easyocr는 requirements.txt에 아직 넣지 않음)

실행 (저장소 맨 위 폴더에서):
    py -m pip install easyocr
    py experiments/ocr_trial.py docs/images/ocr_sample_chat.png
"""
import sys
from pathlib import Path

import easyocr
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.input.chat_parser import parse_chat  # noqa: E402
from app.pipeline import analyze  # noqa: E402

HEADER_HEIGHT = 64      # 맨 위 채팅방 제목 영역은 대화가 아님
AVATAR_MAX_X = 60       # 왼쪽 프로필 아이콘("판") 영역
SAME_BUBBLE_GAP = 20    # 위아래 줄 간격이 이보다 작으면 같은 말풍선의 다음 줄


def read_boxes(image_path: str) -> list[dict]:
    """OCR로 글자 덩어리(박스)마다 위치와 텍스트를 뽑기"""
    reader = easyocr.Reader(["ko", "en"], gpu=False)
    boxes = []
    for points, text, conf in reader.readtext(image_path):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        boxes.append({"text": text, "conf": conf,
                      "left": min(xs), "right": max(xs), "top": min(ys), "bottom": max(ys)})
    return boxes


def naive_text(boxes: list[dict]) -> str:
    """방법 A: 위치 정보 없이 OCR 결과를 위에서부터 이어 붙이기"""
    # [수업 적용] 2강 Higher-Order Function — sorted()에 key 함수(lambda)를 넘겨 위→아래 순서로 정렬
    return "\n".join(b["text"] for b in sorted(boxes, key=lambda b: b["top"]))


def to_bubbles(boxes: list[dict], width: int) -> list[dict]:
    """방법 B: 가까운 줄끼리 말풍선으로 묶은 뒤, 말풍선 시작 위치로 화자 정하기

    줄 하나씩 화자를 정하면 '나요?'처럼 짧은 둘째 줄이 왼쪽으로 잘못 분류됨
    → 말풍선 단위로 먼저 묶고, 말풍선 왼쪽 끝이 화면 왼쪽 1/4 안이면 판매자, 아니면 구매자
    """
    bubbles: list[dict] = []
    for b in sorted(boxes, key=lambda b: (b["top"], b["left"])):
        if b["top"] < HEADER_HEIGHT or b["right"] < AVATAR_MAX_X:
            continue
        last = bubbles[-1] if bubbles else None
        if last and b["top"] - last["bottom"] < SAME_BUBBLE_GAP:
            last["text"] += " " + b["text"]        # 두 줄로 나뉜 말풍선 이어 붙이기
            last["bottom"] = max(last["bottom"], b["bottom"])
            last["left"] = min(last["left"], b["left"])
        else:
            bubbles.append({"text": b["text"], "bottom": b["bottom"], "left": b["left"]})
    for bubble in bubbles:
        bubble["speaker"] = "판매자" if bubble["left"] < width / 4 else "구매자"
    return bubbles


def main(image_path: str) -> None:
    width = Image.open(image_path).width
    boxes = read_boxes(image_path)

    print("## OCR 원본 결과 (박스별)")
    for b in sorted(boxes, key=lambda b: b["top"]):
        print(f"- ({b['left']:.0f}, {b['top']:.0f}) conf={b['conf']:.2f}  {b['text']}")

    print("\n## 방법 A: 텍스트만 이어 붙여서 parse_chat()")
    for m in parse_chat(naive_text(boxes)):
        print(m)

    chat = "\n".join(f"{b['speaker']}: {b['text']}" for b in to_bubbles(boxes, width))
    print("\n## 방법 B: 말풍선 위치로 화자 정한 텍스트")
    print(chat)
    print("\n## 방법 B → parse_chat()")
    for m in parse_chat(chat):
        print(m)

    result = analyze(chat)
    print(f"\n## 방법 B → analyze(): {result['level']} ({result['score']}점)")
    for s in result["signals"]:
        print(f"- {s['signal']} ← \"{s['evidence']}\"")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/images/ocr_sample_chat.png")
