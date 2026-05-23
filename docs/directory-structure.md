# 디렉토리 구조

```
kospi-quant-lab/
│
├── docs/                          # 프로젝트 문서
│   ├── architecture.md            # 시스템 아키텍처 개요
│   ├── directory-structure.md     # 이 파일
│   ├── factors.md                 # Factor 1~4 판단 로직 상세
│   └── setup.md                   # 환경 설정 및 실행 가이드
│
├── auto_update.py                 # KIS Open API 데이터 수집
├── naver_crawl.py                 # 네이버 금융 기술 지표 크롤링
├── naver_investor_crawl.py        # 네이버 투자자 매매동향 크롤링
├── yfinance_crawl.py              # Yahoo Finance 실적/밸류 수집
├── merge_data.py                  # 4개 소스 병합 + Factor 계산
├── refresh_token.py               # KIS API Access Token 갱신 유틸리티
│
├── run_final.bat                  # 전체 파이프라인 일괄 실행 (Windows)
│
├── stock_list.json                # 관심종목 목록 (입력값)
│
├── appkey.txt.example             # API 키 형식 예시 (실제 키 X)
├── appkey.txt                     # API 키 (gitignore — 로컬 전용)
│
└── .gitignore
```

## 파일 설명

### 스크립트

| 파일 | 설명 |
|---|---|
| `auto_update.py` | `KISStockAPI` 클래스. 현재가·일봉 차트를 조회하여 MA5/20, RSI(14), STOCH(9)을 계산 후 `stock_data.json`에 저장 |
| `naver_crawl.py` | `NaverFinanceCrawler` 클래스. 네이버 차트 XML API(`fchart.stock.naver.com`)에서 200일 일봉을 파싱해 MA60/120, RSI, ATR, 최근20일고가를 계산 후 `naver_ma_data.json`에 저장 |
| `naver_investor_crawl.py` | `NaverInvestorCrawler` 클래스. 네이버 `frgn.naver` 페이지를 크롤링(BS4 또는 regex 폴백)하여 기관/외국인 일별 순매수 데이터 20거래일 분을 `naver_investor_data.json`에 저장 |
| `yfinance_crawl.py` | yfinance 라이브러리로 Yahoo Finance에서 Forward PE, 어닝서프라이즈, 다음 실적발표일, 목표주가, 연간 영업이익을 수집해 `yfinance_data.json`에 저장 |
| `merge_data.py` | 위 4개 JSON을 종목코드 기준으로 병합하고 Factor 1(기술), Factor 2(수급)를 계산. 결과를 `stock_data_full.json`에 저장 |
| `refresh_token.py` | `appkey.txt`에서 키를 읽어 KIS API Access Token을 재발급하고 파일에 덮어씀 |

### 데이터 파일 (gitignore 대상)

| 파일 | 설명 |
|---|---|
| `stock_data.json` | `auto_update.py` 출력 — 종목별 현재가·MA·RSI |
| `naver_ma_data.json` | `naver_crawl.py` 출력 — 종목별 MA60/120·ATR |
| `naver_investor_data.json` | `naver_investor_crawl.py` 출력 — 투자자 매매동향 |
| `yfinance_data.json` | `yfinance_crawl.py` 출력 — 실적·밸류 데이터 |
| `stock_data_full.json` | `merge_data.py` 최종 출력 — 전체 병합 + Factor 결과 |

### 설정 파일

| 파일 | 설명 |
|---|---|
| `stock_list.json` | 분석 대상 종목 리스트. `[{"종목코드":"005930","종목명":"삼성전자"}]` 형식 |
| `appkey.txt` | KIS API 인증 키. 1번째 줄: APP_KEY, 2번째 줄: APP_SECRET (gitignore) |
| `appkey.txt.example` | `appkey.txt` 형식 예시 템플릿 |
| `run_final.bat` | 5단계 파이프라인 순차 실행 배치 파일 |
