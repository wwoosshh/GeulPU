# GeulPU 교차 검증 — 다른 PC 에서도 같은 출력이 나오는가
#   모델: DeepSeek-R1-Distill-Qwen-7B Q8_0 · 수학 문제 32 개 · 탐욕 생성(temperature 0) · 답 길이 상한 3200 토큰
#   쓰는 법: git clone https://github.com/wwoosshh/GeulPU 한 뒤 교차검증\run.bat 을 실행한다.
#     1. 환경 검사  2. 소스에서 빌드(글 컴파일러 → PTX 뒷단 → 생성기 · 서버 → 7B 모듈 — 단계마다 기준 PC 의 해시와 대조)
#     3. 모델 받기(8.1 GB)  4. 생성  5. 기준 PC 의 출력과 비교  6. 자기 진단(32단계)  7. result-….zip
#   진단만: diag.bat (-DiagOnly) — 빌드 · 모델 확인 뒤 생성은 건너뛰고 자기 진단만(이 기기의 바닥과 커널마다의 바닥 대비, 1~2 분).
param([switch]$BuildOnly, [switch]$CompareOnly, [switch]$DiagOnly, [string]$ResponsesDir = '', [string]$GeulC = '')
# 시험용 인자: -BuildOnly(빌드까지만) · -CompareOnly -ResponsesDir <폴더>(받은 응답으로 비교만) · -GeulC <geulc.exe>(첫 컴파일러를 받지 않고 이것으로)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path        # …\GeulPU\교차검증
$Root = Split-Path -Parent $Here                                 # …\GeulPU
$Work = Join-Path $Here 'work'
Set-Location -LiteralPath $Here
[Environment]::SetEnvironmentVariable('CUDA_DEVICE_ORDER', 'PCI_BUS_ID', 'Process')   # CUDA 장치 0 = nvidia-smi 의 GPU 0

$ScriptVersion = 'crosscheck-r1-v4'
$ModelName  = 'DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf'
$ModelUrl   = 'https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf'
$ModelSize  = 8098524896
$ModelSha   = '7307bfbb539fd2e8ed636315440781fed23140dc7f911f64b33418f5b978281b'
$GeulZipUrl = 'https://github.com/wwoosshh/geul-lang/releases/download/2g-1.3.1/geul-1.3.1-windows-x64.zip'
$GeulZipSha = 'a1b71f1ddddd1a858593e33b0ff3c7e4e4e5afe4e6381c70e5817dedcfd36f72'
$GeulRepo   = 'https://github.com/wwoosshh/geul-lang'
$Port       = 18091
$Context    = 3584
$MaxTokens  = 3200

function Say([string]$m) { Write-Host ('[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Fail([string]$m) {
    # 결과 폴더가 있으면 그때까지의 기록을 묶어 남긴다
    if ($script:Out -and (Test-Path -LiteralPath $script:Out)) { Finish ('중단: ' + $m) 'Red' }
    else { Write-Host ''; Write-Host ('중단: ' + $m) -ForegroundColor Red }
    exit 1
}
function Sha256Hex([byte[]]$b) {
    $h = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($h.ComputeHash($b)) -replace '-', '').ToLower() } finally { $h.Dispose() }
}
function FileSha([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() }
function ReadJson([string]$path) { return ([IO.File]::ReadAllText($path, [Text.Encoding]::UTF8) | ConvertFrom-Json) }
function ToInt($s) { $r = 0; if ([int]::TryParse(([string]$s).Trim(), [ref]$r)) { return $r }; return 0 }
function Native([string[]]$a) {
    # 바깥 명령(nvidia-smi · git · powercfg …)의 출력 — 실패해도 멈추지 않는다
    $ErrorActionPreference = 'Continue'
    try {
        if ($a.Count -gt 1) { $o = & $a[0] $a[1..($a.Count - 1)] 2>$null } else { $o = & $a[0] 2>$null }
        if ($LASTEXITCODE -ne 0) { return @() }
        return @($o | ForEach-Object { ([string]$_).Trim() })
    } catch { return @() }
}
function Quote([string]$s) { if ($s -match '[\s"]') { return '"' + ($s -replace '"', '\"') + '"' }; return $s }
function Tool([string]$exe, [string[]]$argv, [string]$cwd, [string]$name) {
    # 빌드 도구를 돌리고 종료 코드를 돌려준다(출력은 기록 폴더에)
    $o = Join-Path $LogDir ($name + '.log'); $e = Join-Path $LogDir ($name + '-err.log')
    $p = Start-Process -FilePath $exe -ArgumentList ($argv | ForEach-Object { Quote $_ }) -WorkingDirectory $cwd -NoNewWindow -PassThru `
        -RedirectStandardOutput $o -RedirectStandardError $e
    $null = $p.Handle
    $p.WaitForExit()
    return $p.ExitCode
}
function Download([string]$url, [string]$dest) {
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (Test-Path -LiteralPath $curl) {
        & $curl -L --fail --retry 5 --retry-delay 5 -C - -o $dest $url
        return ($LASTEXITCODE -eq 0)
    }
    Import-Module BitsTransfer
    Start-BitsTransfer -Source $url -Destination $dest
    return $true
}

$Checks = New-Object System.Collections.ArrayList
function Check([string]$name, [string]$state, [string]$detail) {
    [void]$Checks.Add([ordered]@{ name = $name; state = $state; detail = $detail })
    $color = 'Gray'
    if ($state -eq '통과') { $color = 'Green' } elseif ($state -eq '경고') { $color = 'Yellow' } elseif ($state -eq '실패') { $color = 'Red' }
    Write-Host ('  [{0}] {1}: {2}' -f $state, $name, $detail) -ForegroundColor $color
}

Write-Host '=== GeulPU 교차 검증 (R1 · 32 문제) ==='
Write-Host '환경 검사 → 소스에서 빌드(1~3 분) → 모델 받기(8.1 GB, 없을 때만) → 생성(GPU 에 따라 5~15 분) → 비교. 창을 닫지 마세요.'
Write-Host ''

$exp = ReadJson (Join-Path $Here 'expected.json')

# ================= 1. 환경 검사 =================
Write-Host '--- 환경 검사 ---'
$EnvInfo = [ordered]@{ script = $ScriptVersion; checked_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') }

$os = Get-CimInstance Win32_OperatingSystem
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction SilentlyContinue
$disp = ''; $ubr = ''
if ($cv) { $disp = [string]$cv.DisplayVersion; $ubr = [string]$cv.UBR }
$EnvInfo.os = [ordered]@{ caption = [string]$os.Caption; display_version = $disp; build = ([string]$os.BuildNumber + '.' + $ubr)
                          architecture = [string]$os.OSArchitecture; locale = (Get-Culture).Name }
if ([string]$os.OSArchitecture -match '64') { Check '운영체제' '통과' ('{0} {1} (빌드 {2})' -f $os.Caption, $disp, $EnvInfo.os.build) }
else { Check '운영체제' '실패' '64 비트 윈도가 필요합니다' }

$netRel = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue).Release
$EnvInfo.powershell = $PSVersionTable.PSVersion.ToString()
$EnvInfo.dotnet_release = $netRel
Check 'PowerShell · .NET' '정보' ('PowerShell {0} · .NET 4 릴리스 {1}' -f $EnvInfo.powershell, $netRel)

$cpuObj = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem
$EnvInfo.cpu = [ordered]@{ name = ([string]$cpuObj.Name).Trim(); cores = [int]$cpuObj.NumberOfCores; threads = [int]$cpuObj.NumberOfLogicalProcessors
                           max_mhz = [int]$cpuObj.MaxClockSpeed }
$EnvInfo.ram_gb = [Math]::Round([double]$cs.TotalPhysicalMemory / 1GB, 1)
Check 'CPU · 메모리' '정보' ('{0} · {1}코어 {2}스레드 · RAM {3} GB' -f $EnvInfo.cpu.name, $EnvInfo.cpu.cores, $EnvInfo.cpu.threads, $EnvInfo.ram_gb)

$nvcuda = Join-Path $env:SystemRoot 'System32\nvcuda.dll'
$EnvInfo.nvcuda_dll = $null
if (Test-Path -LiteralPath $nvcuda) {
    $EnvInfo.nvcuda_dll = (Get-Item -LiteralPath $nvcuda).VersionInfo.FileVersion
    Check 'CUDA 드라이버 (nvcuda.dll)' '통과' $EnvInfo.nvcuda_dll
}
else { Check 'CUDA 드라이버 (nvcuda.dll)' '실패' 'NVIDIA 그래픽 드라이버가 필요합니다' }

$gpu = 'unknown'; $driver = ''; $vram = 0; $cap = ''
$slotsList = @(8, 2, 1)
$gpus = @()
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $head = (Native @('nvidia-smi')) -join "`n"
    $EnvInfo.cuda_driver_version = ''
    if ($head -match 'CUDA (?:UMD )?Version:\s*([0-9.]+)') { $EnvInfo.cuda_driver_version = $Matches[1] }   # 새 드라이버는 'CUDA UMD Version'
    $fields = @('index', 'name', 'pci.bus_id', 'driver_version', 'driver_model.current', 'vbios_version', 'compute_cap', 'memory.total',
                'memory.used', 'pcie.link.gen.max', 'pcie.link.width.max', 'clocks.max.sm', 'clocks.max.memory', 'power.limit', 'temperature.gpu')
    $cols = @{}
    foreach ($f in $fields) { $cols[$f] = @(Native @('nvidia-smi', ('--query-gpu=' + $f), '--format=csv,noheader,nounits')) }
    for ($i = 0; $i -lt @($cols['index']).Count; $i++) {
        $g = [ordered]@{}
        foreach ($f in $fields) { $v = @($cols[$f]); if ($i -lt $v.Count) { $g[$f] = $v[$i] } else { $g[$f] = $null } }
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

$hags = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers' -Name HwSchMode -ErrorAction SilentlyContinue).HwSchMode
$EnvInfo.hardware_gpu_scheduling = 'default'
if ($hags -eq 2) { $EnvInfo.hardware_gpu_scheduling = 'on' } elseif ($hags -eq 1) { $EnvInfo.hardware_gpu_scheduling = 'off' }
$plan = ''
$pc = (Native @('powercfg', '/getactivescheme')) -join ' '
if ($pc -match '\(([^)]+)\)') { $plan = $Matches[1] }
$EnvInfo.power_plan = $plan
Check '그래픽 일정 · 전원' '정보' ('하드웨어 가속 GPU 일정 {0} · 전원 계획 {1}' -f $EnvInfo.hardware_gpu_scheduling, $plan)

# git · 저장소
$gitv = (Native @('git', '--version')) -join ' '
$EnvInfo.git = $gitv
if ($gitv) { Check 'git' '통과' $gitv } else { Check 'git' '실패' 'git 이 필요합니다 (https://git-scm.com)' }
$EnvInfo.geulpu_commit = ((Native @('git', '-C', $Root, 'rev-parse', 'HEAD')) -join '')
$dirty = @(Native @('git', '-C', $Root, 'status', '--porcelain', '--', '호스트', '커널', '교차검증/run.ps1', '교차검증/expected.json', '교차검증/requests.json')).Count
$EnvInfo.geulpu_modified = ($dirty -gt 0)
if ($dirty -gt 0) { Check 'GeulPU 저장소' '경고' ('커밋 {0} · 고친 파일이 있습니다 (빌드 해시가 다를 수 있음)' -f $EnvInfo.geulpu_commit) }
else { Check 'GeulPU 저장소' '통과' ('커밋 {0}' -f $EnvInfo.geulpu_commit) }

# 디스크 · 모델
$ModelPath = $null
foreach ($c in @((Join-Path $Here $ModelName), (Join-Path $Work $ModelName))) { if (Test-Path -LiteralPath $c) { $ModelPath = $c; break } }
$freeGB = [Math]::Round((Get-Item -LiteralPath $Here).PSDrive.Free / 1GB, 1)
$EnvInfo.disk_free_gb = $freeGB
$EnvInfo.model_present = [bool]$ModelPath
if ($ModelPath) { Check '디스크 · 모델' '통과' ('여유 {0} GB · 모델 파일 있음' -f $freeGB) }
elseif ($CompareOnly -or $BuildOnly -or $freeGB -ge 10) { Check '디스크 · 모델' '통과' ('여유 {0} GB · 모델을 받습니다 (8.1 GB)' -f $freeGB) }
else { Check '디스크 · 모델' '실패' ('여유 {0} GB — 10 GB 이상이 필요합니다' -f $freeGB) }

# ---- 결과 폴더 ----
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$safeGpu = (($gpu -replace '[^A-Za-z0-9]+', '-').Trim('-'))
$Out = Join-Path $Here ('result-' + $safeGpu + '-' + $Stamp)
$RespOut = Join-Path $Out 'responses'
$LogDir = Join-Path $Out 'logs'
New-Item -ItemType Directory -Path $RespOut -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $Work -Force | Out-Null

function Finish([string]$headline, [string]$color) {
    # 기록을 남기고(사용자 이름 · 폴더 경로는 지운다) zip 으로 묶는다
    $EnvInfo.checks = $Checks
    $EnvInfo | ConvertTo-Json -Depth 6 | Out-File -FilePath (Join-Path $Out 'environment.json') -Encoding UTF8
    Get-ChildItem -LiteralPath $Out -Recurse -Filter *.log | ForEach-Object {
        $t = [IO.File]::ReadAllText($_.FullName)
        $t = $t.Replace($Root, '<GeulPU>').Replace($env:USERPROFILE, '<home>')
        [IO.File]::WriteAllText($_.FullName, $t)
    }
    $zip = $Out + '.zip'
    Compress-Archive -Path (Join-Path $Out '*') -DestinationPath $zip -Force
    Write-Host ''
    Write-Host $headline -ForegroundColor $color
    Write-Host ('이 파일을 보내 주세요: ' + $zip)
}

# 32단계 — 자기 진단: 이 기기의 바닥(메모리 읽기 대역 · 정수 텐서 코어 최고치)을 그 자리에서 재고, 7B 엔진의 커널 종류마다 시간과 바닥 대비를
# 적는다(생성 한 줄 · 여덟 줄 · 프롬프트 · 슬롯 여덟 · 넷의 생성 걸음). 엔진이 이 기기에서 후보마다 잰 판과 고른 판, 그리고 31단계의 후보로
# 고른 그래프와 모든 후보로 고른 그래프를 번갈아 잰 비(슬롯 여덟 · 넷)도 적는다. 같은 자리에서 여러 번 재 가장 빠른 값을 쓴다. GPU 를
# 쓰는 다른 프로그램은 함께 적어 둔다.
function RunDiag {
    Write-Host ''
    Say '자기 진단: 이 기기의 바닥과 커널마다의 바닥 대비를 잽니다 (1~2 분)...'
    $gs = (Native @('nvidia-smi', '--query-gpu=utilization.gpu,memory.used,clocks.sm,clocks.mem,power.draw,temperature.gpu', '--format=csv')) -join "`n"
    $apps = (Native @('nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv')) -join "`n"
    [IO.File]::WriteAllText((Join-Path $Out 'diag-gpu-state.txt'), ($gs + "`n`n" + $apps + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    $code = Tool $diagExe @($diagPtx, (Join-Path $Out 'diag.json'), $ModelPath, $modPtx) $Work 'diag'
    if ($code -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $Out 'diag.json'))) { Check '자기 진단' '경고' '실패 — logs 의 diag.log 를 보내 주세요'; return }
    $d = ReadJson (Join-Path $Out 'diag.json')
    $EnvInfo.diag = [ordered]@{ read_bandwidth_gbs = $d.'바닥'.'읽기대역_GBs'; spec_bandwidth_gbs = $d.'바닥'.'사양대역_GBs'; int8_tops = $d.'바닥'.'정수텐서_TOPS';
                                ab8_ratio = $d.'번갈아_여덟슬롯'.'비_가운데'; ab4_ratio = $d.'번갈아_네슬롯'.'비_가운데' }
    $line = '대역 {0:N1} GB/s (사양 {1:N1}) · 정수 텐서 {2:N1} TOPS' -f $d.'바닥'.'읽기대역_GBs', $d.'바닥'.'사양대역_GBs', $d.'바닥'.'정수텐서_TOPS'
    foreach ($k in @('생성 문맥 1024', '슬롯 여덟 걸음 문맥 2048', '프롬프트 2048')) {
        $c = $d.'커널'.$k
        if ($c) { $line += (' · {0} {1:N2} 배' -f $k, $c.'배') }
    }
    if ($d.'번갈아_여덟슬롯') { $line += (' · 32/31 슬롯 여덟 {0:N3} · 넷 {1:N3}' -f $d.'번갈아_여덟슬롯'.'비_가운데', $d.'번갈아_네슬롯'.'비_가운데') }
    Check '자기 진단' '통과' $line
}

$failed = @($Checks | Where-Object { $_.state -eq '실패' }).Count
if ($failed -gt 0 -and -not $CompareOnly) {
    Finish ('환경 검사에서 실패 {0} 건 — 위 내용을 확인해 주세요.' -f $failed) 'Red'
    exit 1
}

$results = @{}
$slots = 0
$genMinutes = 0.0
$proc = $null
$Build = [ordered]@{}

try {
    if (-not $CompareOnly) {
        # ================= 2. 소스에서 빌드 =================
        Write-Host ''
        Write-Host '--- 소스에서 빌드 (기준 PC 의 해시와 대조) ---'
        $want = $exp.build
        function BuildCheck([string]$name, [string]$path, [string]$wantSha) {
            if (-not (Test-Path -LiteralPath $path)) { Check $name '실패' '만들어지지 않았습니다 (logs 폴더를 보내 주세요)'; return $false }
            $s = FileSha $path
            $Build[$name] = $s
            if ($s -eq $wantSha) { Check $name '통과' ('기준과 같음 ' + $s.Substring(0, 12)) }
            else { Check $name '경고' ('기준과 다름 ' + $s.Substring(0, 12) + ' (기준 ' + $wantSha.Substring(0, 12) + ')') }
            return $true
        }

        # a. 첫 컴파일러: 글 1.3.1 공개 배포판(github.com/wwoosshh/geul-lang 의 릴리스)
        if ($GeulC) {
            $geulc0 = $GeulC
            Check '첫 컴파일러' '정보' ('지정한 것: ' + $GeulC)
        }
        else {
            $geulZip = Join-Path $Work 'geul-1.3.1-windows-x64.zip'
            if (-not (Test-Path -LiteralPath $geulZip)) {
                Say '글 1.3.1 컴파일러를 받습니다 (182 KB)...'
                if (-not (Download $GeulZipUrl $geulZip)) { Fail '글 1.3.1 을 받지 못했습니다.' }
            }
            if ((FileSha $geulZip) -ne $GeulZipSha) { Remove-Item -LiteralPath $geulZip -Force; Fail '글 1.3.1 zip 의 SHA-256 이 다릅니다. 다시 실행해 주세요.' }
            $geul0Dir = Join-Path $Work 'geul-1.3.1'
            if (-not (Test-Path -LiteralPath $geul0Dir)) { Expand-Archive -LiteralPath $geulZip -DestinationPath $geul0Dir -Force }
            $geulc0 = (Get-ChildItem -LiteralPath $geul0Dir -Recurse -Filter 'geulc.exe' | Select-Object -First 1).FullName
            if (-not $geulc0) { Fail 'geulc.exe 를 찾지 못했습니다.' }
            Check '첫 컴파일러 (글 1.3.1)' '통과' 'SHA-256 확인'
        }

        # b. 글 저장소의 고정 커밋(GeulPU 의 시험/글저장소커밋.txt — CI 와 같다)
        $pin = ([IO.File]::ReadAllText((Join-Path $Root '시험\글저장소커밋.txt'))).Trim()
        $GeulDir = Join-Path $Work 'geul-lang'
        if (-not (Test-Path -LiteralPath (Join-Path $GeulDir '.git'))) {
            Say '글 저장소를 받습니다 (약 35 MB)...'
            & git clone --quiet $GeulRepo $GeulDir
            if ($LASTEXITCODE -ne 0) { Fail '글 저장소를 받지 못했습니다 (git clone).' }
        }
        & git -C $GeulDir -c advice.detachedHead=false checkout --quiet $pin
        if ($LASTEXITCODE -ne 0) { & git -C $GeulDir fetch --quiet origin; & git -C $GeulDir -c advice.detachedHead=false checkout --quiet $pin }
        $head2 = ((Native @('git', '-C', $GeulDir, 'rev-parse', 'HEAD')) -join '')
        if ($head2 -ne $pin) { Fail ('글 저장소를 고정 커밋 ' + $pin + ' 으로 맞추지 못했습니다.') }
        Check '글 저장소' '통과' ('고정 커밋 ' + $pin)
        $EnvInfo.geul_commit = $pin
        [Environment]::SetEnvironmentVariable('GEUL_ROOT', $GeulDir, 'Process')
        [Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'Process')

        # c. 글 컴파일러 — 두 번 빌드해 고정점(첫 컴파일러가 무엇이든 같은 바이트)
        Say '글 컴파일러를 빌드합니다...'
        $s1 = Join-Path $Work 'self_s1.exe'
        $comp = Join-Path $Work 'self_compiler.exe'
        $code = Tool $geulc0 @('self/컴파일러.gl', '-o', $s1) $GeulDir 'build-compiler-s1'
        if ($code -ne 0 -or -not (Test-Path -LiteralPath $s1)) {
            $py = Get-Command python -ErrorAction SilentlyContinue
            if (-not $py) { Fail '글 1.3.1 로 컴파일러를 빌드하지 못했고, 대신 쓸 파이썬도 없습니다. logs 폴더를 보내 주세요.' }
            Say '글 1.3.1 로 안 되어 파이썬 참조 구현으로 빌드합니다 (몇 분)...'
            $code = Tool $py.Source @('ref/geulc.py', 'self/컴파일러.gl', '-o', $s1) $GeulDir 'build-compiler-s1-python'
            if ($code -ne 0) { Fail '파이썬으로도 컴파일러를 빌드하지 못했습니다. logs 폴더를 보내 주세요.' }
        }
        $code = Tool $s1 @('self/컴파일러.gl', '-o', $comp) $GeulDir 'build-compiler'
        if ($code -ne 0) { Fail '글 컴파일러 빌드 실패. logs 폴더를 보내 주세요.' }
        [void](BuildCheck '글 컴파일러' $comp $want.self_compiler)

        # d. PTX 뒷단
        Say 'PTX 뒷단을 빌드합니다...'
        $ptxBackend = Join-Path $Work 'ptx_backend.exe'
        $code = Tool $comp @('research/gpu/자체PTX/PTX.gl', '-o', $ptxBackend) $GeulDir 'build-ptx-backend'
        if ($code -ne 0) { Fail 'PTX 뒷단 빌드 실패.' }
        [void](BuildCheck 'PTX 뒷단' $ptxBackend $want.ptx_backend)

        # e. 서버 — 저장소의 호스트 · 커널을 work\src 에 복사하고 토크나이저 두 곳만 고친다(토크나이저_R1.diff 와 같은 내용)
        Say '서버를 빌드합니다 (토크나이저 두 곳만 이 모델에 맞춤)...'
        $Src = Join-Path $Work 'src'
        if (Test-Path -LiteralPath $Src) { Remove-Item -LiteralPath $Src -Recurse -Force }
        New-Item -ItemType Directory -Path $Src | Out-Null
        Copy-Item -LiteralPath (Join-Path $Root '호스트') -Destination $Src -Recurse
        Copy-Item -LiteralPath (Join-Path $Root '커널') -Destination $Src -Recurse
        $tk = Join-Path $Src '호스트\토크나이저.gl'
        $t = [IO.File]::ReadAllText($tk, [Text.Encoding]::UTF8).Replace("`r`n", "`n")
        $old1 = '    아닌 (문자열_같은가(메타글(g, "tokenizer.ggml.model"), "gpt2") 그리고 문자열_같은가(메타글(g, "tokenizer.ggml.pre"), "qwen2"))이면 {'
        $new1 = '    참거짓 딥시크 = 문자열_같은가(메타글(g, "tokenizer.ggml.pre"), "deepseek-r1-qwen").' + "`n" +
                '    아닌 (문자열_같은가(메타글(g, "tokenizer.ggml.model"), "gpt2") 그리고 (문자열_같은가(메타글(g, "tokenizer.ggml.pre"), "qwen2") 또는 딥시크))이면 {'
        $old2 = '    끝토큰 = 특수번호("<|im_end|>").' + "`n" + '    글끝토큰 = 특수번호("<|endoftext|>").'
        $new2 = '    딥시크이면 {' + "`n" + '        끝토큰 = 특수번호("<｜end▁of▁sentence｜>").' + "`n" + '        글끝토큰 = 끝토큰.' + "`n" + '    }' + "`n" +
                '    아니면 {' + "`n" + '        끝토큰 = 특수번호("<|im_end|>").' + "`n" + '        글끝토큰 = 특수번호("<|endoftext|>").' + "`n" + '    }'
        if (-not $t.Contains($old1) -or -not $t.Contains($old2)) { Fail '토크나이저.gl 이 예상과 달라 고칠 수 없습니다 (저장소 판을 확인해 주세요).' }
        $t = $t.Replace($old1, $new1).Replace($old2, $new2)
        [IO.File]::WriteAllText($tk, $t, (New-Object System.Text.UTF8Encoding($false)))
        $server = Join-Path $Work 'server_r1.exe'
        $code = Tool $comp @('호스트/서버.gl', '-o', $server) $Src 'build-server'
        if ($code -ne 0) { Fail '서버 빌드 실패.' }
        [void](BuildCheck '서버 (R1)' $server $want.server_r1)

        # f. 생성기 → 7B Q8_0 모듈 → PTX
        Say '커널 생성기 · 7B 모듈 · PTX 를 만듭니다 (1~2 분)...'
        $gen = Join-Path $Work 'kernel_gen.exe'
        $code = Tool $comp @('커널/커널생성.gl', '-o', $gen) $Root 'build-generator'
        if ($code -ne 0) { Fail '커널 생성기 빌드 실패.' }
        [void](BuildCheck '커널 생성기' $gen $want.generator)
        $modGl = Join-Path $Work 'qwen2Q8_7b.gl'
        $code = Tool $gen @('qwen2Q8_7b', $modGl) $Root 'generate-module'
        if ($code -ne 0) { Fail '모듈 소스 생성 실패.' }
        [void](BuildCheck '7B 모듈 소스' $modGl $want.module_source)
        $modPtx = Join-Path $Work 'q8_7b.ptx'
        $code = Tool $ptxBackend @($modGl, '-o', $modPtx) $Root 'build-module-ptx'
        if ($code -ne 0) { Fail '모듈 PTX 빌드 실패.' }
        [void](BuildCheck '7B 모듈 PTX' $modPtx $want.module_ptx)

        # g. 자기 진단 도구(32단계) — 진단 커널(PTX) · 진단 프로그램
        Say '자기 진단 도구를 빌드합니다...'
        $diagPtx = Join-Path $Work 'diag.ptx'
        $code = Tool $ptxBackend @('커널/진단.gl', '-o', $diagPtx) $Root 'build-diag-ptx'
        if ($code -ne 0) { Fail '진단 커널 빌드 실패.' }
        $diagExe = Join-Path $Work 'diag.exe'
        $code = Tool $comp @('호스트/진단.gl', '-o', $diagExe) $Root 'build-diag'
        if ($code -ne 0) { Fail '진단 프로그램 빌드 실패.' }
        $EnvInfo.build = $Build

        if ($BuildOnly) { Finish '빌드만 했습니다 (-BuildOnly).' 'Green'; exit 0 }

        # ================= 3. 모델 =================
        Write-Host ''
        if (-not $ModelPath) {
            $ModelPath = Join-Path $Work $ModelName
            Say '모델을 받습니다 (8.1 GB, Hugging Face). 끊기면 다시 실행하면 이어서 받습니다.'
            if (-not (Download $ModelUrl ($ModelPath + '.part'))) { Fail '모델 받기에 실패했습니다. 다시 실행해 주세요.' }
            Move-Item -LiteralPath ($ModelPath + '.part') -Destination $ModelPath
        }
        $len = (Get-Item -LiteralPath $ModelPath).Length
        if ($len -ne $ModelSize) { Fail ('모델 파일 크기가 다릅니다 ({0} 바이트). 파일을 지우고 다시 실행해 주세요.' -f $len) }
        Say '모델 파일 확인 중 (SHA-256, 1~2 분)...'
        if ((FileSha $ModelPath) -ne $ModelSha) { Fail '모델 파일의 SHA-256 이 다릅니다. 파일을 지우고 다시 실행해 주세요.' }
        Say '모델 확인 완료.'

        if ($DiagOnly) {
            RunDiag
            Finish '자기 진단을 마쳤습니다 (-DiagOnly — 생성은 건너뜀).' 'Green'
            exit 0
        }

        # ================= 4. 서버를 띄우고(127.0.0.1 에서만) 32 문제를 한꺼번에 보낸다 =================
        $ok = $false
        foreach ($s in $slotsList) {
            $argList = @((Quote $ModelPath), '--ptx', (Quote $modPtx), '--슬롯', "$s", '--문맥', "$Context", '--포트', "$Port")
            Say ('서버를 띄웁니다 (슬롯 {0})...' -f $s)
            $proc = Start-Process -FilePath $server -ArgumentList $argList -PassThru -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $LogDir ('server-{0}.log' -f $s)) -RedirectStandardError (Join-Path $LogDir ('server-{0}-err.log' -f $s))
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
        if (-not $ok) { Finish '서버를 띄우지 못했습니다.' 'Red'; exit 1 }
        Say ('서버 준비 완료 (슬롯 {0}).' -f $slots)

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
            if ($proc.HasExited) { Finish '생성 도중에 서버가 끝났습니다.' 'Red'; exit 1 }
            Start-Sleep -Seconds 30
        }
        $genMinutes = ((Get-Date) - $tg).TotalMinutes
        foreach ($id in ($tasks.Keys | Sort-Object)) {
            $tk2 = $tasks[$id]
            if ($tk2.IsFaulted -or $tk2.IsCanceled) { $results[$id] = @{ status = 0; error = [string]$tk2.Exception }; continue }
            $resp = $tk2.Result
            $bytes = $resp.Content.ReadAsByteArrayAsync().Result
            [IO.File]::WriteAllBytes((Join-Path $RespOut ('{0:D2}.json' -f $id)), $bytes)
            $results[$id] = @{ status = [int]$resp.StatusCode; json = ([Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json) }
        }
    }
    else {
        # 시험용: 이미 받은 응답 파일(NN.json)로 비교만 한다
        Get-ChildItem -LiteralPath $ResponsesDir -Filter *.json | ForEach-Object {
            $bytes = [IO.File]::ReadAllBytes($_.FullName)
            [IO.File]::WriteAllBytes((Join-Path $RespOut $_.Name), $bytes)
            $results[[int]$_.BaseName] = @{ status = 200; json = ([Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json) }
        }
    }
}
finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}

# ================= 5. 기준 PC 의 출력과 견준다 =================
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
$run = [ordered]@{ slots = $slots; generate_minutes = [Math]::Round($genMinutes, 1); date = $Stamp; compare_only = [bool]$CompareOnly }
$summary = [ordered]@{ environment = $EnvInfo; build = $Build; run = $run; reference = $exp.reference; same = $same; total = $total; items = $rows }
$summary | ConvertTo-Json -Depth 7 | Out-File -FilePath (Join-Path $Out 'summary.json') -Encoding UTF8
if (-not $CompareOnly -and $diagExe) { RunDiag }
if ($same -eq $total) { Finish ('결과: 32 문제 모두 기준 PC 와 똑같은 출력입니다 ({0}/{1}).' -f $same, $total) 'Green' }
else { Finish ('결과: {0}/{1} 문제만 기준 PC 와 같습니다.' -f $same, $total) 'Yellow' }
