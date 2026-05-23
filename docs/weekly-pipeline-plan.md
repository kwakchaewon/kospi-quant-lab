# 주간 주식 분석 파이프라인 자동화 — Claude Co-worker 등록 가이드

## Context

매주 일요일 21시(9PM KST)에 아래 3단계를 자동으로 실행한다:
1. `run_final.bat` → F1/F2 데이터 수집 (stock_data_full.json 생성)
2. Claude OPUS가 F3/F4 웹검색 분석 → stock_data_full.json 업데이트
3. 주간 보고서 생성 + 커밋

**핵심 제약**: `auto_update.py`는 로컬 `appkey.txt` (KIS API 키)가 필요하므로,
`run_final.bat`은 로컬 Windows 작업 스케줄러로 실행해야 한다.
Claude Co-worker `/schedule` 루틴은 F3/F4 분석 + 보고서 생성을 담당한다.

---

## 파이프라인 아키텍처

```
[8:45 PM KST 일요일]           [9:00 PM KST 일요일]
Windows 작업 스케줄러           Claude Co-worker (/schedule)
        │                               │
  run_final.bat                 weekly-stock-analysis 루틴
  (4 Python 스크립트)                   │
        │                     ┌─────────┼──────────┐
  stock_data_full.json   F3/F4 분석   보고서 생성  auto-commit
  (F1/F2 채워진 상태)    (웹검색)    reports/*.md  git push
```

---

## 생성 파일 목록

| 파일 | 목적 | 상태 |
|---|---|---|
| `update_f3f4.py` | F3/F4 결과를 JSON에 병합하는 헬퍼 | ✅ 완료 |
| `reports/.gitkeep` | reports/ 디렉토리 git 추적용 | ✅ 완료 |
| `.claude/agents/weekly-stock-analysis.md` | Co-worker 루틴 에이전트 프롬프트 | ✅ 완료 |

---

## Step 1: Windows 작업 스케줄러 등록

PowerShell **관리자 권한**으로 실행:

```powershell
$action = New-ScheduledTaskAction `
  -Execute 'C:\Users\eden240213\Desktop\stock_update\run_final.bat'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '08:45PM'
Register-ScheduledTask -TaskName 'StockUpdateF1F2' `
  -Action $action -Trigger $trigger -RunLevel Highest
```

확인:
```powershell
Get-ScheduledTask -TaskName 'StockUpdateF1F2' | Select-Object TaskName, State
```

---

## Step 2: Claude Co-worker 루틴 등록

Claude Code CLI에서 stock_update 프로젝트 열린 상태에서:

```
/schedule
```

입력값:
- **이름**: `weekly-stock-analysis`
- **프롬프트**: `Read the file .claude/agents/weekly-stock-analysis.md and follow all instructions exactly.`
- **스케줄(cron)**: `0 12 * * 0`  ← 일요일 12:00 UTC = 21:00 KST
- **모델**: claude-opus-4-7
- **반복**: 매주

등록 완료 시 `trigger_id`와 결과 확인 URL(claude.ai)을 저장해 둔다.

---

## Step 3: 에이전트 프롬프트 파일

**파일**: `.claude/agents/weekly-stock-analysis.md`

에이전트가 매주 일요일 9PM KST에 실행하는 지시사항:
- STEP A: stock_data_full.json 전제조건 확인 (분석일 = 오늘)
- STEP B: F3 실적 분석 — F1/F2 충족 종목 대상 웹검색 3회
- STEP C: F4 밸류 분석 — F3 충족 종목 대상 웹검색 2회
- STEP D: `python update_f3f4.py --input f3f4_results.json` 으로 JSON 업데이트
- STEP E: `reports/weekly_YYYY-MM-DD.md` 보고서 생성
- STEP F: git add → commit → push (appkey.txt, *.json 미포함 확인)

---

## Step 4: .claude/settings.json 권한 추가

아래 항목을 `permissions.allow` 배열에 추가:

```json
"Bash(python update_f3f4.py *)",
"Bash(python auto_update.py)",
"Bash(python naver_crawl.py)",
"Bash(python naver_investor_crawl.py)",
"Bash(python merge_data.py)",
"Bash(git push *)"
```

---

## 검증 방법

| 단계 | 명령 | 확인 사항 |
|---|---|---|
| 배치 단독 | `run_final.bat` 수동 실행 | stock_data_full.json 분석일 = 오늘 |
| update 스크립트 | `python update_f3f4.py --input test.json` | F3/F4 필드 반영 |
| 보고서 | reports/weekly_YYYY-MM-DD.md 열기 | 섹션 구조 확인 |
| 커밋 확인 | `git log --oneline -3` | appkey.txt / *.json 미포함 |
| Co-worker 즉시 | RemoteTrigger run <trigger_id> | 전체 파이프라인 end-to-end |

---

## 타임라인 요약

```
20:45 KST  Windows Task Scheduler → run_final.bat 실행 (약 5~10분 소요)
21:00 KST  Claude Co-worker 루틴 시작
           → F3/F4 웹검색 분석 (종목당 최대 5회, 약 30~60분)
           → stock_data_full.json 업데이트
           → reports/weekly_YYYY-MM-DD.md 생성
           → git commit & push
```
