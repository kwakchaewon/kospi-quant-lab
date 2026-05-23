#!/usr/bin/env python3
"""
stock_data_full.json 커밋 시 이전 버전을 data-history/ 에 스냅샷으로 저장.
pre-commit 훅에서 호출됩니다.
"""
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
HISTORY_DIR = ROOT / "docs" / "data-history"


def get_head_content() -> str | None:
    result = subprocess.run(
        ["git", "show", "HEAD:stock_data_full.json"],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
    )
    return result.stdout if result.returncode == 0 else None


def main() -> int:
    old_content = get_head_content()
    if not old_content:
        print("[archive_data] HEAD 없음 — 첫 커밋이므로 아카이빙 건너뜀.")
        return 0

    today = date.today().isoformat()
    snapshot = HISTORY_DIR / f"stock_data_{today}.json"

    if snapshot.exists():
        for i in range(2, 100):
            candidate = HISTORY_DIR / f"stock_data_{today}_{i}.json"
            if not candidate.exists():
                snapshot = candidate
                break

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(old_content, encoding="utf-8")
    subprocess.run(["git", "add", str(HISTORY_DIR)], cwd=ROOT)
    print(f"[archive_data] 스냅샷 저장 → {snapshot.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
