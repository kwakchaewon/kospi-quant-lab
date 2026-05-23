"""
데이터 병합 스크립트
KIS API (stock_data.json)
  + 네이버 MA/RSI/ATR (naver_ma_data.json)
  + 네이버 투자자 매매동향 (naver_investor_data.json)
→ stock_data_full.json

F3/F4 필드는 Claude 웹검색으로 채울 placeholder로만 출력됩니다.
yfinance 파생 필드는 품질 문제로 제외되었습니다.
"""

import sys
import json
from datetime import date


def _sum_net(records, key, n):
    """records 앞 n개 항목의 key 합계 (데이터 부족 시 None)"""
    if not records or len(records) < n:
        return None
    return sum(r.get(key, 0) for r in records[:n])


def _factor1(item):
    """
    Factor 1 가격 위치 판단 v4.0 (2026-04-16 변경)

    케이스A (정배열 눌림):
      현재가 > MA60 AND 현재가 > MA120
      AND 현재가 <= MA20
      AND 40 <= RSI <= 78

    케이스B (정배열 돌파):
      현재가 > MA20 > MA60
      AND 현재가 >= 최근20일고가 × 0.87
      AND 45 <= RSI <= 78
    """
    price  = item.get("현재가")
    ma20   = item.get("MA20")
    ma60   = item.get("MA60")
    ma120  = item.get("MA120")
    rsi    = item.get("RSI_14")
    high20 = item.get("최근20일고가")

    if not all([price, ma20, ma60, ma120, rsi]):
        return "❌ 미충족", "케이스없음"

    # 케이스A: 정배열 눌림
    case_a = (
        price > ma60 and
        price > ma120 and
        price <= ma20 and
        40 <= rsi <= 78
    )
    if case_a:
        return "✅ 충족", "케이스A(정배열눌림)"

    # 케이스B: 정배열 돌파
    if high20:
        case_b = (
            price > ma20 and ma20 > ma60 and
            price >= high20 * 0.87 and
            45 <= rsi <= 78
        )
        if case_b:
            return "✅ 충족", "케이스B(정배열돌파)"

    return "❌ 미충족", "케이스없음"


def _factor2(records):
    """
    Factor 2 수급 판단 v3.0 (2026-04-16 변경)

    [탈락 조건 — 강제 ❌, 먼저 체크]
    탈락1: 외인 최근 2일 연속 순매도
    탈락2: 기관 최근 5일 순매도 >= 3일
    탈락3: 최근 5일 기관+외인 동시 순매수 0일

    [충족 조건 — 3개 AND]
    조건1: 기관 20일 누적 순매수 > 0 AND 20일 중 순매수 >= 10일
    조건2: 외인 최근 5일 중 순매수 >= 3일
    조건3: 최근 5일 기관+외인 동시 순매수 >= 2일

    탈락 없음 AND (조건1 AND 조건2 AND 조건3) → ✅ 충족
    """
    if not records or len(records) < 20:
        return "❌ 미충족"

    recent2  = records[0:2]
    recent5  = records[0:5]
    recent20 = records[0:20]

    # ── 탈락 조건 ────────────────────────────────────────────────
    # 탈락1: 외인 최근 2일 연속 순매도
    elim1 = all(r.get("외국인_순매수_수량", 0) <= 0 for r in recent2)

    # 탈락2: 기관 최근 5일 순매도 >= 3일
    inst_sell5 = sum(1 for r in recent5 if r.get("기관_순매수_수량", 0) <= 0)
    elim2 = inst_sell5 >= 3

    # 탈락3: 최근 5일 기관+외인 동시 순매수 0일
    both5 = sum(
        1 for r in recent5
        if r.get("외국인_순매수_수량", 0) > 0 and r.get("기관_순매수_수량", 0) > 0
    )
    elim3 = both5 == 0

    if elim1 or elim2 or elim3:
        return "❌ 미충족"

    # ── 충족 조건 ────────────────────────────────────────────────
    # 조건1: 기관 20일 누적 > 0 AND 20일 중 순매수 >= 10일
    inst_cum20  = sum(r.get("기관_순매수_수량", 0) for r in recent20)
    inst_days20 = sum(1 for r in recent20 if r.get("기관_순매수_수량", 0) > 0)
    cond1 = inst_cum20 > 0 and inst_days20 >= 10

    # 조건2: 외인 최근 5일 중 순매수 >= 3일
    for_days5 = sum(1 for r in recent5 if r.get("외국인_순매수_수량", 0) > 0)
    cond2 = for_days5 >= 3

    # 조건3: 최근 5일 기관+외인 동시 순매수 >= 2일
    cond3 = both5 >= 2

    if cond1 and cond2 and cond3:
        return "✅ 충족"
    return "❌ 미충족"



def merge_stock_data():
    print("=" * 60)
    print("🔄 데이터 병합 시작")
    print("=" * 60)

    today = date.today().isoformat()

    # KIS API 데이터 로드
    try:
        with open('stock_data.json', 'r', encoding='utf-8') as f:
            kis_data = json.load(f)
        print(f"✅ KIS API 데이터 로드: {len(kis_data)}개 종목")
    except FileNotFoundError:
        print("❌ stock_data.json 파일이 없습니다.")
        print("   먼저 'python auto_update.py'를 실행하세요.")
        sys.exit(1)

    # 네이버 MA/RSI/ATR 데이터 로드
    try:
        with open('naver_ma_data.json', 'r', encoding='utf-8') as f:
            naver_data = json.load(f)
        print(f"✅ 네이버 MA 데이터 로드: {len(naver_data)}개 종목")
    except FileNotFoundError:
        print("❌ naver_ma_data.json 파일이 없습니다.")
        print("   먼저 'python naver_crawl.py'를 실행하세요.")
        sys.exit(1)

    # 네이버 투자자 매매동향 데이터 로드
    try:
        with open('naver_investor_data.json', 'r', encoding='utf-8') as f:
            investor_data = json.load(f)
        print(f"✅ 네이버 투자자 데이터 로드: {len(investor_data)}개 종목")
    except FileNotFoundError:
        print("⚠️  naver_investor_data.json 없음 — 투자자 데이터 생략")
        print("   추가하려면 'python naver_investor_crawl.py'를 먼저 실행하세요.")
        investor_data = []

    # 데이터 병합
    print("\n" + "=" * 60)
    print("🔗 데이터 병합 중...")

    naver_dict    = {item['종목코드']: item for item in naver_data}
    investor_dict = {item['종목코드']: item for item in investor_data}

    merged_data = []
    success_count = 0

    for kis_item in kis_data:
        ticker = kis_item['종목코드']

        # ── 기술 지표 ─────────────────────────────────────────────────
        naver_item = naver_dict.get(ticker, {})
        rsi   = kis_item.get('RSI_14') or naver_item.get('RSI_14')
        ma60  = naver_item.get('MA60')
        ma120 = naver_item.get('MA120')

        if ma60 is not None or ma120 is not None:
            success_count += 1

        tech = {
            "종목코드":   ticker,
            "종목명":     kis_item['종목명'],
            "분석일":     today,
            "현재가":     kis_item.get('현재가'),
            "거래량":     kis_item.get('거래량'),
            "전일거래량": kis_item.get('전일거래량'),
            "RSI_14":     rsi,
            "MA5":        kis_item.get('MA5'),
            "MA20":       kis_item.get('MA20'),
            "MA60":       ma60,
            "MA120":      ma120,
            "ATR_14":     naver_item.get('ATR_14'),
            "최근20일고가": naver_item.get('최근20일고가'),
        }

        f1_result, f1_case = _factor1(tech)
        tech['Factor1_기술'] = f1_result
        tech['케이스']       = f1_case

        # ── 수급 ──────────────────────────────────────────────────────
        if ticker in investor_dict:
            records = investor_dict[ticker].get('투자자_매매동향', [])
            supply = {
                "개인_5일_순매수":        _sum_net(records, '개인_순매수_수량', 5),
                "개인_5일_순매수_금액":   _sum_net(records, '개인_순매수_금액', 5),
                "외국인_5일_순매수":      _sum_net(records, '외국인_순매수_수량', 5),
                "외국인_5일_순매수_금액": _sum_net(records, '외국인_순매수_금액', 5),
                "기관_5일_누적":          _sum_net(records, '기관_순매수_수량', 5),
                "기관_5일_누적_금액":     _sum_net(records, '기관_순매수_금액', 5),
                "Factor2_수급":           _factor2(records),
            }
        else:
            records = []
            supply = {
                "개인_5일_순매수":        None,
                "개인_5일_순매수_금액":   None,
                "외국인_5일_순매수":      None,
                "외국인_5일_순매수_금액": None,
                "기관_5일_누적":          None,
                "기관_5일_누적_금액":     None,
                "Factor2_수급":           "❌ 미충족",
            }

        # ── 최종 항목 조립 (필드 순서 고정) ──────────────────────────
        merged_item = {
            **tech,
            **supply,
            # F3/F4: Claude 웹검색으로 채울 placeholder
            "Factor3_실적":           None,
            "Factor4_밸류":           None,
            "컨센서스":               None,
            "최근분기_영업이익_YoY":  None,
            "업종_평균_PER":          None,
            "분석상태":               "🔍 분석중",
            # Raw 데이터
            "투자자_매매동향":        records,
        }

        merged_data.append(merged_item)

    # ── F1/F2 카테고리 분류 ───────────────────────────────────────
    def _is_pass(item, key):
        return item.get(key) == "✅ 충족"

    cat_both    = [i['종목명'] for i in merged_data if     _is_pass(i,'Factor1_기술') and     _is_pass(i,'Factor2_수급')]
    cat_f1_only = [i['종목명'] for i in merged_data if     _is_pass(i,'Factor1_기술') and not _is_pass(i,'Factor2_수급')]
    cat_f2_only = [i['종목명'] for i in merged_data if not _is_pass(i,'Factor1_기술') and     _is_pass(i,'Factor2_수급')]
    cat_neither = [i['종목명'] for i in merged_data if not _is_pass(i,'Factor1_기술') and not _is_pass(i,'Factor2_수급')]

    # ── 집계 요약 ─────────────────────────────────────────────────
    summary = {
        "분석일":       today,
        "전체_종목수":  len(merged_data),
        "F1F2_모두충족": {"개수": len(cat_both),    "종목": cat_both},
        "F1만_충족":    {"개수": len(cat_f1_only), "종목": cat_f1_only},
        "F2만_충족":    {"개수": len(cat_f2_only), "종목": cat_f2_only},
        "둘다_미충족":  {"개수": len(cat_neither), "종목": cat_neither},
    }

    # 병합 결과 저장
    with open('stock_data_full.json', 'w', encoding='utf-8') as f:
        json.dump({"집계": summary, "종목": merged_data}, f, indent=2, ensure_ascii=False)

    # 검증 결과 출력
    null_stocks = [
        f"{item['종목명']}({item['종목코드']})"
        for item in merged_data
        if item.get('MA60') is None or item.get('MA120') is None
    ]

    print("=" * 60)
    print(f"✅ 병합 완료: {len(merged_data)}개 종목 (분석일: {today})")
    if null_stocks:
        print(f"⚠️  MA60/MA120 누락 종목 ({len(null_stocks)}개):")
        for s in null_stocks:
            print(f"   - {s}")
    else:
        print("✅ 모든 종목 MA60/MA120 정상 수집")
    print(f"💾 저장 완료: stock_data_full.json")
    print("=" * 60)
    print(f"\n📊 Factor 집계:")
    print(f"  F1+F2 모두 충족: {len(cat_both)}개  {cat_both}")
    print(f"  F1만  충족:      {len(cat_f1_only)}개  {cat_f1_only}")
    print(f"  F2만  충족:      {len(cat_f2_only)}개  {cat_f2_only}")
    print(f"  둘 다 미충족:    {len(cat_neither)}개")
    print(f"\n✅ 이제 'stock_data_full.json'을 Claude에 업로드하세요!")


if __name__ == "__main__":
    merge_stock_data()
