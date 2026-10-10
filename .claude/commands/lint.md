# /lint — LLM Wiki 건강검진 스킬

`wiki/` 전체를 스캔해 깨진 링크, 고아 페이지, 누락된 연결, stale 내용 등을 탐지하고 수정한다.
인자 없이 `/lint` 만 입력하면 전체 검사를 실행한다.

---

## Step 1. 컨텍스트 로드

다음 파일을 읽는다. 스킵하지 않는다.

1. `CLAUDE.md` — 볼트 운영 규칙
2. `wiki/index.md` — 등록된 페이지 목록
3. `wiki/log.md` — 오퍼레이션 히스토리

---

## Step 2. 전체 파일 스캔

`wiki/` 하위 모든 `.md` 파일 경로를 수집한다 (`index.md`, `log.md`, `CLAUDE.md` 제외).
각 파일의 YAML frontmatter와 `[[wikilink]]` 패턴을 파싱한다.

---

## Step 3. 검사 항목 실행

아래 7개 검사를 순서대로 실행한다.

### CHECK-1. 깨진 wikilink (Broken Links)
모든 페이지에서 `[[파일명]]` 패턴을 추출한다.
해당 파일명과 일치하는 `.md` 파일이 `wiki/` 하위에 존재하지 않으면 → **깨진 링크**.

### CHECK-2. 고아 페이지 (Orphan Pages)
`wiki/` 하위 모든 페이지 중 다른 어떤 페이지에서도 `[[링크]]`로 참조되지 않고,
`index.md`에도 없으면 → **고아 페이지**.

### CHECK-3. index.md 동기화 불일치
- `wiki/` 하위에 파일이 존재하지만 `index.md`에 등록이 안 된 페이지 → **index 누락**
- `index.md`에 등록됐지만 파일이 실제로 없는 항목 → **유령 항목**

### CHECK-4. YAML frontmatter 불완전
모든 wiki 페이지에서 다음 필드가 있는지 확인한다:
`title`, `type`, `tags`, `created`, `updated`, `sources`, `source_count`
누락된 필드가 있으면 → **frontmatter 불완전**.

### CHECK-5. 누락된 개념·엔티티 페이지 (Mentioned but Missing)
wiki 페이지 전체에서 `[[파일명]]` 형태로 언급됐지만 실제 파일이 없는 항목을 수집한다.
`log.md`의 "링크 예정" 또는 "미생성" 메모와 대조한다.
여러 페이지에서 반복 언급된 항목 → **생성 우선순위 높음**.

### CHECK-6. 상호 링크 누락 (Missing Cross-reference)
두 페이지 A, B가 같은 소스를 `sources:` 에 공유하거나 같은 개념을 본문에서 다루는데
서로를 `[[링크]]`로 참조하지 않으면 → **크로스링크 누락**.

### CHECK-7. source_count 불일치
각 페이지의 `source_count` 값과 실제 `sources:` 리스트 길이를 비교한다.
값이 다르면 → **source_count 오류**.

---

## Step 4. 검사 결과 보고

아래 형식으로 보고한다. 문제가 없는 항목은 "✅ 이상 없음"으로 표시한다.

```
## /lint 결과 — YYYY-MM-DD

### ❌ CHECK-1. 깨진 wikilink
- [[존재하지 않는 페이지]] — 참조 위치: concept-xxx.md, entity-yyy.md

### ⚠️ CHECK-2. 고아 페이지
- wiki/concepts/concept-zzz.md — 어떤 페이지에서도 참조 없음

### ⚠️ CHECK-3. index.md 동기화 불일치
- [index 누락] wiki/entities/entity-aaa.md — index.md에 없음
- [유령 항목] [[concept-bbb]] — index.md에는 있으나 파일 없음

### ⚠️ CHECK-4. frontmatter 불완전
- wiki/summaries/summary-xxx.md — 누락 필드: updated, source_count

### 📋 CHECK-5. 언급됐지만 페이지 없는 항목
우선순위 높음 (3회 이상 언급):
- MLOps — concept-MLOps.md 없음. 언급: concept-cloud-architecture.md(2회), concept-LLM-Wiki.md(1회)

우선순위 낮음 (1-2회 언급):
- FastMCP — entity-FastMCP.md 없음.

### ⚠️ CHECK-6. 크로스링크 누락
- concept-cloud-architecture ↔ summary-클라우드아키텍처-Google-2026: sources 공유하지만 상호 링크 없음

### ⚠️ CHECK-7. source_count 불일치
- wiki/concepts/concept-xxx.md: source_count=0 이지만 sources에 1개 항목 있음

---
요약: 자동 수정 가능 N건 / 검토 필요 N건 / 신규 페이지 생성 권장 N건
```

---

## Step 5. 자동 수정 실행

사용자 승인 없이 즉시 수정할 수 있는 항목:

| 항목 | 자동 수정 내용 |
|------|---------------|
| CHECK-3 index 누락 | `index.md`에 해당 페이지 항목 추가 |
| CHECK-4 frontmatter 불완전 | 누락 필드를 기본값으로 채움 (`updated`: 오늘 날짜, `source_count`: sources 길이 기준) |
| CHECK-7 source_count 불일치 | `source_count` 값을 sources 리스트 길이로 정정 |

자동 수정 후 수정된 파일과 변경 내용을 보고한다.

---

## Step 6. 사용자 판단이 필요한 항목 처리

자동 수정 후 남은 항목을 제시하고 사용자에게 어떻게 할지 묻는다.

**깨진 wikilink**: 링크 대상 파일 생성 vs 링크 제거 중 선택
**고아 페이지**: 삭제 vs 연결 페이지에서 링크 추가 중 선택
**언급됐지만 없는 페이지 (우선순위 높음)**: 지금 생성할지 나중으로 미룰지 선택
**크로스링크 누락**: 지금 양쪽 페이지에 링크 추가할지 선택

사용자가 "다 고쳐줘" 또는 "모두 수정" 이라고 하면 → 모든 항목을 순서대로 처리한다.
특정 CHECK 번호를 지정하면 → 해당 항목만 처리한다.

---

## Step 7. log.md 업데이트

lint 실행 결과를 `wiki/log.md` 맨 앞에 기록한다.

```
## [YYYY-MM-DD] lint | wiki 건강검진

발견: [각 CHECK별 건수 요약]
자동 수정: [수정된 항목 목록]
미해결: [사용자 판단 대기 항목]
```

---

## 절대 규칙

- `raw/` 파일은 절대 수정하지 않는다
- `log.md`는 append-only — 기존 항목 절대 수정 금지
- 자동 수정 범위를 벗어난 변경(페이지 삭제, 새 페이지 생성)은 반드시 사용자에게 먼저 보고하고 승인 후 실행한다
- 모순이 발견되면 임의로 하나를 지우지 않고 `⚠️ 모순` 태그와 함께 양쪽 소스를 모두 남긴다
