@echo off
cd /d "%~dp0"

echo [1/4] auto_update...
python auto_update.py

echo [2/4] naver MA...
python naver_crawl.py

echo [3/4] naver investor...
python naver_investor_crawl.py

echo [4/4] merge...
python merge_data.py

echo Done.

echo [5/5] stock_data_full.json git push...
git add stock_data_full.json
git diff --cached --quiet && (echo [skip] no changes to commit) || (git commit -m "data: %DATE% F1/F2 업데이트" && git push origin main && echo [ok] pushed)

pause
