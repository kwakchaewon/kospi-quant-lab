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
pause
