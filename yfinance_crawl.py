"""
yfinance 데이터 수집 스크립트
어닝서프라이즈, 영업이익 YoY(연간), 다음 실적발표일, 목표가, ForwardPE, 업종
→ yfinance_data.json
"""
import json
import sys
import time

import yfinance as yf

_OPERATING_INCOME_LABELS = [
    "Operating Income",
    "Total Operating Income As Reported",
    "EBIT",
    "Normalized EBITDA",
]


def _safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fetch_info_with_retry(ticker_obj, max_retries=3):
    for attempt in range(max_retries):
        try:
            info = ticker_obj.info
            if info and len(info) > 5:
                return info
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return {}


def _parse_earnings_surprise(ticker_obj):
    try:
        df = ticker_obj.earnings_history
        if df is None or df.empty:
            return None
        df = df.sort_index(ascending=False)
        row = df.iloc[0]
        for col in ["Surprise(%)", "surprisePercent"]:
            val = row.get(col)
            if val is not None:
                return _safe_float(val)
        return None
    except Exception:
        return None


def _parse_next_earnings_date(ticker_obj):
    try:
        import pandas as pd
        df = ticker_obj.earnings_dates
        if df is None or df.empty:
            return None
        now = pd.Timestamp.now(tz="UTC")
        future = df[df.index > now]
        if future.empty:
            return None
        return str(future.index.min())[:10]
    except Exception:
        return None


def _parse_annual_operating_income(ticker_obj):
    """연간 손익계산서에서 최근 2개 연도 영업이익 추출"""
    try:
        df = ticker_obj.income_stmt
        if df is None or df.empty:
            return None, None, None, None, None
        df = df.sort_index(axis=1, ascending=False)
        if df.shape[1] < 2:
            return None, None, None, None, None

        row = None
        label_used = None
        for label in _OPERATING_INCOME_LABELS:
            if label in df.index:
                row = df.loc[label]
                label_used = label
                break

        if row is None:
            return None, None, None, None, None

        recent_val    = _safe_float(row.iloc[0])
        prior_val     = _safe_float(row.iloc[1])
        recent_period = str(df.columns[0])[:10]
        prior_period  = str(df.columns[1])[:10]
        return recent_val, prior_val, recent_period, prior_period, label_used
    except Exception:
        return None, None, None, None, None


def _parse_price_targets(ticker_obj):
    try:
        pt = ticker_obj.analyst_price_targets
        if pt is None:
            return {}
        if hasattr(pt, "to_dict"):
            pt = pt.to_dict()
        return {
            "current": _safe_float(pt.get("current")),
            "high":    _safe_float(pt.get("high")),
            "low":     _safe_float(pt.get("low")),
            "mean":    _safe_float(pt.get("mean")),
            "median":  _safe_float(pt.get("median")),
        }
    except Exception:
        return {}


def _empty_record(ticker_code, stock_name):
    return {
        "종목코드": ticker_code,
        "종목명": stock_name,
        "yahoo_symbol": ticker_code + ".KS",
        "forwardPE": None,
        "sector": None,
        "industry": None,
        "earnings_surprise_latest": None,
        "next_earnings_date": None,
        "영업이익_최근연도": None,
        "영업이익_전년도": None,
        "영업이익_최근연도_period": None,
        "영업이익_전년도_period": None,
        "영업이익_label": None,
        "analyst_price_targets": {},
    }


def get_stock_data(ticker_code, stock_name):
    yahoo_sym = ticker_code + ".KS"
    t = yf.Ticker(yahoo_sym)

    info       = _fetch_info_with_retry(t)
    forward_pe = _safe_float(info.get("forwardPE"))
    sector     = info.get("sector")
    industry   = info.get("industry")

    surprise  = _parse_earnings_surprise(t)
    next_date = _parse_next_earnings_date(t)

    recent_oi, prior_oi, recent_period, prior_period, oi_label = \
        _parse_annual_operating_income(t)

    targets = _parse_price_targets(t)

    return {
        "종목코드": ticker_code,
        "종목명": stock_name,
        "yahoo_symbol": yahoo_sym,
        "forwardPE": forward_pe,
        "sector": sector,
        "industry": industry,
        "earnings_surprise_latest": surprise,
        "next_earnings_date": next_date,
        "영업이익_최근연도": int(recent_oi) if recent_oi is not None else None,
        "영업이익_전년도":   int(prior_oi)  if prior_oi  is not None else None,
        "영업이익_최근연도_period": recent_period,
        "영업이익_전년도_period":   prior_period,
        "영업이익_label": oi_label,
        "analyst_price_targets": targets,
    }


def main():
    print("=" * 60)
    print("📡 yfinance 데이터 수집 시작")
    print("=" * 60)

    try:
        with open("stock_list.json", "r", encoding="utf-8") as f:
            stock_list = json.load(f)
    except FileNotFoundError:
        print("❌ stock_list.json 파일이 없습니다.")
        sys.exit(1)

    print(f"대상: {len(stock_list)}개 종목\n")

    all_data = []
    success  = 0

    for i, stock in enumerate(stock_list, 1):
        code = stock["종목코드"]
        name = stock["종목명"]
        print(f"[{i:2d}/{len(stock_list)}] {code} {name}", end=" ... ")
        try:
            result = get_stock_data(code, name)
            has_data = (
                result["forwardPE"] is not None
                or result["earnings_surprise_latest"] is not None
                or result["영업이익_최근연도"] is not None
            )
            if has_data:
                success += 1
            print("✅" if has_data else "⚠️ 데이터없음")
        except Exception as e:
            print(f"❌ 오류: {e}")
            result = _empty_record(code, name)

        all_data.append(result)

        if i < len(stock_list):
            time.sleep(2.0)

    with open("yfinance_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"✅ 수집 완료: {len(all_data)}개 종목 (유효 데이터: {success}개)")
    print("💾 저장 완료: yfinance_data.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
