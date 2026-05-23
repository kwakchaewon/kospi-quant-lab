# 시스템 아키텍처

## 개요

KOSPI 관심종목에 대해 **기술 지표 + 수급 + 실적/밸류** 데이터를 자동 수집하고,
Factor 1~4 기준으로 종목을 분류하는 데이터 파이프라인입니다.

## 전체 흐름

```
[stock_list.json]  ← 관심종목 입력
        │
        ├──▶ auto_update.py        (KIS Open API)
        │         └─▶ stock_data.json
        │
        ├──▶ naver_crawl.py        (네이버 금융 크롤링)
        │         └─▶ naver_ma_data.json
        │
        ├──▶ naver_investor_crawl.py (네이버 투자자 매매동향)
        │         └─▶ naver_investor_data.json
        │
        └──▶ yfinance_crawl.py     (Yahoo Finance)
                  └─▶ yfinance_data.json
                            │
                            ▼
                     merge_data.py
                            │
                            ▼
                   stock_data_full.json  ← 최종 출력
                  (Factor 1~4 분석 포함)
```

## 데이터 소스별 역할

| 스크립트 | 데이터 소스 | 수집 항목 |
|---|---|---|
| `auto_update.py` | 한국투자증권 Open API | 현재가, 거래량, MA5/20, RSI, STOCH |
| `naver_crawl.py` | 네이버 금융 차트 API | MA60/120, RSI(보조), ATR, 최근20일고가, PER |
| `naver_investor_crawl.py` | 네이버 투자자 매매동향 | 기관/외국인 일별 순매수량·금액 (최근 20거래일) |
| `yfinance_crawl.py` | Yahoo Finance | Forward PE, 어닝서프라이즈, 다음 실적발표일, 목표주가 |

## Factor 분류 결과

`merge_data.py`가 4개 JSON을 병합하여 종목별로 아래 4가지 Factor를 평가합니다.

| Factor | 판단 기준 | 데이터 출처 |
|---|---|---|
| F1 기술 | 이동평균 정배열 + RSI 범위 | KIS API + 네이버 MA |
| F2 수급 | 기관/외국인 누적 순매수 패턴 | 네이버 투자자 매매동향 |
| F3 실적 | 어닝서프라이즈, 영업이익 YoY | Claude 웹검색 (placeholder) |
| F4 밸류 | PER, Forward PE | Claude 웹검색 (placeholder) |

F1·F2는 자동 계산되고, F3·F4는 `stock_data_full.json`을 Claude에 업로드하여 웹검색으로 보완합니다.

## 인증

KIS Open API 인증은 `appkey.txt`에서 APP_KEY / APP_SECRET을 읽어 OAuth2 Bearer 토큰을 발급받습니다.
해당 파일은 `.gitignore`로 관리되며 저장소에 포함되지 않습니다.
