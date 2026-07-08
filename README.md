# AlphaBet

멀티 에이전트 기반 주식 분석 프레임워크입니다. 재무제표, 차트, 거시경제, 뉴스/감성 4개 전문 에이전트가 각각 분석을 수행하고, Supervisor가 결과를 통합해 최종 판단을 제공합니다.

---

## 목차

- [개요](#개요)
- [아키텍처](#아키텍처)
- [에이전트 구성](#에이전트-구성)
- [프로젝트 구조](#프로젝트-구조)
- [폴더·파일 상세 설명](#폴더파일-상세-설명)
- [데이터 흐름](#데이터-흐름)
- [설치 및 실행](#설치-및-실행)
- [환경 변수](#환경-변수)
- [설계 원칙](#설계-원칙)
- [향후 작업](#향후-작업)

---

## 개요

AlphaBet은 하나의 Python 패키지(`alphabet`) 안에 모든 에이전트를 구현하는 **모노레포 구조**입니다.

| 에이전트 | 핵심 질문 | 분석 시간 축 |
|---------|----------|-------------|
| Financial | 이 회사가 돈을 잘 버는가? | 분기~연 |
| Chart | 지금 차트상 흐름이 어떤가? | 일~주 |
| Macro | 지금 시장 환경이 주식에 유리한가? | 월~분기 |
| News | 이 종목에 호재·악재가 있는가? | 일 |
| Supervisor | 위 4개 결과를 어떻게 통합할까? | — |

각 에이전트는 동일한 출력 스키마(`AgentReport`)를 반환하므로, Supervisor가 신호를 비교·가중·통합할 수 있습니다.
HuggingFace 모델은 `alphabet/ml/`에 공통으로 두고, 필요한 에이전트만 선택적으로 사용합니다.

---

## 아키텍처

```
[사용자 입력: 종목, 시장, 질문]
        │
        ▼
   main.py (CLI)
        │
        ▼
 orchestrator/pipeline.py
   ┌────┼────┬────────┬────────┐
   ▼    ▼    ▼        ▼        │  (asyncio 병렬 실행)
Financial Chart Macro   News   │
   │    │    │        │        │
   └────┴────┴────────┘        │
        │                       │
        ▼                       │
  AgentReport × 4               │
        │                       │
        ▼                       │
 agents/supervisor.py ◄─────────┘
   (가중 통합 + 상충 감지)
        │
        ▼
  AnalysisResult (최종 리포트)
```

### 3계층 분리

| 계층 | 역할 | 위치 |
|------|------|------|
| **Services** | 외부 API·DB에서 원시 데이터 수집 | `alphabet/services/` |
| **Agents** | 데이터 해석, 신호 도출, (선택) HF 모델 추론 | `alphabet/agents/` |
| **Orchestrator** | 에이전트 병렬 실행, Supervisor 호출 | `alphabet/orchestrator/` |

에이전트는 데이터를 직접 가져오지 않고 `services/`를 통해 받습니다. 이 덕분에 API 교체·모킹·단위 테스트가 쉬워집니다.

---

## 에이전트 구성

### FinancialAgent (`agents/financial.py`)

- **질문**: "이 회사가 돈을 잘 버는가?"
- **데이터**: `FinancialDataService` → 매출성장률, 영업이익률, ROE, 부채비율, PER, PBR
- **판단 로직**: 지표별 점수 합산 → `bullish` / `neutral` / `bearish`
- **HF 사용**: 현재 미연동 (추후 공시 요약 등에 `hf_summarization_model` 활용 가능)

### ChartAgent (`agents/chart.py`)

- **질문**: "지금 차트상 흐름이 어떤가?"
- **데이터**: `MarketDataService` → OHLCV, 이동평균, 추세
- **판단 로직**: 단기 추세(up/down) + 종가 vs 20일 이동평균
- **HF 사용**: 현재 미연동 (추후 시계열 모델 연동 가능)

### MacroAgent (`agents/macro.py`)

- **질문**: "지금 시장 환경이 주식에 유리한가?"
- **데이터**: `MacroDataService` → 금리, CPI, 환율, 지수 추세, VIX
- **판단 로직**: 인플레이션·변동성·지수 추세 종합 점수
- **HF 사용**: 없음

### NewsAgent (`agents/news.py`)

- **질문**: "이 종목에 호재·악재가 있는가?"
- **데이터**: `NewsDataService` → 최근 뉴스·공시 헤드라인
- **판단 로직**: HuggingFace FinBERT 감성 분석 (`--hf` 플래그) 또는 헤드라인만 수집
- **HF 사용**: `SentimentAnalyzer` → `ProsusAI/finbert` (기본값)

### SupervisorAgent (`agents/supervisor.py`)

- **역할**: 4개 `AgentReport`를 가중 통합하고 상충 신호를 감지
- **가중치**: `horizon`(short/medium/long)에 따라 에이전트별 비중 자동 조정
- **상충 감지 예시**:
  - 재무 bullish + 차트 bearish → "펀더멘털은 양호하나 단기 차트는 약세"
  - 강세·약세 에이전트가 동시에 존재할 때 경고 메시지 생성

---

## 프로젝트 구조

```
AlphaBet/
├── README.md
├── pyproject.toml          # 패키지 메타데이터, CLI 엔트리포인트
├── requirements.txt        # pip 의존성
├── .env.example            # 환경 변수 템플릿
│
└── alphabet/               # 메인 Python 패키지
    ├── __init__.py         # 패키지 버전
    ├── main.py             # CLI 진입점
    ├── config.py           # 환경 설정 (Pydantic Settings)
    │
    ├── schemas/            # 데이터 타입·계약 정의
    │   ├── __init__.py
    │   ├── common.py       # Signal, AgentReport, AnalysisResult 등
    │   └── weights.py      # 에이전트별 가중치
    │
    ├── services/           # 외부 데이터 수집 레이어
    │   ├── __init__.py
    │   ├── financial_data.py
    │   ├── market_data.py
    │   ├── macro_data.py
    │   └── news_data.py
    │
    ├── ml/                 # HuggingFace 공통 레이어
    │   ├── __init__.py     # lazy import (HF 없이도 실행 가능)
    │   ├── hf_client.py    # 파이프라인 로더, 디바이스 자동 선택
    │   └── sentiment.py    # FinBERT 감성 분석
    │
    ├── agents/             # 분석 에이전트
    │   ├── __init__.py
    │   ├── base.py         # BaseAgent 추상 클래스
    │   ├── financial.py
    │   ├── chart.py
    │   ├── macro.py
    │   ├── news.py
    │   └── supervisor.py
    │
    └── orchestrator/       # 실행 조율
        ├── __init__.py
        └── pipeline.py     # 병렬 실행 + Supervisor 호출
```

---

## 폴더·파일 상세 설명

### 루트 파일

#### `pyproject.toml`

패키지 이름, 버전, Python 요구 버전(≥3.11), 의존성을 정의합니다. `alphabet` CLI 명령어가 `alphabet.main:main`에 연결됩니다.

#### `requirements.txt`

`pip install -r requirements.txt`로 설치할 의존성 목록입니다. 데이터 API 연동용 패키지(yfinance, pykrx 등)는 주석 처리되어 있으며, 필요 시 활성화합니다.

#### `.env.example`

환경 변수 템플릿입니다. `.env`로 복사해 사용합니다.

---

### `alphabet/` — 메인 패키지

#### `__init__.py`

패키지 버전(`0.1.0`)을 노출합니다.

#### `main.py`

CLI 진입점입니다. argparse로 종목 코드, 질문, 시장(KR/US), HF 사용 여부를 받아 `run_analysis()`를 호출하고 JSON 결과를 출력합니다.

```bash
python -m alphabet.main 005930
python -m alphabet.main 005930 -q "지금 매수 타이밍인가?"
python -m alphabet.main AAPL -m US --hf
```

#### `config.py`

`pydantic-settings` 기반 설정 클래스입니다. `.env` 파일과 환경 변수를 자동으로 읽습니다.

| 설정 | 설명 | 기본값 |
|------|------|--------|
| `hf_token` | HuggingFace API 토큰 | `None` |
| `hf_device` | 추론 디바이스 | `auto` (CUDA → MPS → CPU) |
| `hf_sentiment_model` | 감성 분석 모델 | `ProsusAI/finbert` |
| `hf_summarization_model` | 요약 모델 (추후 사용) | `facebook/bart-large-cnn` |
| `dart_api_key` | DART Open API 키 | `None` |
| `news_api_key` | 뉴스 API 키 | `None` |
| `agent_timeout_sec` | 에이전트 타임아웃(초) | `120` |

---

### `alphabet/schemas/` — 데이터 계약

에이전트 간 통신 형식을 Pydantic 모델로 고정합니다. 모든 에이전트가 같은 스키마를 쓰므로 Supervisor 통합이 단순해집니다.

#### `common.py`

| 타입 | 설명 |
|------|------|
| `Signal` | `bullish` / `neutral` / `bearish` |
| `Horizon` | `short` / `medium` / `long` — 분석 시간 축 |
| `AgentName` | 에이전트 식별자 |
| `Evidence` | 근거 항목 (source, metric, value, detail) |
| `AnalysisRequest` | 분석 요청 (ticker, market, question, horizon) |
| `AgentReport` | 에이전트 개별 결과 |
| `AnalysisResult` | Supervisor 최종 결과 |

**`AgentReport` 예시 구조:**

```json
{
  "agent": "financial",
  "signal": "bullish",
  "confidence": 0.75,
  "horizon": "medium",
  "summary": "005930 재무 관점: bullish. 영업이익률 15.0%, ROE 12.0%.",
  "key_points": ["매출이 전년 대비 성장 중", "ROE 양호"],
  "evidence": [{"source": "financial_data", "metric": "roe", "value": "0.12"}],
  "risks": [],
  "raw_data": {}
}
```

#### `weights.py`

Supervisor가 사용하는 에이전트별 가중치입니다. `horizon`에 따라 자동 조정됩니다.

| Horizon | Financial | Chart | Macro | News |
|---------|-----------|-------|-------|------|
| short | 0.15 | 0.35 | 0.15 | 0.35 |
| medium | 0.30 | 0.25 | 0.20 | 0.25 |
| long | 0.45 | 0.10 | 0.30 | 0.15 |

---

### `alphabet/services/` — 데이터 수집 레이어

에이전트와 외부 API 사이의 중간 계층입니다. 현재는 **스텁(가짜) 데이터**를 반환하며, 실제 API 연동 시 이 레이어만 수정하면 됩니다.

#### `financial_data.py`

재무제표·밸류에이션 데이터를 제공합니다.

- **반환 지표**: 매출성장률, 영업이익률, ROE, 부채비율, PER, PBR
- **추후 연동**: DART Open API, SEC EDGAR, yfinance fundamentals

#### `market_data.py`

OHLCV·기술적 지표 데이터를 제공합니다.

- **반환 데이터**: `PriceBar` 리스트, 기술 스냅샷(종가, SMA20, 추세)
- **추후 연동**: yfinance, pykrx

#### `macro_data.py`

거시경제 지표를 제공합니다.

- **반환 지표**: 기준금리, CPI, USD/KRW, KOSPI 추세, VIX
- **추후 연동**: FRED, 한국은행 ECOS

#### `news_data.py`

뉴스·공시 헤드라인을 제공합니다.

- **반환 데이터**: `NewsItem` 리스트 (title, summary, published_at, source)
- **추후 연동**: NewsAPI, DART 공시, RSS

---

### `alphabet/ml/` — HuggingFace 공통 레이어

여러 에이전트가 공유하는 ML 인프라입니다. `transformers`가 설치되지 않아도 프로젝트 전체가 동작하도록 **lazy import**를 적용했습니다.

#### `hf_client.py`

HuggingFace `pipeline`을 로드·캐시하는 싱글톤 클라이언트입니다.

- 디바이스 자동 선택: CUDA → Apple MPS → CPU
- 동일 모델은 한 번만 로드 (`_pipelines` 캐시)
- `HF_TOKEN`, `HF_CACHE_DIR` 환경 변수 지원

#### `sentiment.py`

FinBERT 등 금융 텍스트 감성 분석기입니다.

- `analyze(text)` → `SentimentResult` (label, score, signal)
- `analyze_batch(texts)` → 리스트
- `aggregate(sentiments)` → 전체 뉴스의 종합 신호

현재 `NewsAgent`에서 사용하며, 추후 `FinancialAgent`(공시 요약) 등에도 확장 가능합니다.

---

### `alphabet/agents/` — 분석 에이전트

#### `base.py`

모든 에이전트의 부모 추상 클래스입니다.

```python
class BaseAgent(ABC):
    name: AgentName

    async def analyze(self, request: AnalysisRequest) -> AgentReport: ...
    def default_question(self, request: AnalysisRequest) -> str: ...
    def build_question(self, request: AnalysisRequest) -> str: ...
```

- `analyze()`: 핵심 분석 메서드 (async)
- `default_question()`: 에이전트별 기본 질문
- `build_question()`: 사용자 질문이 있으면 그것을, 없으면 기본 질문 반환

#### `financial.py` / `chart.py` / `macro.py` / `news.py`

각 전문 에이전트 구현체입니다. 공통 패턴:

1. `services/`에서 데이터 수집
2. 규칙 기반 또는 HF로 신호 도출
3. `AgentReport` 반환

#### `supervisor.py`

4개 리포트를 받아 `AnalysisResult`를 생성합니다.

- `synthesize()`: 가중 점수 계산 → 최종 signal/confidence
- `_detect_conflicts()`: 상충 신호 탐지
- `analyze()`는 의도적으로 `NotImplementedError` — Supervisor는 직접 분석하지 않음

---

### `alphabet/orchestrator/` — 실행 조율

#### `pipeline.py`

전체 분석 파이프라인의 핵심입니다.

```python
class AnalysisPipeline:
    async def run(request, weights) -> AnalysisResult:
        reports = await self._run_agents_parallel(request)  # asyncio.gather
        return self.supervisor.synthesize(request, reports, weights)
```

- 4개 에이전트를 `asyncio.gather`로 **병렬 실행**
- 각 에이전트에 `agent_timeout_sec` 타임아웃 적용
- `run_analysis()` 함수: CLI·스크립트용 단축 진입점

---

## 데이터 흐름

```
1. 사용자: python -m alphabet.main 005930 -q "지금 사도 될까?"

2. main.py
   → AnalysisRequest(ticker="005930", question="지금 사도 될까?")

3. pipeline.py
   → FinancialAgent.analyze()  ─┐
   → ChartAgent.analyze()      ─┤ asyncio 병렬
   → MacroAgent.analyze()      ─┤
   → NewsAgent.analyze()       ─┘
   → 각각 AgentReport 반환

4. SupervisorAgent.synthesize()
   → horizon=medium 가중치 적용
   → weighted_score 계산
   → 상충 감지
   → AnalysisResult 반환

5. main.py → JSON 출력
```

---

## 설치 및 실행

### 요구 사항

- Python 3.11+
- (선택) Apple Silicon Mac에서 MPS 가속, 또는 CUDA GPU

### 설치

```bash
# 가상환경 생성 (권장)
python3.13 -m venv .venv
source .venv/bin/activate

# 패키지 설치
pip install -e .

# 환경 변수 설정
cp .env.example .env
# .env 파일에 HF_TOKEN 등 입력
```

### 실행

```bash
# 기본 분석 (스텁 데이터, HF 없이)
python -m alphabet.main 005930

# 질문 지정
python -m alphabet.main 005930 -q "장기 투자 관점에서 어떤가?"

# 미국 주식
python -m alphabet.main AAPL -m US

# HuggingFace 감성 분석 포함 (FinBERT 다운로드 필요)
python -m alphabet.main 005930 --hf
```

### Python 코드에서 사용

```python
import asyncio
from alphabet.orchestrator.pipeline import run_analysis

result = asyncio.run(run_analysis("005930", question="지금 매수 타이밍인가?"))
print(result.final_signal)   # bullish / neutral / bearish
print(result.summary)
print(result.conflicts)
```

---

## 환경 변수

`.env.example`을 `.env`로 복사해 설정합니다.

```env
# HuggingFace
HF_TOKEN=hf_xxxxxxxx          # gated 모델 접근 시 필요
HF_DEVICE=auto                # auto | cpu | mps | cuda
# HF_CACHE_DIR=./.cache/huggingface

# 외부 API (추후 연동)
# DART_API_KEY=
# NEWS_API_KEY=
```

---

## 설계 원칙

### 1. 단일 패키지 (모노레포)

모든 에이전트가 `alphabet` 패키지 안에 있어 import, 테스트, 배포가 단순합니다.

### 2. 관심사 분리

```
services  →  "데이터를 어디서 가져오나"
agents    →  "데이터를 어떻게 해석하나"
ml        →  "ML 모델을 어떻게 로드·실행하나"
orchestrator → "언제, 어떤 순서로 실행하나"
schemas   →  "에이전트 간 무엇을 주고받나"
```

### 3. 공통 출력 스키마

모든 에이전트가 `AgentReport`를 반환하므로 Supervisor 통합, 로깅, UI 렌더링이 일관됩니다.

### 4. HF Lazy Load

`transformers`/`torch` 없이도 스텁 데이터로 전체 파이프라인을 테스트할 수 있습니다. `--hf` 플래그로 필요할 때만 모델을 로드합니다.

### 5. Horizon 기반 가중치

"지금 사도 되나?"(short)와 "3년 들고 가도 되나?"(long)는 다른 에이전트 비중이 필요합니다. `weights.py`에서 자동 조정합니다.

### 6. 근거 기반 출력

모든 `AgentReport`에 `evidence` 필드가 있어, 결론 없이 "매수 추천"만 내지 않도록 설계했습니다.

---

## 향후 작업

### 데이터 연동 (services/)

| 파일 | 연동 대상 | 우선순위 |
|------|----------|---------|
| `financial_data.py` | DART Open API, yfinance | 높음 |
| `market_data.py` | yfinance, pykrx | 높음 |
| `macro_data.py` | FRED, 한국은행 ECOS | 중간 |
| `news_data.py` | NewsAPI, DART 공시 | 높음 |

### HF 확장 (ml/ + agents/)

| 에이전트 | 활용 모델 | 용도 |
|---------|----------|------|
| NewsAgent | FinBERT (현재) | 뉴스 감성 분석 |
| FinancialAgent | BART | 공시·재무 보고서 요약 |
| ChartAgent | 시계열 모델 | 추세 예측 (추후) |

### 오케스트레이션

- LangGraph 기반 상태 머신으로 전환 (조건부 재분석, 에이전트 간 피드백)
- Web API (FastAPI) 엔드포인트 추가
- 캐싱 레이어 (재무·거시: 일 1회, 차트·뉴스: 더 자주)

---

## 라이선스

MIT (추후 명시)
