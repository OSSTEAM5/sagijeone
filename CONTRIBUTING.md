# 협업 규칙

우리 팀은 **`main`에 직접 push하지 않습니다.** 모든 작업은 아래 흐름을 따릅니다.

```
Issue 만들기 → 담당자 지정 → 브랜치 생성 → 개발/커밋 → PR → 리뷰 1명 승인 → Merge
```

---

## 1. Issue

- 작업을 시작하기 전에 Issue부터 만듭니다. (템플릿: 기능 / 버그)
- 담당자(Assignees)와 라벨을 지정합니다.
- Issue 하나는 **며칠 안에 끝낼 수 있는 크기**로 나눕니다.
  - ❌ `텍스트 분석 구현`
  - ✅ `안전결제 거부 탐지 함수 구현`

## 2. 브랜치

`main`에서 새 브랜치를 만들고, 이름은 `종류/이슈번호-짧은설명` 형식으로 짓습니다.

| 종류 | 용도 | 예시 |
|---|---|---|
| `feat` | 새 기능 | `feat/12-safe-payment-detector` |
| `fix` | 버그 수정 | `fix/20-ocr-encoding` |
| `docs` | 문서 | `docs/3-readme-team` |
| `refactor` | 동작 변경 없는 코드 정리 | `refactor/25-risk-engine` |
| `test` | 테스트 | `test/30-false-positive-samples` |

## 3. 커밋 메시지

```
종류: 무엇을 했는지 (한 줄)
```

예시:
```
feat: 안전결제 거부 탐지 함수 추가
fix: 부정 표현이 있으면 계좌이체 신호가 뜨지 않도록 수정
docs: README 팀원 표 추가
```

- 한 커밋에는 하나의 작업만 담습니다.
- `수정`, `ㅇㅇ`, `final` 같은 메시지는 쓰지 않습니다.

## 4. Pull Request

- PR 제목은 커밋 메시지와 같은 형식으로 씁니다.
- 본문에 `Closes #이슈번호`를 적으면 Merge될 때 Issue가 자동으로 닫힙니다.
- **최소 1명의 승인**을 받아야 Merge할 수 있습니다.
- PR은 작게 만듭니다. 변경이 너무 크면 리뷰하기 어렵습니다.

## 5. 리뷰

- 리뷰 요청을 받으면 **24시간 안에** 확인합니다.
- 코멘트는 코드에 대해 씁니다. 사람을 평가하지 않습니다.
- 질문도 좋은 리뷰입니다. ("이 정규식은 어떤 경우를 잡는 건가요?")
- 승인할 때는 `Approve`, 수정이 필요하면 `Request changes`를 사용합니다.

## 6. 자주 쓰는 Git 명령어

```bash
# 1) 최신 main 받기
git switch main
git pull origin main

# 2) 작업 브랜치 만들기
git switch -c feat/12-safe-payment-detector

# 3) 작업 후 커밋
git add .
git commit -m "feat: 안전결제 거부 탐지 함수 추가"

# 4) GitHub에 올리기 → 웹에서 PR 생성
git push origin feat/12-safe-payment-detector

# 5) 내 브랜치에 최신 main 반영하기 (충돌이 날 때)
git switch main
git pull origin main
git switch feat/12-safe-payment-detector
git merge main
```

## 7. 막히면

Discord `#질문-오류` 채널에 **에러 메시지 전문 + 무엇을 하다가 생겼는지**를 같이 올려주세요.
