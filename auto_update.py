"""
완전 자동화 주식 차트 업데이트 시스템
Notion 관심종목 DB → 한국투자증권 API → Notion DB 자동 업데이트
"""

import sys
import requests
import json
import time
from datetime import datetime

class KISStockAPI:
    """한국투자증권 Open API 클래스"""
    
    def __init__(self, app_key, app_secret):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.access_token = None
        
    def get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                result = response.json()
                self.access_token = result['access_token']
                print("[OK] KIS API 토큰 발급 성공")
                return True
            else:
                print(f"[FAIL] 토큰 발급 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERR] 토큰 발급 오류: {e}")
            return False
    
    def get_current_price(self, ticker):
        """현재가 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['rt_cd'] == '0':
                    output = data['output']
                    return {
                        "현재가": int(output['stck_prpr']),
                        "거래량": int(output['acml_vol'])
                    }
            return None
        except Exception as e:
            return None
    
    def get_daily_chart(self, ticker):
        """일봉 차트 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010400"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['rt_cd'] == '0':
                    return data['output']
            return None
        except Exception as e:
            return None
    
    def calculate_ma(self, chart_data, period):
        """이동평균선 계산"""
        if not chart_data or len(chart_data) < period:
            return None
        prices = [int(item['stck_clpr']) for item in chart_data[:period]]
        return int(sum(prices) / len(prices))
    
    def calculate_rsi(self, chart_data, period=14):
        """RSI 계산"""
        if not chart_data or len(chart_data) < period + 1:
            return None
        
        prices = [int(item['stck_clpr']) for item in chart_data[:period + 1]]
        prices.reverse()
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
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
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_stochastic(self, chart_data, k_period=9):
        """STOCH 계산"""
        if not chart_data or len(chart_data) < k_period:
            return None
        
        recent_data = chart_data[:k_period]
        current_close = int(recent_data[0]['stck_clpr'])
        highest_high = max([int(d['stck_hgpr']) for d in recent_data])
        lowest_low = min([int(d['stck_lwpr']) for d in recent_data])
        
        if highest_high == lowest_low:
            return 50.0
        
        stoch_k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        return round(stoch_k, 2)
    
    def get_stock_data(self, ticker, stock_name=""):
        """종목 전체 데이터 수집"""
        print(f"  {stock_name}({ticker}) 수집 중...", end=" ")
        
        price_data = self.get_current_price(ticker)
        if not price_data:
            time.sleep(0.5)
            price_data = self.get_current_price(ticker)
        if not price_data:
            print("FAIL")
            return None

        time.sleep(0.1)

        chart_data = self.get_daily_chart(ticker)
        if not chart_data:
            time.sleep(0.5)
            chart_data = self.get_daily_chart(ticker)
        if not chart_data:
            print("FAIL")
            return None

        prev_volume = int(chart_data[1]['acml_vol']) if len(chart_data) > 1 else None

        result = {
            "종목코드": ticker,
            "종목명": stock_name,
            "현재가": price_data["현재가"],
            "거래량": price_data["거래량"],
            "전일거래량": prev_volume,
            "RSI_14": self.calculate_rsi(chart_data, 14),
            "STOCH_9_6": self.calculate_stochastic(chart_data, 9),
            "MA5": self.calculate_ma(chart_data, 5),
            "MA20": self.calculate_ma(chart_data, 20),
            "MA60": self.calculate_ma(chart_data, 60),
            "MA120": self.calculate_ma(chart_data, 120)
        }
        
        print("OK")
        return result


# ==================== 사용 방법 ====================
# 
# 1. Notion에서 관심종목 리스트 JSON 파일 저장:
#    stock_list.json 형식:
#    [
#      {"종목코드": "079550", "종목명": "LIG넥스원"},
#      {"종목코드": "005930", "종목명": "삼성전자"}
#    ]
#
# 2. Python 실행:
#    python auto_update.py
#
# 3. 결과 JSON 파일 생성:
#    stock_data.json
#
# 4. Claude가 Notion DB에 자동 업데이트
#

def main():
    print("=" * 60)
    print("============================================================")
    print("주식 차트 자동 업데이트 시스템")
    print("============================================================")
    print("=" * 60)
    
    # 1. API 키 설정 (appkey.txt에서 읽기)
    try:
        with open('appkey.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            APP_KEY = lines[0].strip()
            APP_SECRET = lines[1].strip()
        print(f"\n[OK] API 키 로드 완료")
    except FileNotFoundError:
        print("\n[ERR] appkey.txt 파일이 없습니다!")
        print("appkey.txt 파일을 생성하고 다음 형식으로 입력하세요:")
        print("1번째 줄: APP_KEY")
        print("2번째 줄: APP_SECRET")
        sys.exit(1)
    except IndexError:
        print("\n[ERR] appkey.txt 형식이 잘못되었습니다!")
        print("1번째 줄: APP_KEY")
        print("2번째 줄: APP_SECRET")
        sys.exit(1)
    
    # 2. 관심종목 리스트 로드
    try:
        with open('stock_list.json', 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
        print(f"\n관심종목: {len(stock_list)}개")
    except FileNotFoundError:
        print("\n[ERR] stock_list.json 파일이 없습니다.")
        print("Notion에서 먼저 종목 리스트를 생성하세요.")
        sys.exit(1)

    # 3. API 초기화
    api = KISStockAPI(APP_KEY, APP_SECRET)
    if not api.get_access_token():
        print("\n[ERR] API 연동 실패")
        sys.exit(1)
    
    # 4. 전체 종목 데이터 수집
    print("\n" + "=" * 60)
    all_data = []
    failed_stocks = []
    for stock in stock_list:
        ticker = stock['종목코드']
        name = stock['종목명']
        data = api.get_stock_data(ticker, name)
        if data:
            all_data.append(data)
        else:
            failed_stocks.append(f"{name}({ticker})")
        time.sleep(0.15)

    # 5. 결과 저장
    with open('stock_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # 6. 검증 결과 출력
    print("=" * 60)
    success_count = len(all_data)
    total_count = len(stock_list)

    if success_count == total_count:
        print(f"[OK] 전체 {total_count}개 종목 모두 수집 완료")
    else:
        print(f"[WARN] 수집 완료: {success_count}/{total_count}개")
        print(f"[FAIL] 실패 종목 ({len(failed_stocks)}개):")
        for s in failed_stocks:
            print(f"   - {s}")

    print(f"저장 완료: stock_data.json")
    print("=" * 60)

    # 7. 샘플 데이터 출력
    if all_data:
        print("\n샘플 데이터:")
        sample = all_data[0]
        print(f"  종목: {sample['종목명']}({sample['종목코드']})")
        print(f"  현재가: {sample['현재가']:,}원")
        print(f"  RSI: {sample['RSI_14']} | STOCH: {sample['STOCH_9_6']}")
        print(f"  MA5: {sample['MA5']:,}원 | MA20: {sample['MA20']:,}원")


if __name__ == "__main__":
    main()
