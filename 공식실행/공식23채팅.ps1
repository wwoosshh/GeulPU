param([string]$저장소, [string]$출력폴더)
# 23단계 기록 — 파이썬 없는 PATH 에서 글 실행기로 7B Q4_0 채팅(18a 와 같은 꼴). 실행기가 GGUF 의 형식을 보고 옆의 qwen2Q4_7b.ptx 를 고른다.
$ErrorActionPreference = "Stop"
$기록 = Join-Path $출력폴더 "23_채팅기록_Q4.txt"
$env:PATH = "C:\Windows\System32;C:\Windows"
$py = $null; $py2 = $null
try { $py = (Get-Command python -ErrorAction Stop).Source } catch {}
try { $py2 = (Get-Command py -ErrorAction Stop).Source } catch {}
"시작 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -Encoding utf8 $기록
"PATH = $env:PATH · python 찾음: $($py -ne $null) · py 찾음: $($py2 -ne $null)" | Out-File -Encoding utf8 -Append $기록
$실행기 = Join-Path $저장소 "빌드\글\실행기.exe"
$모델 = Join-Path $저장소 "모델\qwen2.5-7b-instruct-gguf\qwen2.5-7b-instruct-q4_0-pure.gguf"
$입력 = Join-Path $저장소 "문서\결과\18단계\18a_채팅입력.txt"
$출력 = Join-Path $출력폴더 "23_채팅출력_Q4.txt"
$p = Start-Process -FilePath $실행기 -ArgumentList "`"$모델`"" -RedirectStandardInput $입력 -RedirectStandardOutput $출력 -NoNewWindow -PassThru -Wait
"채팅 종료 코드 $($p.ExitCode)" | Out-File -Encoding utf8 -Append $기록
"끝 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -Encoding utf8 -Append $기록
foreach ($f in @($실행기, (Join-Path $저장소 "빌드\글\qwen2Q4_7b.ptx"), (Join-Path $저장소 "빌드\글\qwen2Q8.ptx"))) {
    $h = (Get-FileHash -Algorithm SHA256 $f).Hash.ToLower()
    "$h  $((Get-Item $f).Length)  $(Split-Path $f -Leaf)" | Out-File -Encoding utf8 -Append $기록
}
