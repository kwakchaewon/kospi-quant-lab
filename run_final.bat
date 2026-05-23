@echo off
cd /d "%~dp0"

echo [1/5] auto_update...
python auto_update.py

echo [2/5] naver MA...
python naver_crawl.py

echo [3/5] naver investor...
python naver_investor_crawl.py

echo [4/5] yfinance...
python yfinance_crawl.py

echo [5/5] merge...
python merge_data.py

echo Done.
pause
