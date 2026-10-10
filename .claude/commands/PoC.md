# /PoC — RAG 검색 품질 평가 스킬

`run_eval.py` 파이프라인을 실행해 RAG 검색 품질을 측정한다.

인자 예시:
- `/PoC` — 새 위키 파일 자동 감지 후 필요 시 DB 재빌드 + 전체 평가
- `/PoC quick` — DB 재빌드 없이 현재 DB로 즉시 재평가
- `/PoC rebuild` — 강제 DB 재빌드 후 전체 평가

---

## Step 0. 인자 파악

`$ARGUMENTS`를 확인한다:
- 없음 또는 기본 → Step 1부터 순서대로 진행 (자동 감지)
- `quick` → Step 3으로 바로 이동 (DB 재빌드 건너뜀)
- `rebuild` → Step 2로 바로 이동 (강제 재빌드)

---

## Step 1. 새 위키 파일 감지

`wiki/` 하위 `.md` 파일 목록을 수집한다 (index.md, log.md, todo.md, CLAUDE.md, graphify-out/ 제외).

`run_eval.py` 파일을 읽어 현재 DB에 인덱싱된 파일 수를 확인한다.
- 방법: 스크립트 내 `QA_PAIRS` 개수 확인 및 `chroma_db/` 폴더 존재 여부 확인

현재 위키 파일 수와 마지막 평가 시 파일 수를 비교해 신규 파일이 있으면:
- 신규 파일 목록을 사용자에게 보고
- "DB 재빌드가 필요합니다. 진행할까요?" 확인 후 Step 2 진행
- 없으면 Step 3으로 이동

---

## Step 2. Q&A 쌍 업데이트 + DB 재빌드

### 2-1. 신규 파일 내용 파악

새로 추가된 wiki 페이지를 읽는다.
각 페이지의 핵심 주제를 파악해 대표 검색 질문을 1개씩 설계한다.

질문 설계 원칙:
- 실제로 검색할 법한 자연어 질문
- 해당 페이지가 정답이 될 수 있을 만큼 구체적
- 다른 페이지와 혼동될 수 있는 범용어 질문은 피한다

### 2-2. run_eval.py 업데이트

`run_eval.py`를 열어 `QA_PAIRS_NEW` 리스트에 새 Q&A 쌍을 추가한다.
`QA_PAIRS_23`처럼 총 개수가 늘어나면 변수명도 맞게 업데이트한다.

### 2-3. DB 재빌드 실행

```
python -X utf8 run_eval.py
```

---

## Step 3. 평가 실행 (quick 모드)

quick 모드일 때는 기존 DB로 20개 Q&A만 재평가한다.
`run_eval.py`에서 Step 1 부분(기존 DB 평가)만 임시 스크립트로 실행한다:

```python
# quick_eval.py (임시 생성)
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()  # OPENAI_API_KEY는 .env에서 로드
# 기존 DB 로드 + 20개 Q&A 평가 실행
```

---

## Step 4. 결과 보고

평가 완료 후 아래 형식으로 보고한다:

```
## /PoC 평가 결과 — YYYY-MM-DD

| 항목 | 이번 | 직전 | 변화 |
|------|------|------|------|
| Recall@3 | XX% | XX% | ±X% |
| Recall@5 | XX% | XX% | ±X% |
| MRR | X.XXX | X.XXX | ±X.XXX |
| Q&A 쌍 수 | 23 | 20 | +3 |

### 실패 케이스
- ✗ [파일명]: [실패 이유 추정]

### 개선된 케이스 (직전 대비)
- [파일명]: RR X.XX → X.XX
```

---

## Step 5. 저장 여부 판단

다음 중 하나에 해당하면 wiki 로그 저장을 제안한다:
- 이전 대비 수치가 변한 경우
- Q&A 쌍이 추가된 경우
- 새로운 실패 패턴이 발견된 경우

저장 승인 시 → `wiki/log.md` 맨 앞에 평가 결과를 기록한다:

```
## [YYYY-MM-DD] PoC eval | RAG 검색 품질 평가

Q&A 쌍: N개 | Recall@3: XX% | Recall@5: XX% | MRR: X.XXX
직전 대비: R@3 ±X%, MRR ±X.XXX
실패: [파일명 목록]
DB: chroma_db_v[N] (위키 파일 N개 인덱싱)
```

---

## 절대 규칙

- 평가 중에는 `run_eval.py`와 결과 CSV만 수정 — 위키 원문(`wiki/`) 수정 금지
- API 키는 `.env`(또는 환경변수 `OPENAI_API_KEY`)에서만 읽는다 — 코드에 하드코딩 금지
- 평가 실행 전 반드시 Python 환경 확인 (`python -c "import chromadb"`)
- `chroma_db_v2/`가 존재하면 신규 평가는 `chroma_db_v3/`로 버전업 (덮어쓰기 금지)
- 결과 CSV는 `results/eval_YYYY-MM-DD.csv`로 날짜 포함 저장
