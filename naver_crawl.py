"""
네이버 금융 크롤링 - MA60, MA120 수집
"""

import sys
import requests
import json
import time
import re
from datetime import datetime

class NaverFinanceCrawler:
    def __init__(self):
        self.base_url = "https://finance.naver.com/item/main.naver"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def _parse_per(self, html):
        """main.naver 페이지에서 PER, FPER 파싱"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', {'class': 'per_table'})
            if not table:
                return None, None
            rows = table.find_all('tr')
            def first_float(text):
                m = re.search(r'[\d,.]+', text.replace(',', ''))
                if m:
                    try:
                        return float(m.group().replace(',', ''))
                    except ValueError:
                        return None
                return None
            per  = first_float(rows[0].find('td').get_text()) if len(rows) > 0 and rows[0].find('td') else None
            fper = first_float(rows[1].find('td').get_text()) if len(rows) > 1 and rows[1].find('td') else None
            return per, fper
        except Exception:
            return None, None

    def get_moving_averages(self, ticker, stock_name=""):
        """MA60, MA120, PER, FPER 수집"""
        print(f"  {stock_name}({ticker}) 크롤링 중...", end=" ")

        try:
            # 네이버 금융 페이지 접근
            url = f"{self.base_url}?code={ticker}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            html = response.text
            
            # MA60, MA120 추출 (HTML 파싱)
            # 네이버 금융에서 이동평균선은 차트 데이터 API로 제공
            chart_url = f"https://fchart.stock.naver.com/sise.nhn?symbol={ticker}&timeframe=day&count=200&requestType=0"
            chart_response = None
            for attempt in range(3):
                chart_response = requests.get(chart_url, headers=self.headers, timeout=10)
                if chart_response.status_code == 200:
                    break
                time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1.0s, 2.0s

            if chart_response and chart_response.status_code == 200:
                # XML 파싱하여 최근 120일 데이터 수집
                chart_data = self._parse_chart_data(chart_response.text)

                if len(chart_data) >= 120:
                    # MA60, MA120, RSI_14, ATR_14 계산
                    ma60   = self._calculate_ma(chart_data, 60)
                    ma120  = self._calculate_ma(chart_data, 120)
                    rsi14  = self._calculate_rsi(chart_data, 14)
                    atr14  = self._calculate_atr(chart_data, 14)
                    high20 = self._calculate_high20(chart_data)

                    if ma60 is not None and ma120 is not None:
                        ratio = ma60 / ma120
                        if ratio < 0.5 or ratio > 2.0:
                            print(f"[WARN] MA sanity warning {ticker}: MA60={ma60:,} MA120={ma120:,} ratio={ratio:.2f}")

                    per, fper = self._parse_per(html)
                    print("OK")
                    return {
                        "종목코드": ticker,
                        "종목명": stock_name,
                        "MA60":      ma60,
                        "MA120":     ma120,
                        "RSI_14":    rsi14,
                        "ATR_14":    atr14,
                        "최근20일고가": high20,
                        "PER":       per,
                        "FPER":      fper,
                    }
                else:
                    print("[WARN] (데이터 부족)")
                    return {
                        "종목코드": ticker,
                        "종목명": stock_name,
                        "MA60":      None,
                        "MA120":     None,
                        "RSI_14":    None,
                        "ATR_14":    None,
                        "최근20일고가": None,
                        "PER":       None,
                        "FPER":      None,
                    }
            else:
                print("FAIL")
                return None

        except Exception as e:
            print(f"[ERR] ({str(e)[:30]})")
            return {
                "종목코드": ticker,
                "종목명": stock_name,
                "MA60":      None,
                "MA120":     None,
                "RSI_14":    None,
                "ATR_14":    None,
                "최근20일고가": None,
                "PER":       None,
                "FPER":      None,
            }
    
    def _parse_chart_data(self, xml_text):
        """차트 데이터 XML 파싱"""
        import re

        # <item data="날짜|시가|고가|저가|종가|거래량" /> 형식 파싱
        pattern = r'data="([^"]+)"'
        matches = re.findall(pattern, xml_text)

        items = []
        for match in matches:
            parts = match.split('|')
            if len(parts) >= 6:
                try:
                    items.append({
                        "date":  parts[0],
                        "high":  int(parts[2]),
                        "low":   int(parts[3]),
                        "close": int(parts[4]),
                    })
                except:
                    continue

        items.sort(key=lambda x: x["date"])    # 날짜 오름차순 강제 정렬
        return items
    
    def _calculate_high20(self, candles):
        """최근 20일 고가 계산"""
        if len(candles) < 20:
            return None
        return max(c["high"] for c in candles[-20:])

    def _calculate_ma(self, candles, period):
        """이동평균선 계산"""
        if len(candles) < period:
            return None

        prices = [c["close"] for c in candles[-period:]]
        return int(sum(prices) / period)

    def _calculate_rsi(self, candles, period=14):
        """RSI 계산"""
        if len(candles) < period + 1:
            return None

        prices = [c["close"] for c in candles[-(period + 1):]]
        gains, losses = [], []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def _calculate_atr(self, candles, period=14):
        """ATR(14) 계산"""
        if len(candles) < period + 1:
            return None

        recent = candles[-(period + 1):]
        trs = []
        for i in range(1, len(recent)):
            high      = recent[i]["high"]
            low       = recent[i]["low"]
            prev_close = recent[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)

        return round(sum(trs) / period)


def main():
    print("=" * 60)
    print("네이버 금융 크롤링 시스템 (MA60, MA120)")
    print("=" * 60)
    
    # 종목 리스트 로드
    try:
        with open('stock_list.json', 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
        print(f"\n관심종목: {len(stock_list)}개")
    except FileNotFoundError:
        print("\n[ERR] stock_list.json 파일이 없습니다.")
        sys.exit(1)
    
    # 크롤러 초기화
    crawler = NaverFinanceCrawler()
    
    # 데이터 수집
    print("\n" + "=" * 60)
    all_data = []
    failed_stocks = []
    for stock in stock_list:
        ticker = stock['종목코드']
        name = stock['종목명']
        data = crawler.get_moving_averages(ticker, name)
        if data:
            all_data.append(data)
        else:
            failed_stocks.append(f"{name}({ticker})")
        time.sleep(0.5)  # 0.5초 대기 (과도한 요청 방지)

    # 결과 저장
    with open('naver_ma_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # 검증 결과 출력
    print("=" * 60)
    if len(all_data) == len(stock_list):
        print(f"[OK] 전체 {len(stock_list)}개 종목 모두 수집 완료")
    else:
        print(f"[WARN] 수집 완료: {len(all_data)}/{len(stock_list)}개")
        print(f"[FAIL] 실패 종목 ({len(failed_stocks)}개):")
        for s in failed_stocks:
            print(f"   - {s}")
    print(f"저장 완료: naver_ma_data.json")
    print("=" * 60)
    
    # 샘플 출력
    if all_data:
        print("\n샘플 데이터:")
        sample = all_data[0]
        print(f"  종목: {sample['종목명']}({sample['종목코드']})")
        if sample['MA60']:
            print(f"  MA60: {sample['MA60']:,}원")
        if sample['MA120']:
            print(f"  MA120: {sample['MA120']:,}원")


if __name__ == "__main__":
    main()
