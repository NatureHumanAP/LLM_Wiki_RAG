# rag-retrieval-eval

개인 지식베이스(LLM Wiki)에 RAG를 붙이고, 검색 품질을 **체감이 아닌 지표로** 비교·개선한 평가 파이프라인입니다.

> 평가 대상 문서(`wiki/`, 77개 페이지)는 개인 지식베이스라 이 저장소에 포함하지 않습니다.
> 평가 방법, 코드, QA 셋, 버전별 결과만 공개합니다.

## 결과 요약

같은 31개 QA 벤치마크로 버전별 Retrieval 품질을 비교했습니다.

| 버전 | 변경 | Hit@1 | Recall@3 | Recall@5 | MRR | Fβ(β=2) |
|------|------|-------|----------|----------|-----|---------|
| v2.1 | 로컬 임베딩 (`paraphrase-multilingual-MiniLM-L12-v2`) | 54.8% | 80.6% | 100.0% | 0.692 | 85.9% |
| v2.2 | OpenAI 임베딩 (`text-embedding-3-small`) | 71.0% | 90.3% | 93.5% | 0.819 | 88.0% |
| **v2.3** | 같은 임베딩 + QA 구성 개선 | **77.4%** | **96.8%** | **100.0%** | **0.874** | **94.5%** |

![버전별 지표 변화](results/eval_progress.png)

- **v2.1 → v2.2 (임베딩 교체):** Hit@1 +16.2%p, MRR +0.127. 대신 Recall@5는 100% → 93.5%로 떨어졌습니다.
- **v2.2 → v2.3 (QA 구성 개선):** 같은 임베딩에서 질문을 보완해 Hit@1 +6.4%p, Recall@5 100% 회복.
- 두 변경이 함께 반영된 결과이므로, 최종 개선폭을 한 가지 요인의 효과로 보지 않습니다.

## 평가 방법

```
wiki/*.md ──► 청킹 ──► 임베딩 ──► ChromaDB ──► similarity_search ──► 정답 문서 순위로 채점
```

- **청킹:** `RecursiveCharacterTextSplitter` (chunk 800 / overlap 100, 마크다운 헤더 우선 분할)
- **정답 기준:** 질문마다 정답 위키 페이지 1개를 지정 (`expected`). 검색된 청크의 출처 파일명으로 채점
- **QA 셋:** 31개 = 기본 20개 + 프로젝트 문서 3개 + CQ(Competency Question) 기반 8개
  - CQ 원칙: "이 지식베이스가 반드시 답할 수 있어야 하는 질문"을 기준으로 설계

| 지표 | 의미 |
|------|------|
| Hit@1 | 1순위 검색 결과가 정답 문서인 비율 (precision 지향) |
| Recall@3 / @5 | 상위 3·5개 결과 안에 정답 문서가 포함된 비율 |
| MRR | 정답 문서 순위 역수(1/순위)의 평균 |
| Fβ(β=2) | Hit@1을 precision, Recall@5를 recall로 두고 recall에 2배 가중한 종합 지표 |

## 저장소 구성

| 경로 | 내용 |
|------|------|
| `run_eval.py` | 벤치마크 실행: DB 재빌드 → 23/31개 QA 평가 → 버전 히스토리 누적 → 차트·리포트 자동 갱신 |
| `notebooks/rag_eval.ipynb` | 초기 PoC (20개 QA)와 구조화 vs 비구조화 문서 비교 실험 |
| `results/` | 버전별 평가 CSV, `version_history.json`, `eval_report.md`, 차트 |
| `.claude/commands/` | Claude Code 커맨드: `/PoC`(평가 실행), `/ingest`·`/query`·`/lint`(위키 운영) |
| `docs/wiki-schema.md` | 평가 코퍼스를 만드는 LLM Wiki의 구조와 운영 규칙 |

### 참고: 구조화 vs 비구조화 실험 (`notebooks/`)

개념·엔티티별로 나눈 문서와 하나로 합친 문서의 검색 품질을 비교한 초기 실험입니다(20개 QA).
비구조화 쪽은 출처 파일이 하나뿐이라 **키워드 기반 soft match**로 채점했기 때문에 두 결과를 같은 기준으로 직접 비교할 수는 없습니다.
이 한계 때문에 이후 벤치마크(`run_eval.py`)는 파일 단위 정답 기준으로 통일했습니다.

## 실행

```bash
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY, WIKI_DIR 입력
python -X utf8 run_eval.py
```

`WIKI_DIR`에는 마크다운 문서 폴더를 지정합니다. 파일명(확장자 제외)이 QA 셋의 `expected` 값과 일치해야 채점됩니다.

## 비공개 처리

- QA 항목 1개는 개인 문서를 가리켜 질문과 문서명을 일반화했습니다 (`synthesis-RAG-practice-notes`). 점수는 원래 결과 그대로입니다.
- 코퍼스 파일 목록(`corpus_manifest_*.json`)과 벡터 DB는 문서 원문이 포함돼 제외했습니다.

## Stack

Python · LangChain · ChromaDB · OpenAI Embeddings · HuggingFace(MiniLM) · pandas · matplotlib · Claude Code
