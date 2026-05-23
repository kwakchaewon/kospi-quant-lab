# 환경 설정 및 실행 가이드

## 1. 사전 요구사항

- Python 3.9 이상
- 한국투자증권 Open API 계정 (APP_KEY, APP_SECRET 발급 필요)

## 2. 패키지 설치

```bash
pip install requests beautifulsoup4 yfinance
```

| 패키지 | 용도 |
|---|---|
| `requests` | KIS API, 네이버 크롤링 |
| `beautifulsoup4` | 네이버 HTML 파싱 (없으면 regex 폴백 동작) |
| `yfinance` | Yahoo Finance 데이터 수집 |

## 3. API 키 설정

`appkey.txt.example`을 참고하여 `appkey.txt`를 생성합니다.

```
YOUR_APP_KEY_HERE
YOUR_APP_SECRET_HERE
```

- 1번째 줄: KIS API APP_KEY
- 2번째 줄: KIS API APP_SECRET
- `appkey.txt`는 `.gitignore`에 등록되어 저장소에 포함되지 않습니다.

## 4. 관심종목 설정

`stock_list.json`을 편집하여 분석할 종목을 입력합니다.

```json
[
  {"종목코드": "005930", "종목명": "삼성전자"},
  {"종목코드": "000660", "종목명": "SK하이닉스"},
  {"종목코드": "079550", "종목명": "LIG넥스원"}
]
```

- 종목코드: 6자리 KOSPI/KOSDAQ 종목코드

## 5. 실행 방법

### 전체 파이프라인 (권장)

```bash
run_final.bat
```

배치 파일이 아래 5단계를 순서대로 실행합니다.

```
[1/5] auto_update.py         → stock_data.json
[2/5] naver_crawl.py         → naver_ma_data.json
[3/5] naver_investor_crawl.py → naver_investor_data.json
[4/5] yfinance_crawl.py      → yfinance_data.json
[5/5] merge_data.py          → stock_data_full.json
```

### 개별 실행

```bash
python auto_update.py          # KIS API 데이터 수집
python naver_crawl.py          # 네이버 MA/RSI/ATR 수집
python naver_investor_crawl.py # 투자자 매매동향 수집
python yfinance_crawl.py       # Yahoo Finance 실적/밸류 수집
python merge_data.py           # 병합 + Factor 계산
```

## 6. 출력 확인

`stock_data_full.json`이 생성되면 상단 `집계` 필드에서 Factor 결과를 확인합니다.

```json
{
  "집계": {
    "분석일": "2026-05-23",
    "전체_종목수": 20,
    "F1F2_모두충족": {"개수": 3, "종목": ["삼성전자", ...]},
    "F1만_충족":    {"개수": 5, "종목": [...]},
    "F2만_충족":    {"개수": 2, "종목": [...]},
    "둘다_미충족":  {"개수": 10, "종목": [...]}
  },
  "종목": [...]
}
```

## 7. Access Token 갱신

KIS API Access Token이 만료된 경우:

```bash
python refresh_token.py
```

`appkey.txt`에 갱신된 토큰이 자동으로 업데이트됩니다.

## 8. 주의사항

- `naver_crawl.py`는 네이버 서버 부하 방지를 위해 종목당 0.5초 대기합니다.
- `yfinance_crawl.py`는 Yahoo Finance 응답 지연으로 종목당 2초 대기합니다.
- 종목 수가 많을 경우 전체 실행 시간이 길어질 수 있습니다.
- KIS API는 실시간 시세를 제공하므로 장 마감 후 실행을 권장합니다.
