"""
RAG eval script — v2.3
벤치마크 버전: v2.3 | 2026-06-04
변경사항: 실행 시마다 version_history.json 자동 누적 → 차트·리포트 자동 재생성
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import json
import shutil
import datetime
from pathlib import Path

from dotenv import load_dotenv

# OPENAI_API_KEY, WIKI_DIR는 .env 또는 환경변수로 설정 (.env.example 참고)
load_dotenv()

import pandas as pd
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

# ── 벤치마크 버전 핀 ───────────────────────────────────────
BENCHMARK_VERSION = "v2.3"
BENCHMARK_DATE    = "2026-06-04"
BENCHMARK_LABEL   = "OpenAI+QA개선"   # ← 새 버전 만들 때 여기만 바꾸면 됨
BENCHMARK_EMBED   = "text-embedding-3-small (OpenAI)"

# ── 경로 설정 ──────────────────────────────────────────────
WIKI_DIR             = Path(os.environ.get("WIKI_DIR", "./wiki"))
DB_DIR_V2            = Path("./chroma_db_v2")
DB_DIR_V3            = Path("./chroma_db_v3")
RESULTS              = Path("./results")
VERSION_HISTORY_PATH = RESULTS / "version_history.json"

EXCLUDE_FILES = {"index.md", "log.md", "todo.md", "CLAUDE.md"}
EXCLUDE_DIRS  = {"graphify-out"}

# ── OpenAI 임베딩 ──────────────────────────────────────────
# 모델: text-embedding-3-small (1536차원)
# (로컬 전환 시: from langchain_huggingface import HuggingFaceEmbeddings
#               embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2"))
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
splitter   = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=100,
    separators=["\n## ", "\n### ", "\n\n", "\n", " "]
)

# ── QA Pairs v1 (원본 20개) ────────────────────────────────
QA_PAIRS_V1 = [
    {"question": "RAG 오픈북 시험 비유 Long Context 8-12배 저렴 청킹 Chroma Pinecone pgvector 벡터DB Reranker",  "expected": "concept-RAG"},
    {"question": "Ontology 기반 지식 표현 방식이란?",                   "expected": "concept-ontology"},
    {"question": "MLOps의 정의와 주요 구성요소는?",                     "expected": "concept-MLOps"},
    {"question": "MCP Model Context Protocol 개념과 활용",              "expected": "concept-MCP"},
    {"question": "클라우드 아키텍처의 주요 구성요소와 설계 원칙",        "expected": "concept-cloud-architecture"},
    {"question": "컨텍스트 엔지니어링이란 무엇이고 왜 필요한가?",        "expected": "concept-context-engineering"},
    {"question": "LLM 환각 발생 원인과 완화 방법",                      "expected": "concept-hallucination"},
    {"question": "Claude Code 서브에이전트 독립 컨텍스트 병렬 실행 JARVIS 라우터 패턴 헤르메스 학습 루프",  "expected": "concept-subagents"},
    {"question": "SLO Service Level Objective 정의와 측정 방법",        "expected": "concept-SLO"},
    {"question": "Zettelkasten 방법론과 지식 연결 방식",                "expected": "concept-Zettelkasten"},
    {"question": "NAVER Cloud HyperCLOVA X AX 서비스",                 "expected": "entity-NAVER-Cloud"},
    {"question": "VGG-16 전이학습 킥보드 불법 주정차 분류 정확도",       "expected": "entity-VGG16-kickboard"},
    {"question": "GPUaaS PoC 프로젝트 구조와 목적",                     "expected": "entity-GPUaaS-PoC"},
    {"question": "NHN Cloud 서비스와 특징",                             "expected": "entity-NHN-Cloud"},
    {"question": "Anthropic Claude API 모델 종류와 특징",               "expected": "entity-Anthropic"},
    {"question": "AWS 클라우드 주요 서비스와 활용 사례",                 "expected": "entity-AWS"},
    {"question": "RAG와 Mem0의 차이점과 각 장단점",                     "expected": "comparison-RAG-vs-Mem0"},
    {"question": "샘 호트만이 설명한 RAG 파이프라인 청킹 하이브리드 서치",   "expected": "summary-RAG-샘호트만-2026"},
    {"question": "LLM Wiki 지식 관리 시스템 설계 원칙",                 "expected": "concept-LLM-Wiki"},
    {"question": "하네스 엔지니어링 개념과 AI 시스템 적용",             "expected": "concept-harness-engineering"},
]

# ── QA Pairs v2 추가분 (3개) ───────────────────────────────
QA_PAIRS_V2_NEW = [
    {"question": "LLM 대화형 지갑 코파일럿 가드레일 패턴 블록체인 트랜잭션", "expected": "entity-polar-star"},
    {"question": "중고차 수출 가격 예측 Flask ML GCP 배포 서비스",            "expected": "entity-car-price-predictor"},
    {"question": "블록체인 블로그 Claude API 번역 콘텐츠 소유권 증명",        "expected": "entity-block-blog"},
]

# ── QA Pairs v3 추가분 (8개) — CQ 기반 설계 ──────────────
# CQ 원칙: "이 시스템이 반드시 답할 수 있어야 하는 질문"을 기준으로 설계
QA_PAIRS_V3_NEW = [
    {"question": "코드 기반 에이전트 프레임워크 vs Computer Use 도구 역할 기반 그래프 기반 이벤트 기반 아키텍처 패턴",  "expected": "concept-agent-frameworks"},
    {"question": "로컬 LLM 서빙 SGLang vLLM Ollama 성능 비교와 선택 기준",         "expected": "concept-LLM-serving"},
    {"question": "CrewAI 역할 기반 멀티 에이전트 프레임워크 특징과 활용",           "expected": "entity-CrewAI"},
    {"question": "SGLang RadixAttention KV Cache 재사용으로 처리량 향상",           "expected": "entity-SGLang"},
    {"question": "vLLM Continuous Batching 범용 LLM 서빙 특징",                    "expected": "entity-vLLM"},
    {"question": "Mem0 LLM 장기 메모리 아키텍처 토큰 절약 지연시간 감소",          "expected": "entity-Mem0"},
    {"question": "Odysseus 자체호스팅 AI 워크스페이스 로컬 LLM 에이전트 통합",     "expected": "entity-Odysseus"},
    {"question": "RAG 실무 적용 전략과 PoC 수치 정리",                              "expected": "synthesis-RAG-practice-notes"},
]

QA_PAIRS_23 = QA_PAIRS_V1 + QA_PAIRS_V2_NEW
QA_PAIRS_31 = QA_PAIRS_23 + QA_PAIRS_V3_NEW


# ── 유틸 함수 ──────────────────────────────────────────────
def load_wiki_docs(wiki_dir: Path):
    docs = []
    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name in EXCLUDE_FILES:
            continue
        if any(d in md_file.parts for d in EXCLUDE_DIRS):
            continue
        try:
            loader = TextLoader(str(md_file), encoding="utf-8")
            loaded = loader.load()
            for doc in loaded:
                doc.metadata["source_file"] = md_file.stem
            docs.extend(loaded)
        except Exception as e:
            print(f"[SKIP] {md_file.name}: {e}")
    return docs


def save_corpus_manifest(wiki_dir: Path, output_path: Path):
    """인덱싱된 파일 목록과 수정 시간을 저장 — benchmark pinning."""
    manifest = {"benchmark_version": BENCHMARK_VERSION, "built_at": BENCHMARK_DATE, "files": []}
    for md_file in sorted(wiki_dir.rglob("*.md")):
        if md_file.name in EXCLUDE_FILES:
            continue
        if any(d in md_file.parts for d in EXCLUDE_DIRS):
            continue
        manifest["files"].append({
            "name": md_file.stem,
            "path": str(md_file.relative_to(wiki_dir)),
            "mtime": datetime.datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
        })
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  코퍼스 매니페스트 저장: {output_path} ({len(manifest['files'])}개 파일)")


def recall_at_k(vs, question, expected, k):
    results = vs.similarity_search(question, k=k)
    retrieved = [r.metadata.get("source_file", "") for r in results]
    return 1 if expected in retrieved else 0


def hit_at_1(vs, question, expected):
    """최상위 결과가 정답인지 — precision 지향 지표."""
    results = vs.similarity_search(question, k=1)
    return 1 if results and results[0].metadata.get("source_file", "") == expected else 0


def reciprocal_rank(vs, question, expected, k=10):
    results = vs.similarity_search(question, k=k)
    for rank, r in enumerate(results, 1):
        if r.metadata.get("source_file", "") == expected:
            return 1.0 / rank
    return 0.0


def f_beta_score(precision: float, recall: float, beta: float = 2.0) -> float:
    """Fβ 점수. β=2이면 recall을 precision보다 2배 가중."""
    if precision + recall == 0:
        return 0.0
    return (1 + beta**2) * precision * recall / (beta**2 * precision + recall)


# ── 버전 히스토리 관리 ─────────────────────────────────────

_HISTORY_SEED = [
    {"version": "v2.1", "date": "2026-06-03", "label": "로컬 MiniLM",
     "embedding": "paraphrase-multilingual-MiniLM-L12-v2 (로컬)",
     "qa_count": 31, "hit1": 54.8, "recall3": 80.6, "recall5": 100.0, "mrr": 69.2, "fbeta": 85.9},
    {"version": "v2.2", "date": "2026-06-04", "label": "OpenAI 초기",
     "embedding": "text-embedding-3-small (OpenAI)",
     "qa_count": 31, "hit1": 71.0, "recall3": 90.3, "recall5": 93.5, "mrr": 81.9, "fbeta": 88.0},
]

def load_version_history():
    if VERSION_HISTORY_PATH.exists():
        return json.loads(VERSION_HISTORY_PATH.read_text(encoding="utf-8"))
    return list(_HISTORY_SEED)

def save_version_history(history):
    VERSION_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def append_or_update_version(history, df):
    """현재 버전 결과를 히스토리에 추가. 같은 버전이면 덮어씀."""
    h1  = round(df["Hit@1"].mean() * 100, 1)
    r3  = round(df["Recall@3"].mean() * 100, 1)
    r5  = round(df["Recall@5"].mean() * 100, 1)
    mrr = round(df["RR"].mean() * 100, 1)
    fb  = round(f_beta_score(df["Hit@1"].mean(), df["Recall@5"].mean(), beta=2) * 100, 1)
    entry = {
        "version": BENCHMARK_VERSION, "date": BENCHMARK_DATE,
        "label": BENCHMARK_LABEL, "embedding": BENCHMARK_EMBED,
        "qa_count": len(df),
        "hit1": h1, "recall3": r3, "recall5": r5, "mrr": mrr, "fbeta": fb,
    }
    for i, h in enumerate(history):
        if h["version"] == BENCHMARK_VERSION:
            history[i] = entry
            return history
    history.append(entry)
    return history

def generate_progress_chart(history):
    if not MATPLOTLIB_OK:
        print("  [SKIP] matplotlib 없음")
        return
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    labels_x = [f"{h['label']}\n({h['version']})" for h in history]
    x      = np.arange(len(labels_x))
    width  = 0.15
    data   = ([h["hit1"]    for h in history],
               [h["recall3"] for h in history],
               [h["recall5"] for h in history],
               [h["mrr"]     for h in history],
               [h["fbeta"]   for h in history])
    colors = ["#89b4fa", "#a6e3a1", "#f38ba8", "#fab387", "#cba6f7"]
    names  = ["Hit@1", "Recall@3", "Recall@5", "MRR", "Fβ(β=2)"]

    fig, ax = plt.subplots(figsize=(max(9, len(history) * 3.5), 6))
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#1e1e2e")

    for i, (d, c, n) in enumerate(zip(data, colors, names)):
        bars = ax.bar(x + (i - 2) * width, d, width, label=n, color=c, alpha=0.9, zorder=3)
        for rect, val in zip(bars, d):
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 0.8,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=7.5,
                    color="white", fontweight="bold")

    ax.set_ylim(0, 115)
    ax.set_xticks(x)
    ax.set_xticklabels(labels_x, color="white", fontsize=10)
    ax.set_ylabel("Score (%)", color="white", fontsize=11)
    ax.set_title("RAG Eval 지표 버전별 변화", color="white", fontsize=13, fontweight="bold", pad=14)
    ax.tick_params(colors="white")
    for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
    for sp in ["bottom", "left"]: ax.spines[sp].set_color("#45475a")
    ax.yaxis.grid(True, color="#45475a", linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", facecolor="#313244", edgecolor="#45475a",
              labelcolor="white", fontsize=9)
    ax.axhline(100, color="#a6e3a1", linestyle=":", linewidth=1.2, alpha=0.6)

    plt.tight_layout()
    chart_path = RESULTS / "eval_progress.png"
    plt.savefig(str(chart_path), dpi=150, bbox_inches="tight", facecolor="#1e1e2e")
    plt.close()
    print(f"  차트 저장: {chart_path}")

def update_eval_report(history):
    latest = history[-1]
    rows = ""
    for h in history:
        b = "**" if h["version"] == latest["version"] else ""
        rows += (f"| {b}{h['version']} ({h['label']}){b} "
                 f"| {b}{h['hit1']}%{b} | {b}{h['recall3']}%{b} "
                 f"| {b}{h['recall5']}%{b} | {b}{h['mrr']/100:.3f}{b} "
                 f"| {b}{h['fbeta']}%{b} |\n")

    content = f"""# RAG Eval 진행 리포트

**프로젝트**: LLM Wiki — RAG Retrieval Eval
**마지막 업데이트**: {latest['date']}
**임베딩 모델 (최신)**: {latest['embedding']}
**QA 셋**: {latest['qa_count']}개

---

## 버전별 지표 변화

![RAG Eval 지표 버전별 변화](eval_progress.png)

| 버전 | Hit@1 | Recall@3 | Recall@5 | MRR | Fβ(β=2) |
|------|-------|----------|----------|-----|---------|
{rows}
---

*`run_eval.py` 실행 시 자동 업데이트됨*
"""
    report_path = RESULTS / "eval_report.md"
    report_path.write_text(content, encoding="utf-8")
    print(f"  리포트 저장: {report_path}")


def run_eval(vs, qa_pairs, label):
    rows = []
    for i, pair in enumerate(qa_pairs, 1):
        q, exp = pair["question"], pair["expected"]
        h1 = hit_at_1(vs, q, exp)
        r3 = recall_at_k(vs, q, exp, k=3)
        r5 = recall_at_k(vs, q, exp, k=5)
        rr = reciprocal_rank(vs, q, exp, k=10)
        rows.append({
            "#": i, "expected": exp,
            "Hit@1": h1, "Recall@3": r3, "Recall@5": r5, "RR": round(rr, 3)
        })
        status = "✓" if h1 else ("△" if r3 else ("▽" if r5 else "✗"))
        print(f"  [{status}] {exp:<40} H@1={h1} R@3={r3} R@5={r5} RR={rr:.3f}")

    df = pd.DataFrame(rows)
    h1m  = df["Hit@1"].mean()
    r3m  = df["Recall@3"].mean()
    r5m  = df["Recall@5"].mean()
    mrr  = df["RR"].mean()
    # Fβ(β=2): dataset precision = Hit@1 rate, dataset recall = Recall@5 rate
    fb   = f_beta_score(h1m, r5m, beta=2)

    print(f"\n{'='*55}")
    print(f"  {label}  [{BENCHMARK_VERSION} · {len(qa_pairs)}개 QA]")
    print(f"  Hit@1    : {h1m:.3f}  ({h1m*100:.1f}%)   ← 상위1 정답률 (precision)")
    print(f"  Recall@3 : {r3m:.3f}  ({r3m*100:.1f}%)")
    print(f"  Recall@5 : {r5m:.3f}  ({r5m*100:.1f}%)   ← 상위5 포함률 (recall)")
    print(f"  MRR      : {mrr:.3f}")
    print(f"  Fβ(β=2)  : {fb:.3f}             ← recall 2배 가중 종합")
    print(f"{'='*55}")

    failed = df[df["Recall@5"] == 0]
    if len(failed):
        print(f"  Recall@5 실패 ({len(failed)}건): {', '.join(failed['expected'].tolist())}")

    return df


# ══════════════════════════════════════════════════════════
# STEP 1: DB 재빌드 (v3 — 현재 wiki 전체)
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*55}")
print(f"STEP 1 — DB 재빌드 v3  [{BENCHMARK_VERSION} · {BENCHMARK_DATE}]")
print(f"{'━'*55}")

raw_docs = load_wiki_docs(WIKI_DIR)
chunks   = splitter.split_documents(raw_docs)
print(f"  로드된 파일: {len(raw_docs)}개 → 청크: {len(chunks)}개")

if DB_DIR_V3.exists():
    shutil.rmtree(DB_DIR_V3)

vs_v3 = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=str(DB_DIR_V3)
)
print(f"  chroma_db_v3 생성 완료")

RESULTS.mkdir(exist_ok=True)
save_corpus_manifest(WIKI_DIR, RESULTS / f"corpus_manifest_{BENCHMARK_VERSION}.json")

# ══════════════════════════════════════════════════════════
# STEP 2: v2 DB baseline — 23개 QA (이전 결과 재현)
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*55}")
print("STEP 2 — v2 DB baseline / 23개 QA")
print(f"{'━'*55}")

if DB_DIR_V2.exists():
    vs_v2 = Chroma(persist_directory=str(DB_DIR_V2), embedding_function=embeddings)
    df_baseline = run_eval(vs_v2, QA_PAIRS_23, "v2 DB · 23개 QA (baseline)")
    df_baseline.to_csv(RESULTS / "eval_baseline_v2db_23qa.csv", index=False, encoding="utf-8-sig")
else:
    print("  chroma_db_v2 없음 — baseline 스킵")
    df_baseline = None

# ══════════════════════════════════════════════════════════
# STEP 3: v3 DB — 23개 QA (DB 갱신 효과)
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*55}")
print("STEP 3 — v3 DB / 23개 QA (DB 갱신 효과)")
print(f"{'━'*55}")

df_v3_23 = run_eval(vs_v3, QA_PAIRS_23, "v3 DB · 23개 QA")
df_v3_23.to_csv(RESULTS / "eval_v3db_23qa.csv", index=False, encoding="utf-8-sig")

# ══════════════════════════════════════════════════════════
# STEP 4: v3 DB — 31개 QA (신규 QA 포함 전체)
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*55}")
print("STEP 4 — v3 DB / 31개 QA (v3 신규 8개 포함)")
print(f"{'━'*55}")

df_v3_31 = run_eval(vs_v3, QA_PAIRS_31, "v3 DB · 31개 QA")
df_v3_31.to_csv(RESULTS / "eval_v3db_31qa.csv", index=False, encoding="utf-8-sig")

# ══════════════════════════════════════════════════════════
# 최종 비교 요약
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*55}")
print("최종 비교")
print(f"{'━'*55}")
print(f"  {'':32} {'H@1':>5} {'R@3':>5} {'R@5':>5} {'MRR':>6} {'Fβ2':>6}")

candidates = [("v2 DB · 23개 (baseline)", df_baseline), ("v3 DB · 23개 (DB 갱신)", df_v3_23), ("v3 DB · 31개 (전체)", df_v3_31)]
for label, df in candidates:
    if df is None:
        print(f"  {label:<32} {'—':>5} {'—':>5} {'—':>5} {'—':>6} {'—':>6}")
        continue
    h1  = df["Hit@1"].mean()
    r3  = df["Recall@3"].mean()
    r5  = df["Recall@5"].mean()
    mrr = df["RR"].mean()
    fb  = f_beta_score(h1, r5, beta=2)
    print(f"  {label:<32} {h1*100:>4.1f}% {r3*100:>4.1f}% {r5*100:>4.1f}% {mrr:>6.3f} {fb:>6.3f}")

print(f"\n모든 결과 results/ 폴더에 저장됨  [{BENCHMARK_VERSION}]")

# ══════════════════════════════════════════════════════════
# STEP 5: 버전 히스토리 누적 → 차트 + 리포트 자동 재생성
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*55}")
print("STEP 5 — 버전 히스토리 · 차트 · 리포트 업데이트")
print(f"{'━'*55}")

history = load_version_history()
history = append_or_update_version(history, df_v3_31)
save_version_history(history)
print(f"  version_history.json 업데이트 ({len(history)}개 버전 누적)")
generate_progress_chart(history)
update_eval_report(history)
