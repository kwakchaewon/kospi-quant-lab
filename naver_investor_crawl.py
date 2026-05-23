"""
네이버 증권 투자자별 매매동향 크롤링
URL: https://finance.naver.com/item/frgn.naver?code={code}

테이블 컬럼 구조 (type2 테이블, 인덱스 3):
  col0: 날짜
  col1: 종가
  col2: 전일비
  col3: 등락률
  col4: 거래량
  col5: 기관 순매매량  ← 기관합계 net buy/sell (주)
  col6: 외국인 순매매량 ← 외국인합계 net buy/sell (주)
  col7: 외국인 보유주수
  col8: 외국인 보유율
"""

import sys
import io
import requests
import json
import time
import re

# Windows 터미널 UTF-8 출력 처리
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# frgn.naver 페이지에서 데이터 테이블의 인덱스 (0-base)
TABLE_INDEX = 3

# 데이터 컬럼 인덱스
COL_DATE      = 0
COL_CLOSE     = 1
COL_VOLUME    = 4
COL_INST_NET  = 5   # 기관 순매매량
COL_FRGN_NET  = 6   # 외국인 순매매량
COL_FRGN_HOLD = 7   # 외국인 보유주수
COL_FRGN_RATE = 8   # 외국인 보유율


class NaverInvestorCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://finance.naver.com',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }

    # ------------------------------------------------------------------ #
    #  공개 메서드                                                          #
    # ------------------------------------------------------------------ #

    def get_investor_data(self, ticker, stock_name='', days=20):
        """최근 N거래일 기관/외국인/개인 순매매 데이터 수집"""
        print(f'  [{stock_name}({ticker})] 투자자 데이터...', end=' ', flush=True)

        try:
            url = f'https://finance.naver.com/item/frgn.naver?code={ticker}'
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'euc-kr'

            if resp.status_code != 200:
                print(f'HTTP {resp.status_code}')
                return self._empty(ticker, stock_name)

            records = self._parse(resp.text, days)

            if not records:
                print('데이터 없음')
                return self._empty(ticker, stock_name)

            print(f'OK ({len(records)}거래일)')
            return {
                '종목코드': ticker,
                '종목명':   stock_name,
                '투자자_매매동향': records,
            }

        except Exception as e:
            print(f'오류: {str(e)[:50]}')
            return self._empty(ticker, stock_name)

    # ------------------------------------------------------------------ #
    #  내부: 파싱                                                           #
    # ------------------------------------------------------------------ #

    def _parse(self, html, days):
        if BS4_AVAILABLE:
            return self._parse_bs4(html, days)
        return self._parse_regex(html, days)

    def _parse_bs4(self, html, days):
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')

        if len(tables) <= TABLE_INDEX:
            return []

        table = tables[TABLE_INDEX]
        records = []

        for row in table.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) <= COL_FRGN_NET:
                continue

            date_txt = tds[COL_DATE].get_text(strip=True)
            if not re.match(r'\d{4}\.\d{2}\.\d{2}', date_txt):
                continue

            try:
                close     = self._to_int(tds[COL_CLOSE].get_text(strip=True))
                volume    = self._to_int(tds[COL_VOLUME].get_text(strip=True))
                inst_net  = self._to_int(tds[COL_INST_NET].get_text(strip=True))
                frgn_net  = self._to_int(tds[COL_FRGN_NET].get_text(strip=True))
                frgn_hold = self._to_int(tds[COL_FRGN_HOLD].get_text(strip=True)) if len(tds) > COL_FRGN_HOLD else None
                frgn_rate = tds[COL_FRGN_RATE].get_text(strip=True) if len(tds) > COL_FRGN_RATE else None

                records.append(self._make_record(
                    date_txt, close, volume,
                    frgn_net, inst_net,
                    frgn_hold, frgn_rate,
                ))
                if len(records) >= days:
                    break

            except Exception:
                continue

        return records

    def _parse_regex(self, html, days):
        """BeautifulSoup 없을 때 regex 폴백"""
        td_pat  = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
        tag_pat = re.compile(r'<[^>]+>')

        def clean(raw):
            return tag_pat.sub('', raw).replace(',', '').replace('+', '').strip()

        tds = [clean(m) for m in td_pat.findall(html)]

        records = []
        i = 0
        while i < len(tds) - COL_FRGN_NET:
            if re.match(r'\d{4}\.\d{2}\.\d{2}', tds[i]):
                try:
                    date_txt  = tds[i]
                    close     = self._to_int(tds[i + COL_CLOSE])
                    volume    = self._to_int(tds[i + COL_VOLUME])
                    inst_net  = self._to_int(tds[i + COL_INST_NET])
                    frgn_net  = self._to_int(tds[i + COL_FRGN_NET])
                    frgn_hold = self._to_int(tds[i + COL_FRGN_HOLD]) if i + COL_FRGN_HOLD < len(tds) else None
                    frgn_rate = tds[i + COL_FRGN_RATE] if i + COL_FRGN_RATE < len(tds) else None

                    records.append(self._make_record(
                        date_txt, close, volume,
                        frgn_net, inst_net,
                        frgn_hold, frgn_rate,
                    ))
                    if len(records) >= days:
                        break
                    i += 9
                except Exception:
                    i += 1
            else:
                i += 1

        return records

    # ------------------------------------------------------------------ #
    #  내부: 유틸                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_int(text):
        txt = re.sub(r'[^\d\-]', '', str(text).strip())
        if not txt or txt == '-':
            return 0
        try:
            return int(txt)
        except ValueError:
            return 0

    @staticmethod
    def _make_record(date, close, volume,
                     frgn_net, inst_net,
                     frgn_hold, frgn_rate):
        """
        금액(원) = 순매매량(주) × 종가(원)  [근사값]
        """
        return {
            '날짜':              date,
            '종가':              close,
            '거래량':            volume,
            '외국인_순매수_수량':  frgn_net,
            '외국인_순매수_금액':  frgn_net * close,
            '기관_순매수_수량':    inst_net,
            '기관_순매수_금액':    inst_net * close,
            '외국인_보유주수':     frgn_hold,
            '외국인_보유율':       frgn_rate,
        }

    @staticmethod
    def _empty(ticker, stock_name):
        return {
            '종목코드': ticker,
            '종목명':   stock_name,
            '투자자_매매동향': [],
        }


# ------------------------------------------------------------------ #
#  main                                                               #
# ------------------------------------------------------------------ #

def main():
    print('=' * 60)
    print('네이버 증권 투자자별 매매동향 크롤링 (최근 20거래일)')
    print('=' * 60)

    if not BS4_AVAILABLE:
        print('BeautifulSoup4 미설치 - regex 폴백 모드')
        print('  정확도 향상: pip install beautifulsoup4')
    print()

    try:
        with open('stock_list.json', 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
        print(f'관심종목: {len(stock_list)}개\n')
    except FileNotFoundError:
        print('stock_list.json 파일이 없습니다.')
        sys.exit(1)

    crawler  = NaverInvestorCrawler()
    all_data = []
    failed   = []

    print('=' * 60)
    for stock in stock_list:
        ticker = stock['종목코드']
        name   = stock['종목명']

        result = crawler.get_investor_data(ticker, name, days=20)
        all_data.append(result)

        if not result['투자자_매매동향']:
            failed.append(f"{name}({ticker})")

        time.sleep(0.5)

    # 저장
    with open('naver_investor_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # 결과 리포트
    print('\n' + '=' * 60)
    ok = len(all_data) - len(failed)
    print(f'수집 성공: {ok}/{len(stock_list)}개')
    if failed:
        print(f'실패 ({len(failed)}개):')
        for s in failed:
            print(f'  - {s}')
    print(f'저장 완료: naver_investor_data.json')
    print('=' * 60)

    # 샘플 출력
    sample = next((d for d in all_data if d['투자자_매매동향']), None)
    if sample:
        print(f"\n샘플 - {sample['종목명']}({sample['종목코드']})")
        print(f"  {'날짜':<12} {'외국인순매수':>12}주 {'금액':>8}억  "
              f"{'기관순매수':>12}주 {'금액':>8}억")
        print(f"  {'-'*60}")
        for row in sample['투자자_매매동향'][:5]:
            fa = row['외국인_순매수_금액'] / 1e8
            ia = row['기관_순매수_금액']  / 1e8
            print(f"  {row['날짜']:<12} "
                  f"{row['외국인_순매수_수량']:>+12,}주 {fa:>+8.1f}억  "
                  f"{row['기관_순매수_수량']:>+12,}주 {ia:>+8.1f}억")


if __name__ == '__main__':
    main()
