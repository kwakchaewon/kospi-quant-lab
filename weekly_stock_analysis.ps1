Set-Location "C:\Users\eden240213\Desktop\stock_update"
$env:PYTHONIOENCODING = "utf-8"

# F1/F2 파이프라인
Write-Host "[1/2] run_final.bat 실행 중..."
cmd /c run_final.bat

# F3/F4 분석 + 커밋 + push (로컬 claude CLI)
Write-Host "[2/2] F3/F4 분석 시작..."
$prompt = Get-Content ".claude\agents\weekly-stock-analysis.md" -Raw
claude -p $prompt --model claude-opus-4-7 --dangerously-skip-permissions
