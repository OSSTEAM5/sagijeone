/**
 * [1번 담당] 채팅 캡처 → 대화 텍스트 (이슈 #70)
 *
 * 사용법 (6번 캡처 화면):
 *   <script src="ocr.js"></script>
 *   const chat = await recognizeChat(file);   // "판매자: ...\n구매자: ..."
 *
 * - 이미지는 서버로 보내지 않고 브라우저 안에서만 읽음 (Tesseract.js)
 * - Tesseract.js는 처음 부를 때 CDN에서 자동으로 불러옴 → 화면에 script 태그를 따로 안 넣어도 됨
 * - 실험 페이지(experiments/tesseract_trial.html)의 전처리·말풍선 묶기를 실제 캡처 5장에 맞게 고친 버전
 */

const TESSERACT_URL = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";

// [수업 적용] 5강 객체 참조·가변성 — 기준값은 Object.freeze로 묶어 실수로 바뀌지 않게 함
// 캡처마다 해상도가 달라서 픽셀 대신 "화면 크기 대비 비율"로 정함
const OCR_LAYOUT = Object.freeze({
  TOP_SKIP: 0.10,        // 위쪽 10%: 상태 표시줄, 채팅방 제목
  HEADER_SEARCH: 0.35,   // 위쪽 35% 안에서 상품 정보·버튼 문구를 찾으면 그 위는 모두 제외
  BOTTOM_SKIP: 0.03,     // 아래쪽 3%: 화면 끝
  FOOTER_SEARCH: 0.30,   // 아래쪽 30% 안에서 입력창·버튼 문구를 찾으면 그 아래는 모두 제외
  AVATAR_RIGHT: 0.15,    // 프로필 사진을 찾는 왼쪽 영역 (화면 너비의 15%)
  FULL_WIDTH: 0.12,      // 양쪽 끝 12% 안까지 꽉 찬 상자는 앱 안내문 (말풍선은 한쪽이 비어 있음)
  MIN_WIDTH: 900,        // 이보다 작은 캡처는 2배로 키워서 읽음 (작은 글자 인식률 개선)
  AVATAR_SIZE: 0.05,     // 왼쪽 끝 검은 덩어리가 화면 너비의 5%보다 높으면 프로필 사진 (글자 한 줄은 약 3%)
  THRESHOLD: 120,        // 검은 글자 전처리: 이보다 어두우면 글자
  WHITE_TEXT: 215,       // 흰 글자 전처리: R·G·B가 모두 이보다 밝으면 글자
  DARK: 110,             // 화면 평균 밝기가 이보다 어두우면 다크 모드
  SMALL_WORD: 0.9,       // 보통 글자 높이의 90%보다 작고 흐릿하게 읽힌 단어 = 시간·읽음 표시
  SPACE_GAP: 0.6,        // 글자 사이가 글자 높이의 60%보다 넓을 때만 띄어쓰기 (단어 안이 띄어지면 탐지가 깨져서 덜 띄우는 쪽으로)
  SAME_BUBBLE: 1.0,      // 위아래 줄 간격이 글자 높이보다 좁으면 같은 말풍선
});

// 시간·읽음 표시: 말풍선 옆에 붙는 작은 글자 (공백을 뺀 조각 전체가 이 모양이면 제외)
const TIME_PIECE = /^((오전|오후|오우|우후|으후|읽음)?\d{1,2}[:;.]?\d{2}|오전|오후|읽음)$/;
// 카카오톡 날짜 줄 ("2026년 11월 18일 수요일", 잘못 읽혀도 숫자 4개 + 요일로 끝남)
const DATE_PIECE = /\d{4}.*[월화수목금토일]요일$/;
// 상품 가격 줄 ("33,333원 무료배송", "100만원 (가격 제안 불가)")
// 가격 바로 뒤가 괄호·OO배송·줄 끝일 때만 → "3만 원까지는 가능해요" 같은 대화는 해당 안 됨
const PRICE = /^[\d,]+만?원(\(|[가-힣]{0,2}배송|$)/;

// ⚠️ 아래 문구들은 이 문구가 들어간 줄을 통째로 빼므로, 대화에도 나올 수 있는 말은 넣지 않음
//    (예: '판매중'은 "판매 중인가요?", '계좌전송'은 "계좌 전송해 드릴게요"에도 들어 있음)
// 채팅방 위쪽 버튼 (이 문구가 보이면 그 위는 대화가 아님)
const HEADER_PHRASES = Object.freeze(["약속잡기", "송금요청", "가격수정"]);
// 채팅방 아래쪽 입력창·버튼 (이 문구가 보이면 그 아래는 대화가 아님)
const FOOTER_PHRASES = Object.freeze([
  "메시지보내기", "메세지를입력", "메시지입력", "롯데방문택배", "중고나라안심보상", "채팅응답이더빠르고", "앱다운로드",
]);
// 대화 사이에 앱이 띄우는 안내 문구 (당근, 중고나라, 카카오톡 캡처에서 찾은 것)
const UI_PHRASES = Object.freeze([
  ...HEADER_PHRASES, ...FOOTER_PHRASES, "바로예약됩니다", "더알아보기", "꼭알아두세요", "안심결제쓰고",
]);
const removeSpaces = text => text.replace(/\s/g, "");
const hasPhrase = (text, phrases) => phrases.some(phrase => removeSpaces(text).includes(phrase));

let tesseractReady = null;   // 스크립트는 한 번만 불러옴
let workerReady = null;      // 언어 데이터(약 4.5MB)도 한 번만 불러오고 재사용

function loadTesseract() {
  if (window.Tesseract) return Promise.resolve();
  tesseractReady ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = TESSERACT_URL;
    script.onload = resolve;
    script.onerror = () => { tesseractReady = null; reject(new Error("Tesseract.js를 불러오지 못했어요")); };
    document.head.appendChild(script);
  });
  return tesseractReady;
}

async function getWorker() {
  await loadTesseract();
  workerReady ??= (async () => {
    const worker = await Tesseract.createWorker("kor+eng");
    await worker.setParameters({ preserve_interword_spaces: "1" });
    return worker;
  })().catch(err => { workerReady = null; throw err; });
  return workerReady;
}

/** File·Blob·<img>·이미지 주소 → 캔버스 (작은 캡처는 2배로 키움) */
async function toCanvas(image) {
  let source = image;
  if (typeof image === "string") source = await (await fetch(image)).blob();
  if (source instanceof Blob) source = await createImageBitmap(source);
  else if (source instanceof HTMLImageElement) await source.decode();

  const w = source.naturalWidth || source.width;
  const h = source.naturalHeight || source.height;
  const scale = w < OCR_LAYOUT.MIN_WIDTH ? 2 : 1;
  const canvas = document.createElement("canvas");
  canvas.width = w * scale;
  canvas.height = h * scale;
  canvas.getContext("2d").drawImage(source, 0, 0, canvas.width, canvas.height);
  return canvas;
}

function averageBrightness(canvas) {
  const d = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4 * 16) sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  return sum / (d.length / (4 * 16));
}

// [수업 적용] 2강 Higher-Order Function — "글자 픽셀인지 판단하는 함수"를 받아 흑백 이미지를 만드는 함수
function toBlackWhite(canvas, isText) {
  const out = document.createElement("canvas");
  out.width = canvas.width;
  out.height = canvas.height;
  const ctx = out.getContext("2d");
  ctx.drawImage(canvas, 0, 0);
  const pixels = ctx.getImageData(0, 0, out.width, out.height);
  const d = pixels.data;
  for (let i = 0; i < d.length; i += 4) {
    d[i] = d[i + 1] = d[i + 2] = isText(d[i], d[i + 1], d[i + 2]) ? 0 : 255;
  }
  ctx.putImageData(pixels, 0, 0);
  clearAvatars(ctx, out.width, out.height);
  return out;
}

/** 왼쪽 끝의 프로필 사진 지우기: 글자 한 줄보다 훨씬 높은 검은 덩어리를 흰색으로 덮음 */
function clearAvatars(ctx, width, height) {
  const band = Math.round(width * OCR_LAYOUT.AVATAR_RIGHT);
  const d = ctx.getImageData(0, 0, band, height).data;
  const tall = width * OCR_LAYOUT.AVATAR_SIZE;
  let start = -1;
  for (let y = 0; y <= height; y++) {
    let dark = false;
    for (let x = 0; y < height && x < band && !dark; x++) dark = d[(y * band + x) * 4] === 0;
    if (dark && start < 0) start = y;
    if (!dark && start >= 0) {
      if (y - start > tall) {
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, start, avatarRight(d, band, start, y), y - start);
      }
      start = -1;
    }
  }
}

/** 프로필 사진이 끝나는 x: 사진 오른쪽에 처음 나오는 빈 세로줄 (말풍선 글자는 지우지 않게) */
function avatarRight(d, band, y0, y1) {
  const isEmpty = x => { for (let y = y0; y < y1; y++) if (d[(y * band + x) * 4] === 0) return false; return true; };
  let x = 0;
  while (x < band && isEmpty(x)) x++;      // 사진 왼쪽 여백
  while (x < band && !isEmpty(x)) x++;     // 사진
  return x;
}

// [수업 적용] 3강 함수 지향 전략 — 전처리 방식마다 클래스 대신 함수 하나 (새 방식은 여기에 추가)
// 앱·말풍선 색마다 잘 읽히는 방식이 달라서 여러 방식으로 읽고 한글이 가장 많이 읽힌 쪽을 고름
const PREPROCESS = Object.freeze({
  // 당근 주황 말풍선(흰 글자) + 회색 말풍선(검은 글자): 원본이 가장 잘 읽힘
  "원본": canvas => canvas,
  // 카카오톡 노란 말풍선: 어두운 글자만 검게 남겨야 읽힘
  "검은 글자": canvas => toBlackWhite(canvas, (r, g, b) => 0.299 * r + 0.587 * g + 0.114 * b < OCR_LAYOUT.THRESHOLD),
  // 다크 모드: 말풍선 색과 상관없이 글자가 흰색 → 흰 글자만 검게 바꿔서 읽음
  "흰 글자": canvas => toBlackWhite(canvas, (r, g, b) => Math.min(r, g, b) > OCR_LAYOUT.WHITE_TEXT),
});

/** 화면 밝기에 따라 시도할 전처리 고르기 (다크 모드면 흰 글자, 아니면 원본·검은 글자) */
function preprocessFor(canvas) {
  const names = averageBrightness(canvas) < OCR_LAYOUT.DARK ? ["원본", "흰 글자"] : ["원본", "검은 글자"];
  return names.map(name => [name, PREPROCESS[name]]);
}

/** 단어들을 같은 줄끼리 모은 뒤, 가로로 멀리 떨어진 곳에서 끊어 조각으로 만듦 */
function wordsToPieces(words) {
  const rows = [];
  // [수업 적용] 2강 Higher-Order Function — sort()에 비교 함수를 넘겨 위→아래 순서로 정렬
  for (const w of [...words].sort((a, b) => a.cy - b.cy)) {
    const row = rows.find(r => Math.abs(r.cy - w.cy) < r.firstHeight / 2);
    if (row) row.words.push(w);
    else rows.push({ cy: w.cy, firstHeight: w.bottom - w.top, words: [w] });
  }

  const pieces = [];
  for (const row of rows) {
    const height = median(row.words.map(w => w.bottom - w.top));
    let piece = null;
    for (const w of row.words.sort((a, b) => a.left - b.left)) {
      // 같은 자리를 두 번 읽은 단어 정리 ('천천히히', '돼돼요' 방지)
      if (piece && w.left < piece.right) {
        if (piece.lastWord.endsWith(w.text)) continue;                  // '천천히' 뒤의 '히'
        if (w.text.startsWith(piece.lastWord)) {                         // '돼' 뒤의 '돼요'
          piece.text = piece.text.slice(0, -piece.lastWord.length) + w.text;
          piece.lastWord = w.text;
          piece.right = Math.max(piece.right, w.right);
          continue;
        }
      }
      // 단어 사이가 글자 높이의 2배보다 멀면 다른 상자 (예: 시간 | 말풍선)
      const gap = piece ? w.left - piece.right : Infinity;
      if (gap < height * 2) {
        // 한글은 글자 하나씩 나뉘어 나올 때가 많음 → 실제로 벌어진 곳만 띄어쓰기
        piece.text += (gap > height * OCR_LAYOUT.SPACE_GAP ? " " : "") + w.text;
        piece.sure += sureHangul(w);
        piece.right = w.right;
        piece.top = Math.min(piece.top, w.top);
        piece.bottom = Math.max(piece.bottom, w.bottom);
        piece.conf = Math.min(piece.conf, w.conf);
        piece.lastWord = w.text;
      } else {
        piece = { text: w.text, left: w.left, right: w.right, top: w.top, bottom: w.bottom, sure: sureHangul(w), conf: w.conf, lastWord: w.text };
        pieces.push(piece);
      }
    }
  }
  return pieces;
}

/** 대화가 시작되는 높이: 위쪽 10% 아래, 상품 정보·버튼 문구가 있으면 그 아래 */
function chatTop(pieces, height) {
  const header = pieces.filter(p => p.top < height * OCR_LAYOUT.HEADER_SEARCH &&
    (hasPhrase(p.text, HEADER_PHRASES) || PRICE.test(removeSpaces(p.text))));
  return Math.max(height * OCR_LAYOUT.TOP_SKIP, ...header.map(p => p.bottom));
}

/** 대화가 끝나는 높이: 아래쪽 3% 위, 입력창·버튼 문구가 있으면 그 위 */
function chatBottom(pieces, height) {
  const footer = pieces.filter(p => p.bottom > height * (1 - OCR_LAYOUT.FOOTER_SEARCH) && hasPhrase(p.text, FOOTER_PHRASES));
  return Math.min(height * (1 - OCR_LAYOUT.BOTTOM_SKIP), ...footer.map(p => p.top));
}

/** 조각 중 대화가 아닌 것(위·아래 영역, 시간, 잡음) 빼기 */
function isChatPiece(p, top, bottom, normal) {
  const cy = (p.top + p.bottom) / 2;
  if (cy < top || cy > bottom) return false;
  const text = removeSpaces(p.text);
  if (TIME_PIECE.test(text) || DATE_PIECE.test(text)) return false;
  // 'ee', '5' 같은 잡음
  if (!/[가-힣]/.test(text) && text.replace(/[^A-Za-z0-9]/g, "").length <= 2) return false;
  // '읽음'을 잘못 읽은 것 ('텔레', '빌레'): 대화 글자보다 작은 짧은 조각
  if (text.length <= 3 && p.bottom - p.top < normal * OCR_LAYOUT.SMALL_WORD) return false;
  // 한 글자인데 흐릿하게 읽힌 것 (아이콘 등)
  return !(text.length === 1 && p.conf < 70);
}

/** 위아래로 가깝고 같은 쪽에 있는 조각을 말풍선 하나로 묶고, 화자 정하기 */
function piecesToBubbles(pieces, width) {
  const bubbles = [];
  for (const p of pieces.sort((a, b) => a.top - b.top)) {
    const last = bubbles[bubbles.length - 1];
    const lineHeight = p.bottom - p.top;
    const overlaps = last && p.left < last.right && p.right > last.left;
    // 줄 간격이 글자 높이보다 좁으면 같은 말풍선의 다음 줄 (해상도와 상관없이 비율로 판단)
    if (overlaps && p.top - last.bottom < lineHeight * OCR_LAYOUT.SAME_BUBBLE) {
      last.text += " " + p.text;
      last.sure += p.sure;
      last.left = Math.min(last.left, p.left);
      last.right = Math.max(last.right, p.right);
      last.bottom = p.bottom;
    } else {
      bubbles.push({ ...p });
    }
  }
  const edge = width * OCR_LAYOUT.FULL_WIDTH;
  return bubbles
    // [수업 적용] 2강 map/filter — 앱 안내 상자(양쪽 끝까지 꽉 참, 안내 문구 포함)는 filter로 빼기
    // 안내 문구는 말풍선으로 묶은 뒤에 확인 → 두 줄짜리 안내의 둘째 줄도 같이 빠짐
    .filter(b => !(b.left < edge && b.right > width - edge) && !hasPhrase(b.text, UI_PHRASES))
    // 말풍선이 왼쪽에 붙어 있으면 판매자, 오른쪽에 붙어 있으면 구매자
    .map(b => ({ text: b.text, speaker: b.left < width - b.right ? "판매자" : "구매자", sure: b.sure }));
}

/** 캔버스 하나를 읽어서 말풍선 목록으로 */
async function readBubbles(worker, canvas) {
  const { data } = await worker.recognize(canvas);
  const words = data.words
    .map(w => ({
      text: w.text.trim(), conf: w.confidence,
      left: w.bbox.x0, right: w.bbox.x1, top: w.bbox.y0, bottom: w.bbox.y1,
      cy: (w.bbox.y0 + w.bbox.y1) / 2,
    }))
    .filter(w => w.text);
  // 보통 글자 높이: 한 글자짜리 단어는 낮게 잡히는 일이 많아서 위쪽 25% 지점 값을 씀
  const normal = percentile(words.filter(w => w.conf > 80 && /[가-힣]/.test(w.text)).map(w => w.bottom - w.top), 0.75);
  const kept = words.filter(w =>
    // 시간·읽음 표시를 영어로 잘못 읽은 것: 대화 글자보다 작고 흐릿함
    !(w.bottom - w.top < normal * OCR_LAYOUT.SMALL_WORD && w.conf < 75 && !/[가-힣0-9]/.test(w.text)) &&
    // 프로필 사진: 왼쪽 끝에서 영어·기호로 잘못 읽힘
    !(w.right < canvas.width * OCR_LAYOUT.AVATAR_RIGHT && !/[가-힣0-9]/.test(w.text)));
  const pieces = wordsToPieces(kept);
  const top = chatTop(pieces, canvas.height);
  const bottom = chatBottom(pieces, canvas.height);
  return piecesToBubbles(pieces.filter(p => isChatPiece(p, top, bottom, normal)), canvas.width);
}

function percentile(nums, ratio) {
  const sorted = [...nums].sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor((sorted.length - 1) * ratio)] : 0;
}
const median = nums => percentile(nums, 0.5);

// 전처리 고르기: 잡음까지 세지 않도록 "확신도 70 이상으로 읽힌 한글"만 셈
const sureHangul = w => (w.conf >= 70 ? (w.text.match(/[가-힣]/g) || []).length : 0);
const countSureHangul = bubbles => bubbles.reduce((n, b) => n + b.sure, 0);

/**
 * 자세한 결과까지 돌려주는 버전 (실험·측정용)
 * → { chat, preprocess, bubbles, seconds }
 */
async function recognizeChatDetail(image) {
  const start = performance.now();
  const [worker, canvas] = await Promise.all([getWorker(), toCanvas(image)]);

  let best = null;
  for (const [name, prepare] of preprocessFor(canvas)) {
    const bubbles = await readBubbles(worker, prepare(canvas));
    const hangul = countSureHangul(bubbles);
    if (!best || hangul > best.hangul) best = { preprocess: name, bubbles, hangul };
  }

  const chat = best.bubbles.map(b => `${b.speaker}: ${b.text}`).join("\n");
  return { chat, preprocess: best.preprocess, bubbles: best.bubbles, seconds: (performance.now() - start) / 1000 };
}

/**
 * 캡처 이미지 → "판매자: ...\n구매자: ..." (기존 텍스트 분석이 그대로 읽는 형식)
 * 글자를 하나도 못 찾으면 빈 문자열 → 화면에서 "직접 붙여넣어 주세요" 안내
 */
async function recognizeChat(imageFile) {
  return (await recognizeChatDetail(imageFile)).chat;
}
