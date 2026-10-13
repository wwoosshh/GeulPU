# GeulPU 교차 검증 — 다른 PC 에서도 같은 출력이 나오는가
#   모델: DeepSeek-R1-Distill-Qwen-7B Q8_0 · 수학 문제 32 개 · 탐욕 생성(temperature 0) · 답 길이 상한 3200 토큰
#   실행: run.bat 을 더블클릭한다. 환경을 검사하고, 모델이 없으면 Hugging Face 에서 받고(8.1 GB), 생성한 뒤,
#         기준 PC 의 출력과 견주고, 결과를 result-…zip 으로 묶는다. 그 zip 을 보내 주면 된다.
param([switch]$CompareOnly, [string]$ResponsesDir = '')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Here
[Environment]::SetEnvironmentVariable('CUDA_DEVICE_ORDER', 'PCI_BUS_ID', 'Process')   # CUDA 장치 0 = nvidia-smi 의 GPU 0

$PackageVersion = 'crosscheck-r1-v1'
$ModelName = 'DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf'
$ModelUrl  = 'https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf'
$ModelSize = 8098524896
$ModelSha  = '7307BFBB539FD2E8ED636315440781FED23140DC7F911F64B33418F5B978281B'
$Port      = 18091
$Context   = 3584
$MaxTokens = 3200

function Say([string]$m) { Write-Host ('[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Fail([string]$m) {
    Write-Host ''
    Write-Host ('중단: ' + $m) -ForegroundColor Red
    exit 1
}
function Sha256Hex([byte[]]$b) {
    $h = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($h.ComputeHash($b)) -replace '-', '').ToLower() } finally { $h.Dispose() }
}
function ReadJson([string]$path) { return ([IO.File]::ReadAllText($path, [Text.Encoding]::UTF8) | ConvertFrom-Json) }
function ToInt($s) { $r = 0; if ([int]::TryParse(([string]$s).Trim(), [ref]$r)) { return $r }; return 0 }
function Native([string[]]$a) {
    # nvidia-smi 같은 바깥 명령 — 실패해도 멈추지 않는다
    $ErrorActionPreference = 'Continue'
    try {
        if ($a.Count -gt 1) { $o = & $a[0] $a[1..($a.Count - 1)] 2>$null } else { $o = & $a[0] 2>$null }
        if ($LASTEXITCODE -ne 0) { return @() }
        return @($o | ForEach-Object { ([string]$_).Trim() })
    } catch { return @() }
}

$Checks = New-Object System.Collections.ArrayList
function Check([string]$name, [string]$state, [string]$detail) {
    [void]$Checks.Add([ordered]@{ name = $name; state = $state; detail = $detail })
    $color = 'Gray'
    if ($state -eq '통과') { $color = 'Green' } elseif ($state -eq '경고') { $color = 'Yellow' } elseif ($state -eq '실패') { $color = 'Red' }
    Write-Host ('  [{0}] {1}: {2}' -f $state, $name, $detail) -ForegroundColor $color
}

Write-Host '=== GeulPU 교차 검증 (R1 · 32 문제) ==='
Write-Host '환경을 검사하고, 모델이 없으면 8.1 GB 를 받습니다. 생성은 GPU 에 따라 5~15 분입니다. 창을 닫지 마세요.'
Write-Host ''

# 압축을 푼 파일의 '인터넷에서 받음' 표시를 지운다(실행이 막히지 않게)
Get-ChildItem -LiteralPath $Here -Recurse -File | ForEach-Object { try { Unblock-File -LiteralPath $_.FullName } catch { } }

# ================= 1. 환경 검사 =================
Write-Host '--- 환경 검사 ---'
$EnvInfo = [ordered]@{ package = $PackageVersion; checked_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') }

# 운영체제
$os = Get-CimInstance Win32_OperatingSystem
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction SilentlyContinue
$disp = ''; $ubr = ''
if ($cv) { $disp = [string]$cv.DisplayVersion; $ubr = [string]$cv.UBR }
$EnvInfo.os = [ordered]@{ caption = [string]$os.Caption; display_version = $disp; build = ([string]$os.BuildNumber + '.' + $ubr)
                          architecture = [string]$os.OSArchitecture; locale = (Get-Culture).Name }
if ([string]$os.OSArchitecture -match '64') { Check '운영체제' '통과' ('{0} {1} (빌드 {2})' -f $os.Caption, $disp, $EnvInfo.os.build) }
else { Check '운영체제' '실패' '64 비트 윈도가 필요합니다' }

# PowerShell · .NET
$netRel = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue).Release
$EnvInfo.powershell = $PSVersionTable.PSVersion.ToString()
$EnvInfo.dotnet_release = $netRel
Check 'PowerShell · .NET' '정보' ('PowerShell {0} · .NET 4 릴리스 {1}' -f $EnvInfo.powershell, $netRel)

# CPU · 메모리
$cpuObj = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem
$EnvInfo.cpu = [ordered]@{ name = ([string]$cpuObj.Name).Trim(); cores = [int]$cpuObj.NumberOfCores; threads = [int]$cpuObj.NumberOfLogicalProcessors
                           max_mhz = [int]$cpuObj.MaxClockSpeed }
$EnvInfo.ram_gb = [Math]::Round([double]$cs.TotalPhysicalMemory / 1GB, 1)
Check 'CPU · 메모리' '정보' ('{0} · {1}코어 {2}스레드 · RAM {3} GB' -f $EnvInfo.cpu.name, $EnvInfo.cpu.cores, $EnvInfo.cpu.threads, $EnvInfo.ram_gb)

# CUDA 드라이버
$nvcuda = Join-Path $env:SystemRoot 'System32\nvcuda.dll'
$EnvInfo.nvcuda_dll = $null
if (Test-Path -LiteralPath $nvcuda) {
    $EnvInfo.nvcuda_dll = (Get-Item -LiteralPath $nvcuda).VersionInfo.FileVersion
    Check 'CUDA 드라이버 (nvcuda.dll)' '통과' $EnvInfo.nvcuda_dll
}
else { Check 'CUDA 드라이버 (nvcuda.dll)' '실패' 'NVIDIA 그래픽 드라이버가 필요합니다' }

# GPU (모두)
$gpu = 'unknown'; $driver = ''; $vram = 0; $cap = ''
$slotsList = @(8, 2, 1)
$gpus = @()
$smiCmd = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smiCmd) {
    $head = (Native @('nvidia-smi')) -join "`n"
    $EnvInfo.cuda_driver_version = ''
    if ($head -match 'CUDA (?:UMD )?Version:\s*([0-9.]+)') { $EnvInfo.cuda_driver_version = $Matches[1] }   # 새 드라이버는 'CUDA UMD Version'
    $fields = @('index', 'name', 'pci.bus_id', 'driver_version', 'driver_model.current', 'vbios_version', 'compute_cap', 'memory.total',
                'memory.used', 'pcie.link.gen.max', 'pcie.link.width.max', 'clocks.max.sm', 'clocks.max.memory', 'power.limit', 'temperature.gpu')
    $cols = @{}
    foreach ($f in $fields) { $cols[$f] = @(Native @('nvidia-smi', ('--query-gpu=' + $f), '--format=csv,noheader,nounits')) }
    $n = @($cols['index']).Count
    for ($i = 0; $i -lt $n; $i++) {
        $g = [ordered]@{}
        foreach ($f in $fields) {
            $v = @($cols[$f])
            if ($i -lt $v.Count) { $g[$f] = $v[$i] } else { $g[$f] = $null }
        }
        $gpus += New-Object psobject -Property $g
    }
}
$EnvInfo.gpus = $gpus
if ($gpus.Count -eq 0) { Check 'GPU' '실패' 'NVIDIA GPU 를 찾지 못했습니다 (nvidia-smi)' }
else {
    foreach ($g in $gpus) {
        Check ('GPU ' + $g.index) '정보' ('{0} · VRAM {1} MiB · compute {2} · 드라이버 {3} ({4}) · VBIOS {5} · PCIe {6}x{7} · 최대 SM {8} MHz / 메모리 {9} MHz · 전력 한도 {10} W' -f `
            $g.name, $g.'memory.total', $g.compute_cap, $g.driver_version, $g.'driver_model.current', $g.vbios_version,
            $g.'pcie.link.gen.max', $g.'pcie.link.width.max', $g.'clocks.max.sm', $g.'clocks.max.memory', $g.'power.limit')
    }
    Check 'CUDA 판' '정보' ('드라이버가 받는 CUDA ' + $EnvInfo.cuda_driver_version)
    $g0 = $gpus[0]
    $gpu = [string]$g0.name; $driver = [string]$g0.driver_version; $vram = ToInt $g0.'memory.total'; $cap = [string]$g0.compute_cap
    if ($cap -match '^\d+\.\d+$') {
        if ([double]$cap -ge 8.0) { Check '연산 능력' '통과' ('compute {0} (8.0 이상 필요)' -f $cap) }
        else { Check '연산 능력' '실패' ('compute {0} — RTX 30 시리즈 이상이 필요합니다' -f $cap) }
    }
    else { Check '연산 능력' '경고' '확인하지 못했습니다 (드라이버가 오래되었을 수 있음)' }
    if ($vram -ge 11500) { Check 'VRAM' '통과' ('{0} MiB — 슬롯 8' -f $vram); $slotsList = @(8, 2, 1) }
    elseif ($vram -ge 9800) { Check 'VRAM' '경고' ('{0} MiB — 슬롯 2 로 줄여 실행 (느림)' -f $vram); $slotsList = @(2, 1) }
    else { Check 'VRAM' '실패' ('{0} MiB — 모델(8.1 GB)이 들어가지 않습니다. 12 GB 이상이 필요합니다' -f $vram) }
    $used = ToInt $g0.'memory.used'
    if ($used -gt 1500) { Check 'VRAM 사용 중' '경고' ('{0} MiB 를 다른 프로그램이 쓰고 있습니다. 게임·브라우저를 닫으면 안전합니다' -f $used) }
    else { Check 'VRAM 사용 중' '통과' ('{0} MiB' -f $used) }
    if ($gpus.Count -gt 1) { Check '여러 GPU' '정보' 'GPU 0 (PCI 순서 첫째)을 씁니다' }
}

# 그래픽 일정 · 전원
$hags = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers' -Name HwSchMode -ErrorAction SilentlyContinue).HwSchMode
$EnvInfo.hardware_gpu_scheduling = 'default'
if ($hags -eq 2) { $EnvInfo.hardware_gpu_scheduling = 'on' } elseif ($hags -eq 1) { $EnvInfo.hardware_gpu_scheduling = 'off' }
$plan = ''
$pc = (Native @('powercfg', '/getactivescheme')) -join ' '
if ($pc -match '\(([^)]+)\)') { $plan = $Matches[1] }
$EnvInfo.power_plan = $plan
Check '그래픽 일정 · 전원' '정보' ('하드웨어 가속 GPU 일정 {0} · 전원 계획 {1}' -f $EnvInfo.hardware_gpu_scheduling, $plan)

# 디스크 · 모델
$ModelPath = Join-Path $Here $ModelName
$freeGB = [Math]::Round((Get-Item -LiteralPath $Here).PSDrive.Free / 1GB, 1)
$EnvInfo.disk_free_gb = $freeGB
$EnvInfo.model_present = (Test-Path -LiteralPath $ModelPath)
if ($EnvInfo.model_present) { Check '디스크 · 모델' '통과' ('여유 {0} GB · 모델 파일 있음' -f $freeGB) }
elseif ($CompareOnly -or $freeGB -ge 9) { Check '디스크 · 모델' '통과' ('여유 {0} GB · 모델을 받습니다 (8.1 GB)' -f $freeGB) }
else { Check '디스크 · 모델' '실패' ('여유 {0} GB — 9 GB 이상이 필요합니다' -f $freeGB) }

# 묶음 파일이 원본과 같은가
$sumFile = Join-Path $Here 'SHA256SUMS.txt'
if (Test-Path -LiteralPath $sumFile) {
    $bad = @()
    foreach ($ln in (Get-Content -LiteralPath $sumFile)) {
        if ($ln -match '^([0-9a-f]{64})\s+(.+)$') {
            $want = $Matches[1]; $fn = $Matches[2]
            $fp = Join-Path $Here $fn
            if (-not (Test-Path -LiteralPath $fp)) { $bad += $fn }
            elseif ((Get-FileHash -LiteralPath $fp -Algorithm SHA256).Hash.ToLower() -ne $want) { $bad += $fn }
        }
    }
    if ($bad.Count -eq 0) { Check '묶음 파일' '통과' 'SHA256SUMS.txt 와 모두 같음' }
    else { Check '묶음 파일' '실패' ('원본과 다른 파일: ' + ($bad -join ', ')) }
}
else { Check '묶음 파일' '경고' 'SHA256SUMS.txt 가 없습니다' }
$EnvInfo.checks = $Checks

# ---- 결과 폴더 ----
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$safeGpu = (($gpu -replace '[^A-Za-z0-9]+', '-').Trim('-'))
$Out = Join-Path $Here ('result-' + $safeGpu + '-' + $Stamp)
$RespOut = Join-Path $Out 'responses'
New-Item -ItemType Directory -Path $RespOut -Force | Out-Null
$EnvInfo | ConvertTo-Json -Depth 6 | Out-File -FilePath (Join-Path $Out 'environment.json') -Encoding UTF8
$failed = @($Checks | Where-Object { $_.state -eq '실패' }).Count
Write-Host ''
if ($failed -gt 0 -and -not $CompareOnly) {
    Compress-Archive -Path (Join-Path $Out '*') -DestinationPath ($Out + '.zip') -Force
    Fail ('환경 검사에서 실패 {0} 건 — 위 내용을 확인해 주세요. 환경 기록: {1}.zip' -f $failed, $Out)
}

$results = @{}
$slots = 0
$genMinutes = 0.0
$proc = $null

try {
    if ($CompareOnly) {
        # 시험용: 이미 받은 응답 파일(NN.json)로 비교만 한다
        Get-ChildItem -LiteralPath $ResponsesDir -Filter *.json | ForEach-Object {
            $id = [int]$_.BaseName
            $bytes = [IO.File]::ReadAllBytes($_.FullName)
            [IO.File]::WriteAllBytes((Join-Path $RespOut $_.Name), $bytes)
            $results[$id] = @{ status = 200; json = ([Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json) }
        }
    }
    else {
        # ================= 2. 모델 =================
        if (-not (Test-Path -LiteralPath $ModelPath)) {
            $part = $ModelPath + '.part'
            Say '모델을 받습니다 (8.1 GB, Hugging Face). 끊기면 다시 실행하면 이어서 받습니다.'
            $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
            if (Test-Path -LiteralPath $curl) {
                & $curl -L --fail --retry 5 --retry-delay 5 -C - -o $part $ModelUrl
                if ($LASTEXITCODE -ne 0) { Fail ('모델 받기에 실패했습니다 (curl 코드 {0}). 다시 실행해 주세요.' -f $LASTEXITCODE) }
            }
            else {
                Import-Module BitsTransfer
                Start-BitsTransfer -Source $ModelUrl -Destination $part
            }
            Move-Item -LiteralPath $part -Destination $ModelPath
        }
        $len = (Get-Item -LiteralPath $ModelPath).Length
        if ($len -ne $ModelSize) { Fail ('모델 파일 크기가 다릅니다 ({0} 바이트). 파일을 지우고 다시 실행해 주세요.' -f $len) }
        Say '모델 파일 확인 중 (SHA-256, 1~2 분)...'
        $fh = Get-FileHash -LiteralPath $ModelPath -Algorithm SHA256
        if ($fh.Hash -ne $ModelSha) { Fail ('모델 파일의 SHA-256 이 다릅니다: ' + $fh.Hash) }
        Say '모델 확인 완료.'

        # ================= 3. 서버 (127.0.0.1 에서만 열린다) =================
        $exe = Join-Path $Here 'server_r1.exe'
        $ptx = Join-Path $Here 'q8_7b.ptx'
        $ok = $false
        foreach ($s in $slotsList) {
            $argList = @(('"' + $ModelPath + '"'), '--ptx', ('"' + $ptx + '"'), '--슬롯', "$s", '--문맥', "$Context", '--포트', "$Port")
            Say ('서버를 띄웁니다 (슬롯 {0})...' -f $s)
            $proc = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $Out ('server-{0}.log' -f $s)) -RedirectStandardError (Join-Path $Out ('server-{0}-err.log' -f $s))
            $t0 = Get-Date
            while (((Get-Date) - $t0).TotalMinutes -lt 15) {
                if ($proc.HasExited) { break }
                try {
                    $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:{0}/health' -f $Port) -TimeoutSec 3
                    if ($r.StatusCode -eq 200) { $ok = $true; break }
                } catch { }
                Start-Sleep -Seconds 1
            }
            if ($ok) { $slots = $s; break }
            if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
            Say ('슬롯 {0} 로는 서버가 뜨지 않았습니다. 더 적은 슬롯으로 다시 시도합니다.' -f $s)
        }
        if (-not $ok) { Fail ('서버를 띄우지 못했습니다. ' + $Out + ' 폴더의 server-*.log 를 보내 주세요.') }
        Say ('서버 준비 완료 (슬롯 {0}).' -f $slots)

        # ================= 4. 32 문제를 한꺼번에 보낸다 (서버가 줄을 세워 슬롯만큼씩 처리) =================
        [System.Net.ServicePointManager]::DefaultConnectionLimit = 64
        [System.Net.ServicePointManager]::Expect100Continue = $false
        Add-Type -AssemblyName System.Net.Http
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.UseProxy = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.Timeout = [TimeSpan]::FromHours(8)
        $reqs = ReadJson (Join-Path $Here 'requests.json')
        $tasks = @{}
        foreach ($q in $reqs) {
            $body = @{ prompt = @($q.prompt_tokens); max_tokens = $MaxTokens; temperature = 0; cache_prompt = $false; geulpu = @{ logit_hash = $true } } |
                ConvertTo-Json -Compress -Depth 5
            $content = New-Object System.Net.Http.StringContent($body, [Text.Encoding]::UTF8, 'application/json')
            $tasks[[int]$q.id] = $client.PostAsync(('http://127.0.0.1:{0}/v1/completions' -f $Port), $content)
        }
        $tg = Get-Date
        while ($true) {
            $done = @($tasks.Values | Where-Object { $_.IsCompleted }).Count
            Say ('생성 중: {0}/{1} 완료 · {2:N1} 분 경과' -f $done, $tasks.Count, ((Get-Date) - $tg).TotalMinutes)
            if ($done -eq $tasks.Count) { break }
            if ($proc.HasExited) { Fail '생성 도중에 서버가 끝났습니다. server-*.log 를 보내 주세요.' }
            Start-Sleep -Seconds 30
        }
        $genMinutes = ((Get-Date) - $tg).TotalMinutes
        foreach ($id in ($tasks.Keys | Sort-Object)) {
            $t = $tasks[$id]
            if ($t.IsFaulted -or $t.IsCanceled) { $results[$id] = @{ status = 0; error = [string]$t.Exception }; continue }
            $resp = $t.Result
            $bytes = $resp.Content.ReadAsByteArrayAsync().Result
            [IO.File]::WriteAllBytes((Join-Path $RespOut ('{0:D2}.json' -f $id)), $bytes)
            $results[$id] = @{ status = [int]$resp.StatusCode; json = ([Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json) }
        }
    }
}
finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}

# ================= 5. 기준 PC 의 출력과 견준다 =================
$exp = ReadJson (Join-Path $Here 'expected.json')
$same = 0
$rows = @()
foreach ($e in $exp.items) {
    $id = [int]$e.id
    $row = [ordered]@{ id = $id; result = 'error'; n = 0; expected_n = [int]$e.n }
    $r = $results[$id]
    if ($r -and $r.status -eq 200) {
        $j = $r.json
        $text = [string]$j.choices[0].text
        $row.n = [int]$j.usage.completion_tokens
        $row.text_sha256 = Sha256Hex ([Text.Encoding]::UTF8.GetBytes($text))
        if ($j.geulpu) {
            $row.tokens_sha256 = Sha256Hex ([Text.Encoding]::ASCII.GetBytes((@($j.geulpu.tokens) -join ',')))
            $row.logit_hashes_sha256 = Sha256Hex ([Text.Encoding]::ASCII.GetBytes((@($j.geulpu.logit_hashes) -join ',')))
        }
        if ($row.text_sha256 -eq $e.text_sha256) { $row.result = 'same'; $same++ }
        else {
            $et = [string]$e.text
            $m = [Math]::Min($et.Length, $text.Length)
            $k = 0
            while ($k -lt $m -and ([int]$et[$k]) -eq ([int]$text[$k])) { $k++ }
            $row.result = 'different'
            $row.first_diff_char = $k
        }
    }
    elseif ($r) { $row.error = ('status {0} {1}' -f $r.status, $r.error) }
    $rows += New-Object psobject -Property $row
}
$total = @($exp.items).Count

# ================= 6. 결과 묶기 (사용자 이름 · 폴더 경로는 지운다) =================
$run = [ordered]@{ slots = $slots; generate_minutes = [Math]::Round($genMinutes, 1); date = $Stamp; compare_only = [bool]$CompareOnly }
$summary = [ordered]@{ environment = $EnvInfo; run = $run; reference = $exp.reference; same = $same; total = $total; items = $rows }
$summary | ConvertTo-Json -Depth 7 | Out-File -FilePath (Join-Path $Out 'summary.json') -Encoding UTF8
Get-ChildItem -LiteralPath $Out -Filter *.log | ForEach-Object {
    $t = [IO.File]::ReadAllText($_.FullName)
    $t = $t.Replace($Here, '<folder>').Replace($env:USERPROFILE, '<home>')
    [IO.File]::WriteAllText($_.FullName, $t)
}
$zip = $Out + '.zip'
Compress-Archive -Path (Join-Path $Out '*') -DestinationPath $zip -Force

Write-Host ''
if ($same -eq $total) { Write-Host ('결과: 32 문제 모두 기준 PC 와 똑같은 출력입니다 ({0}/{1}).' -f $same, $total) -ForegroundColor Green }
else { Write-Host ('결과: {0}/{1} 문제만 기준 PC 와 같습니다.' -f $same, $total) -ForegroundColor Yellow }
Write-Host ('이 파일을 보내 주세요: ' + $zip)
