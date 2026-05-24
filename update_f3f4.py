"""
F3/F4 분석 결과를 stock_data_full.json에 병합하는 헬퍼 스크립트.
Claude 에이전트가 웹검색 분석 후 f3f4_results.json을 생성하면 이 스크립트가 병합한다.

Usage:
  python update_f3f4.py --input f3f4_results.json
"""

import argparse
import json
import sys
from pathlib import Path

FULL_JSON = Path(__file__).parent / "stock_data_full.json"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[update_f3f4] {path.name} 저장 완료")


F3_FIELDS = [
    "Factor3_실적",
    "F3_근거",
    "특수사유",
    "F4_대상",
    "메모",
    "분석상태",
    "컨센서스",
    "어닝서프라이즈_실적값",
    "어닝서프라이즈_비율",
    "최근분기_영업이익_YoY",
    "목표가_평균",
    "목표가_상향건수_3개월",
    "최근3년_매출_연속증가",
]

F4_FIELDS = [
    "Factor4_밸류",
    "Forward_PER",
    "업종_평균_PER",
    "PER_ratio",
    "업종명",
]


def merge_results(full: dict, results: list[dict]) -> dict:
    result_by_code = {r["종목코드"]: r for r in results}

    f3_ok = []
    f4_ok = []

    for stock in full["종목"]:
        code = stock["종목코드"]
        if code not in result_by_code:
            continue
        r = result_by_code[code]

        for field in F3_FIELDS + F4_FIELDS:
            if field in r:
                stock[field] = r[field]

        if stock.get("Factor3_실적") == "✅ 충족":
            f3_ok.append(stock["종목명"])
        if stock.get("Factor4_밸류") in ("✅ 충족", "유지"):
            f4_ok.append(stock["종목명"])

    full["집계"]["F3_충족"] = {"개수": len(f3_ok), "종목": f3_ok}
    full["집계"]["F4_충족"] = {"개수": len(f4_ok), "종목": f4_ok}

    return full


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="f3f4_results.json 경로")
    args = parser.parse_args()

    results_path = Path(args.input)
    if not results_path.exists():
        print(f"[오류] 파일 없음: {results_path}", file=sys.stderr)
        sys.exit(1)

    results_data = load_json(results_path)
    results = results_data.get("results", [])
    if not results:
        print("[오류] results 배열이 비어 있음", file=sys.stderr)
        sys.exit(1)

    full = load_json(FULL_JSON)
    full = merge_results(full, results)
    save_json(FULL_JSON, full)

    f3_count = full["집계"].get("F3_충족", {}).get("개수", 0)
    f4_count = full["집계"].get("F4_충족", {}).get("개수", 0)
    print(f"[update_f3f4] F3 충족 {f3_count}개 / F4 충족(유지 포함) {f4_count}개")


if __name__ == "__main__":
    main()
