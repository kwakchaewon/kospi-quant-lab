#!/usr/bin/env python3
"""
docs/factors.md 커밋 시 이전 버전의 Factor 섹션을 factor-history/ 에 아카이빙.
pre-commit 훅에서 호출됩니다.
"""
import subprocess
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
HISTORY_DIR = ROOT / "docs" / "factor-history"

FACTOR_PATTERNS = {
    1: r"(## Factor 1.*?)(?=\n## Factor \d|\Z)",
    2: r"(## Factor 2.*?)(?=\n## Factor \d|\Z)",
}


def get_head_content() -> str | None:
    result = subprocess.run(
        ["git", "show", "HEAD:docs/factors.md"],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
    )
    return result.stdout if result.returncode == 0 else None


def extract_section(content: str, factor_num: int) -> str | None:
    match = re.search(FACTOR_PATTERNS[factor_num], content, re.DOTALL)
    return match.group(1).strip() if match else None


def prepend_entry(history_file: Path, section: str, today: str) -> None:
    existing = history_file.read_text(encoding="utf-8")
    # 헤더(첫 두 줄)와 본문 분리 후 새 항목 삽입
    lines = existing.split("\n")
    header_end = next(
        (i for i, l in enumerate(lines) if l.strip() == "---"), len(lines)
    )
    header = "\n".join(lines[: header_end + 1])
    body = "\n".join(lines[header_end + 1 :]).lstrip("\n")

    new_entry = f"\n<!-- archived {today} -->\n\n{section}\n\n---\n"
    history_file.write_text(header + new_entry + ("\n" + body if body else ""), encoding="utf-8")


def main() -> int:
    old_content = get_head_content()
    if not old_content:
        print("[archive_factors] HEAD 없음 — 첫 커밋이므로 아카이빙 건너뜀.")
        return 0

    today = date.today().isoformat()
    archived = 0

    for num, history_name in [(1, "factor1.md"), (2, "factor2.md")]:
        section = extract_section(old_content, num)
        if not section:
            continue
        history_file = HISTORY_DIR / history_name
        if not history_file.exists():
            print(f"[archive_factors] {history_file} 없음 — 건너뜀.", file=sys.stderr)
            continue
        prepend_entry(history_file, section, today)
        print(f"[archive_factors] Factor {num} 아카이빙 → {history_file.relative_to(ROOT)}")
        archived += 1

    if archived:
        subprocess.run(["git", "add", str(HISTORY_DIR)], cwd=ROOT)

    return 0


if __name__ == "__main__":
    sys.exit(main())
