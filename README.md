# KOSPI Quant Lab

KOSPI/KOSDAQ 관심종목에 대해 **기술 지표 + 수급 + 실적/밸류** 데이터를 자동 수집하고,
Factor 1~4 기준으로 종목을 분류하는 퀀트 데이터 파이프라인입니다.

## 주요 기능

- **KIS Open API** — 현재가, MA5/20, RSI(14), STOCH(9) 자동 수집
- **네이버 금융 크롤링** — MA60/120, ATR(14), 최근 20일 고가
- **투자자 매매동향** — 기관/외국인 일별 순매수량·금액 (최근 20거래일)
- **Yahoo Finance** — Forward PE, 어닝서프라이즈, 다음 실적발표일, 목표주가
- **Factor 자동 계산** — 수집 데이터를 바탕으로 F1(기술), F2(수급) 판단

## 빠른 시작

### 1. 패키지 설치

```bash
pip install requests beautifulsoup4 yfinance
```

### 2. API 키 설정

```bash
cp appkey.txt.example appkey.txt
# appkey.txt 편집 — 1번째 줄: APP_KEY, 2번째 줄: APP_SECRET
```

### 3. 관심종목 입력

`stock_list.json`에 분석할 종목을 입력합니다.

```json
[
  {"종목코드": "005930", "종목명": "삼성전자"},
  {"종목코드": "000660", "종목명": "SK하이닉스"}
]
```

### 4. 전체 파이프라인 실행

```bash
run_final.bat
```

실행 순서: KIS API → 네이버 MA → 네이버 수급 → Yahoo Finance → 병합

최종 결과: `stock_data_full.json`

## 파이프라인 구조

```
stock_list.json
    │
    ├── auto_update.py          → stock_data.json
    ├── naver_crawl.py          → naver_ma_data.json
    ├── naver_investor_crawl.py → naver_investor_data.json
    └── yfinance_crawl.py       → yfinance_data.json
                                         │
                                   merge_data.py
                                         │
                                 stock_data_full.json
                               (Factor 1~4 분석 포함)
```

## Factor 판단 기준

| Factor | 설명 | 자동화 |
|---|---|---|
| F1 기술 | 이동평균 정배열 + RSI 범위 (케이스A: 눌림, 케이스B: 돌파) | 자동 계산 |
| F2 수급 | 기관/외국인 누적 순매수 패턴 (탈락 조건 + 충족 조건) | 자동 계산 |
| F3 실적 | 어닝서프라이즈, 영업이익 YoY | Claude 웹검색 보완 |
| F4 밸류 | PER, Forward PE | Claude 웹검색 보완 |

### Factor 1 — 기술 (가격 위치)

두 케이스 중 하나를 충족하면 ✅ 충족.

**케이스A — 정배열 눌림**

| 조건 | 내용 |
|---|---|
| 현재가 > MA60 AND MA120 | 장기 정배열 유지 |
| 현재가 ≤ MA20 | 단기 이평선 아래로 눌림 |
| 40 ≤ RSI ≤ 78 | 과매도 아님, 과매수 아님 |

**케이스B — 정배열 돌파**

| 조건 | 내용 |
|---|---|
| 현재가 > MA20 > MA60 | 단·중기 정배열 |
| 현재가 ≥ 최근 20일 고가 × 0.87 | 고점 부근 (13% 이내) |
| 45 ≤ RSI ≤ 78 | 모멘텀 살아있고 과열 아님 |

---

### Factor 2 — 수급 (기관/외국인)

탈락 조건이 하나라도 해당되면 즉시 ❌ 미충족. 탈락 없을 때 충족 조건 3개 AND.

**탈락 조건 (강제 미충족)**

| 번호 | 조건 |
|---|---|
| 탈락1 | 외국인 최근 2일 연속 순매도 |
| 탈락2 | 기관 최근 5일 중 순매도 ≥ 3일 |
| 탈락3 | 최근 5일 기관+외국인 동시 순매수 0일 |

**충족 조건 (3개 AND)**

| 번호 | 조건 |
|---|---|
| 조건1 | 기관 20일 누적 순매수 > 0 AND 20일 중 순매수 ≥ 10일 |
| 조건2 | 외국인 최근 5일 중 순매수 ≥ 3일 |
| 조건3 | 최근 5일 기관+외국인 동시 순매수 ≥ 2일 |

---

### Factor 3 — 실적

3개 항목 중 2개 이상 충족 시 ✅ 충족.

| 번호 | 조건 |
|---|---|
| ① | 어닝서프라이즈 +5% 초과 |
| ② | 영업이익 분기 YoY 증가 |
| ③ | 목표주가 3개월 상향 |

---

### Factor 4 — 밸류

**Fwd PER ÷ 업종 평균 PER** 비율로 판단.

| 비율 | 판정 |
|---|---|
| < 1.0 | ✅ 충족 |
| 1.0 ~ 1.3 | 유지 |
| > 1.3 | ⚠️ 주의 |
| > 2.0 | ❌ 미충족 |

F3/F4는 `stock_data_full.json`에 `null` placeholder로 저장되며 Claude 웹검색으로 수동 보완합니다.

## 문서

- [아키텍처](docs/architecture.md) — 전체 시스템 구조 및 데이터 흐름
- [디렉토리 구조](docs/directory-structure.md) — 파일별 역할 설명
- [Factor 로직](docs/factors.md) — F1~F4 현행 기준 (변경 커밋 시 이전 버전이 자동 아카이빙됨)
- [Factor 변경 이력](docs/factor-history/) — 과거 버전 스냅샷 (`factors_YYYY-MM-DD.md`)
- [환경 설정](docs/setup.md) — 설치, API 키 설정, 실행 가이드

## 보안

`appkey.txt`는 KIS API 인증 키를 포함하며 `.gitignore`로 관리됩니다.
저장소에는 형식 예시 파일(`appkey.txt.example`)만 포함됩니다.
