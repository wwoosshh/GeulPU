# GeulPU 교차 검증 (Vulkan) — AMD 등 다른 회사의 GPU 에서도 기준 PC(NVIDIA · CUDA)와 같은 출력이 나오는가
#   모델 · 문제 · 설정 · 비교 기준은 run.ps1(CUDA)과 같다: DeepSeek-R1-Distill-Qwen-7B Q8_0 · 수학 문제 32 개 · 탐욕 생성(temperature 0) ·
#   답 길이 상한 3200 토큰. 다른 것은 GPU 층뿐이다 — nvcuda.dll 대신 vulkan-1.dll, PTX 대신 글(geul) 컴파일러의 SPIR-V 뒷단이 낸 묶음(.spvs).
#   쓰는 법: git clone https://github.com/wwoosshh/GeulPU 한 뒤 교차검증\runV.bat 을 실행한다.
#     1. 환경 검사  2. 소스에서 빌드(글 컴파일러 → Vulkan 장치 검사 → SPIR-V 뒷단 → 서버(Vulkan) · 생성기 → 7B 모듈 둘(기본 · 협력 행렬)
#        → SPIR-V 묶음 — 단계마다 기준 PC 의 해시와 대조)  3. 모델 받기(8.1 GB)  4. 생성 — 협력 행렬 모듈(장치에 있으면)과 기본 모듈로
#        한 번씩  5. 기준 PC 의 출력과 비교  6. 자기 진단  7. result-V-….zip
#   진단만: diagV.bat (-DiagOnly) — 빌드 · 모델 확인 뒤 생성은 건너뛰고 자기 진단만.
#   속도만: speedV.bat (-SpeedOnly, 35단계) — 빌드 · 모델 확인 뒤 자기 진단을 지금 판 · 34단계(34m) 판으로 번갈아(협력 모듈 두 바퀴,
#     기본 모듈 한 바퀴) 재어 판마다의 시간과 비를 적는다(공유32 장치 — 보통 장치는 지금 판만).
param([switch]$BuildOnly, [switch]$DiagOnly, [switch]$SpeedOnly, [string]$GeulC = '', [string]$Device = '', [string]$Modules = 'both')
# 시험용 인자: -BuildOnly(빌드까지만) · -GeulC <geulc.exe>(첫 컴파일러를 받지 않고 이것으로) · -Device <Vulkan 장치 이름의 일부>(기본은
#   엔진처럼 첫 외장 GPU) · -Modules both | coop | base(협력 행렬 모듈 · 기본 모듈 가운데 무엇으로 생성하나 — 기본 both)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path        # …\GeulPU\교차검증
$Root = Split-Path -Parent $Here                                 # …\GeulPU
$Work = Join-Path $Here 'work'
Set-Location -LiteralPath $Here

$ScriptVersion = 'crosscheck-r1-vulkan-v1'
$ModelName  = 'DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf'
$ModelUrl   = 'https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf'
$ModelSize  = 8098524896
$ModelSha   = '7307bfbb539fd2e8ed636315440781fed23140dc7f911f64b33418f5b978281b'
$GeulZipUrl = 'https://github.com/wwoosshh/geul-lang/releases/download/2g-1.3.1/geul-1.3.1-windows-x64.zip'
$GeulZipSha = 'a1b71f1ddddd1a858593e33b0ff3c7e4e4e5afe4e6381c70e5817dedcfd36f72'
$GeulRepo   = 'https://github.com/wwoosshh/geul-lang'
$Port       = 18092
$Context    = 3584
$MaxTokens  = 3200
if (@('both', 'coop', 'base') -notcontains $Modules) { Write-Host '-Modules 는 both · coop · base 가운데 하나' -ForegroundColor Red; exit 1 }

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
function Native([string[]]$a) {
    # 바깥 명령(git · powercfg …)의 출력 — 실패해도 멈추지 않는다
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
    $o = Join-Path $script:LogDir ($name + '.log'); $e = Join-Path $script:LogDir ($name + '-err.log')
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
function GpuMemUsedMiB {
    # 모든 GPU 의 전용 메모리 사용 가운데 가장 큰 것(윈도의 GPU 성능 카운터 — 회사와 상관없다). 못 읽으면 -1
    try {
        $m = @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction Stop)
        if ($m.Count -eq 0) { return -1 }
        return [int][Math]::Round((($m | Measure-Object -Property DedicatedUsage -Maximum).Maximum) / 1MB)
    } catch { return -1 }
}
function GpuState {
    # 그때 GPU 를 쓰던 프로그램 · 엔진 사용률(윈도의 GPU 성능 카운터)
    $lines = @()
    try {
        foreach ($a in @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction Stop)) {
            $lines += ('어댑터 {0}: 전용 {1:N0} MiB · 공유 {2:N0} MiB' -f ($a.Name -replace '^luid_0x[0-9A-Fa-f]+_0x([0-9A-Fa-f]+).*$', '$1'),
                       ([double]$a.DedicatedUsage / 1MB), ([double]$a.SharedUsage / 1MB))
        }
        foreach ($p in @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory -ErrorAction Stop | Where-Object { $_.DedicatedUsage -gt 64MB })) {
            $procId = 0; if ($p.Name -match '^pid_(\d+)_') { $procId = [int]$Matches[1] }
            $pn = '?'; try { $pn = (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { }
            $lines += ('프로그램 {0} (pid {1}): 전용 {2:N0} MiB' -f $pn, $procId, ([double]$p.DedicatedUsage / 1MB))
        }
        foreach ($g in @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction Stop | Where-Object { $_.UtilizationPercentage -gt 0 })) {
            $procId = 0; if ($g.Name -match '^pid_(\d+)_') { $procId = [int]$Matches[1] }
            $pn = '?'; try { $pn = (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { }
            $eng = ''; if ($g.Name -match '(engtype_[A-Za-z0-9]+)') { $eng = $Matches[1] }
            $lines += ('사용 중 {0} (pid {1}) {2}: {3} %' -f $pn, $procId, $eng, $g.UtilizationPercentage)
        }
    } catch { $lines += ('GPU 성능 카운터를 읽지 못했습니다: ' + $_.Exception.Message) }
    return ($lines -join "`n")
}

$Checks = New-Object System.Collections.ArrayList
function Check([string]$name, [string]$state, [string]$detail) {
    [void]$Checks.Add([ordered]@{ name = $name; state = $state; detail = $detail })
    $color = 'Gray'
    if ($state -eq '통과') { $color = 'Green' } elseif ($state -eq '경고') { $color = 'Yellow' } elseif ($state -eq '실패') { $color = 'Red' }
    Write-Host ('  [{0}] {1}: {2}' -f $state, $name, $detail) -ForegroundColor $color
}

Write-Host '=== GeulPU 교차 검증 — Vulkan (R1 · 32 문제) ==='
Write-Host '환경 검사 → 소스에서 빌드(2~4 분) → 모델 받기(8.1 GB, 없을 때만) → 생성(모듈마다 한 번, GPU 에 따라 5~20 분씩) → 비교. 창을 닫지 마세요.'
Write-Host ''

$exp = ReadJson (Join-Path $Here 'expected.json')

# ================= 1. 환경 검사 =================
Write-Host '--- 환경 검사 ---'
$EnvInfo = [ordered]@{ script = $ScriptVersion; checked_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'); gpu_layer = 'vulkan' }

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

# GPU — 윈도가 아는 모든 그래픽 장치(회사 · 드라이버 판 · 날짜 · PCI 의 회사 · 장치 번호). 장치마다의 고유번호는 적지 않는다
$gpus = @()
$gi = 0
foreach ($v in @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue)) {
    $ids = ''
    if ([string]$v.PNPDeviceID -match '(VEN_[0-9A-Fa-f]{4}&DEV_[0-9A-Fa-f]{4})') { $ids = $Matches[1] }
    $date = ''
    if ($v.DriverDate) { try { $date = ([datetime]$v.DriverDate).ToString('yyyy-MM-dd') } catch { } }
    $g = [ordered]@{ index = $gi; name = [string]$v.Name; vendor = [string]$v.AdapterCompatibility; driver_version = [string]$v.DriverVersion
                     driver_date = $date; pci_id = $ids; video_processor = [string]$v.VideoProcessor }
    $gpus += New-Object psobject -Property $g
    Check ('GPU ' + $gi) '정보' ('{0} · {1} · 드라이버 {2} ({3}) · {4}' -f $g.name, $g.vendor, $g.driver_version, $date, $ids)
    $gi++
}
$EnvInfo.gpus = $gpus
if ($gpus.Count -eq 0) { Check 'GPU' '경고' '윈도에서 그래픽 장치 목록을 읽지 못했습니다 (Vulkan 장치 검사에서 다시 봅니다)' }

$vkdll = Join-Path $env:SystemRoot 'System32\vulkan-1.dll'
$EnvInfo.vulkan_loader = $null
if (Test-Path -LiteralPath $vkdll) {
    $EnvInfo.vulkan_loader = (Get-Item -LiteralPath $vkdll).VersionInfo.FileVersion
    Check 'Vulkan 로더 (vulkan-1.dll)' '통과' $EnvInfo.vulkan_loader
}
else { Check 'Vulkan 로더 (vulkan-1.dll)' '실패' '그래픽 드라이버(AMD Adrenalin · NVIDIA · Intel)를 새로 설치해 주세요' }

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
# git 의 폴더 소유권 검사(safe.directory)는 외장 · 네트워크 · 다른 사용자가 만든 폴더에서 git 을 막는다 — 이 스크립트가 받은 저장소와
# 사용자가 받은 GeulPU 에만, 명령 하나마다 끈다
$EnvInfo.geulpu_commit = ((Native @('git', '-c', 'safe.directory=*', '-C', $Root, 'rev-parse', 'HEAD')) -join '')
$dirty = @(Native @('git', '-c', 'safe.directory=*', '-C', $Root, 'status', '--porcelain', '--', '호스트', '커널', '교차검증/runV.ps1', '교차검증/expected.json', '교차검증/requests.json')).Count
$EnvInfo.geulpu_modified = ($dirty -gt 0)
if (-not $EnvInfo.geulpu_commit) { Check 'GeulPU 저장소' '경고' 'git 저장소가 아닙니다(zip 으로 받았나요?) — git clone 으로 받으면 커밋이 기록됩니다' }
elseif ($dirty -gt 0) { Check 'GeulPU 저장소' '경고' ('커밋 {0} · 고친 파일이 있습니다 (빌드 해시가 다를 수 있음)' -f $EnvInfo.geulpu_commit) }
else { Check 'GeulPU 저장소' '통과' ('커밋 {0}' -f $EnvInfo.geulpu_commit) }

# 디스크 · 모델 — 폴더가 있는 드라이브의 종류(로컬 · 이동식 · 네트워크)와 파일 시스템도 적는다. 클라우드 · 가상 드라이브는 여유를 엉뚱하게 알린다
$ModelPath = $null
foreach ($c in @((Join-Path $Here $ModelName), (Join-Path $Work $ModelName))) { if (Test-Path -LiteralPath $c) { $ModelPath = $c; break } }
$freeGB = -1.0
$EnvInfo.drive = $null
try {
    $di = New-Object System.IO.DriveInfo ([IO.Path]::GetPathRoot($Here))
    $EnvInfo.drive = [ordered]@{ type = [string]$di.DriveType; format = [string]$di.DriveFormat }
    $freeGB = [Math]::Round([double]$di.AvailableFreeSpace / 1GB, 1)
} catch { }
if ($freeGB -lt 0 -or $freeGB -gt 1000000) { $freeGB = -1.0 }
$EnvInfo.disk_free_gb = $freeGB
$EnvInfo.model_present = [bool]$ModelPath
$freeText = '알 수 없음'
if ($freeGB -ge 0) { $freeText = ('{0} GB' -f $freeGB) }
if ($ModelPath) { Check '디스크 · 모델' '통과' ('여유 {0} · 모델 파일 있음' -f $freeText) }
elseif ($BuildOnly -or $freeGB -ge 10 -or $freeGB -lt 0) { Check '디스크 · 모델' '통과' ('여유 {0} · 모델을 받습니다 (8.1 GB)' -f $freeText) }
else { Check '디스크 · 모델' '실패' ('여유 {0} — 10 GB 이상이 필요합니다' -f $freeText) }
if ($EnvInfo.drive -and ($EnvInfo.drive.type -ne 'Fixed' -or $freeGB -lt 0)) {
    Check '폴더의 드라이브' '경고' ('{0} · {1} — 네트워크 · 클라우드 · 이동식 드라이브에서는 빌드 · git 이 실패할 수 있습니다. 로컬 디스크(예: C:\GeulPU)에서 실행해 주세요' -f $EnvInfo.drive.type, $EnvInfo.drive.format)
}

# ---- 결과 폴더(Vulkan 장치를 고른 뒤 그 이름을 붙인다) ----
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Out = Join-Path $Here ('result-V-' + $Stamp)
$LogDir = Join-Path $Out 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $Work -Force | Out-Null

function Finish([string]$headline, [string]$color) {
    # 기록을 남기고(사용자 이름 · 폴더 경로는 지운다) zip 으로 묶는다. 끝맺는 글(성공 · 중단의 까닭)도 결과.txt 로
    $EnvInfo.checks = $Checks
    $EnvInfo.result = $headline.Replace($Root, '<GeulPU>').Replace($env:USERPROFILE, '<home>')
    [IO.File]::WriteAllText((Join-Path $script:Out '결과.txt'), ($EnvInfo.result + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    $EnvInfo | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $script:Out 'environment.json') -Encoding UTF8
    Get-ChildItem -LiteralPath $script:Out -Recurse -Filter *.log | ForEach-Object {
        $t = [IO.File]::ReadAllText($_.FullName)
        $t = $t.Replace($Root, '<GeulPU>').Replace($env:USERPROFILE, '<home>')
        [IO.File]::WriteAllText($_.FullName, $t)
    }
    $zip = $script:Out + '.zip'
    Compress-Archive -Path (Join-Path $script:Out '*') -DestinationPath $zip -Force
    Write-Host ''
    Write-Host $headline -ForegroundColor $color
    Write-Host ('이 파일을 보내 주세요: ' + $zip)
}

# 자기 진단(32단계 · 34단계): 이 기기의 바닥(메모리 읽기 대역 · 정수 텐서 최고치 — 협력 행렬이 있으면 그것으로)을 그 자리에서 재고, 7B 엔진의
# 커널 종류마다 시간과 바닥 대비를 적는다. 엔진이 이 기기에서 후보마다 잰 판과 고른 판, 31단계 후보 대 모든 후보의 번갈아 잰 비도 적는다.
function RunDiag([string]$modSpvs, [string]$diagSpvs) {
    Write-Host ''
    Say '자기 진단: 이 기기의 바닥과 커널마다의 바닥 대비를 잽니다 (GPU 에 따라 1~6 분)...'
    [IO.File]::WriteAllText((Join-Path $script:Out 'diag-gpu-state.txt'), ((GpuState) + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    $code = Tool $diagExe @($diagSpvs, (Join-Path $script:Out 'diag.json'), $ModelPath, $modSpvs) $Work 'diag'
    if ($code -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $script:Out 'diag.json'))) { Check '자기 진단' '경고' '실패 — logs 의 diag.log 를 보내 주세요'; return }
    try { $d = ReadJson (Join-Path $script:Out 'diag.json') } catch { Check '자기 진단' '경고' 'diag.json 을 읽지 못했습니다'; return }
    $EnvInfo.diag = [ordered]@{ module = (Split-Path -Leaf $modSpvs); read_bandwidth_gbs = $d.'바닥'.'읽기대역_GBs'; int8_tops = $d.'바닥'.'정수텐서_TOPS';
                                coop_tops = $d.'바닥'.'협력_TOPS'; emulated_tops = $d.'바닥'.'흉내텐서_TOPS';
                                ab8_ratio = $d.'번갈아_여덟슬롯'.'비_가운데'; ab4_ratio = $d.'번갈아_네슬롯'.'비_가운데' }
    $line = '대역 {0:N1} GB/s · 정수 텐서 {1:N1} TOPS' -f $d.'바닥'.'읽기대역_GBs', $d.'바닥'.'정수텐서_TOPS'
    if ([double]$d.'바닥'.'협력_TOPS' -gt 0) { $line += (' (협력 행렬 — 흉내 {0:N1})' -f $d.'바닥'.'흉내텐서_TOPS') }
    foreach ($k in @('생성 문맥 1024', '슬롯 여덟 걸음 문맥 2048', '프롬프트 2048')) {
        $c = $d.'커널'.$k
        if ($c) { $line += (' · {0} {1:N2} 배' -f $k, $c.'배') }
    }
    if ($d.'번갈아_여덟슬롯') { $line += (' · 32/31 슬롯 여덟 {0:N3} · 넷 {1:N3}' -f $d.'번갈아_여덟슬롯'.'비_가운데', $d.'번갈아_네슬롯'.'비_가운데') }
    Check '자기 진단' '통과' $line
}

# 35단계 — 속도만(-SpeedOnly): 자기 진단을 판마다(지금 · 34m) 번갈아 돌려 칸마다의 시간을 모은다. 칸: 한 줄 생성(문맥 1024), 여덟 줄(문맥
# 2048 — 합 · 어텐션), 프롬프트 512 · 2048(합 · 어텐션), 슬롯 여덟의 생성 걸음(서버의 표 판 그래프 — 모든 후보로 고른 판, 50 걸음씩 세 번의
# 가운데). 같은 판을 여러 바퀴 돌았으면 바퀴마다의 가운데 값을 쓴다
function Median([double[]]$xs) {
    $s = @($xs | Sort-Object)
    if ($s.Count -eq 0) { return [double]::NaN }
    if ($s.Count % 2 -eq 1) { return $s[($s.Count - 1) / 2] }
    return ($s[$s.Count / 2 - 1] + $s[$s.Count / 2]) / 2.0
}
function SpeedRow($d) {
    $k = $d.'커널'
    $row = [ordered]@{}
    $row['생성 문맥 1024'] = [double]$k.'생성 문맥 1024'.'합_ms'
    $row['여덟 줄 문맥 2048'] = [double]$k.'여덟 줄 문맥 2048'.'합_ms'
    $row['여덟 줄 — 어텐션'] = [double]$k.'여덟 줄 문맥 2048'.'종류'.'어텐션'.'ms'
    $row['프롬프트 512'] = [double]$k.'프롬프트 512'.'합_ms'
    $row['프롬프트 512 — 어텐션'] = [double]$k.'프롬프트 512'.'종류'.'어텐션'.'ms'
    $row['프롬프트 2048'] = [double]$k.'프롬프트 2048'.'합_ms'
    $row['프롬프트 2048 — 어텐션'] = [double]$k.'프롬프트 2048'.'종류'.'어텐션'.'ms'
    if ($d.'번갈아_여덟슬롯') { $row['슬롯 여덟 걸음(그래프)'] = Median @($d.'번갈아_여덟슬롯'.'걸음_ms_32' | ForEach-Object { [double]$_ }) }
    return $row
}
function RunSpeed($plan) {
    # $plan: [label, 모듈, 진단 커널] 의 차례(번갈아). 결과: speed/<label>-<n>.json 과 속도.txt · 속도.json
    $sd = Join-Path $script:Out 'speed'
    New-Item -ItemType Directory -Path $sd -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $script:Out 'diag-gpu-state.txt'), ((GpuState) + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    $rows = @{}
    $n = 0
    foreach ($p in $plan) {
        $n++
        $label = $p[0]
        Say ('속도 {0}/{1}: {2} (자기 진단, GPU 에 따라 1~6 분)...' -f $n, $plan.Count, $label)
        $j = Join-Path $sd ('{0}-{1}.json' -f $label, $n)
        $code = Tool $diagExe @($p[2], $j, $ModelPath, $p[1]) $Work ('speed-{0}-{1}' -f $label, $n)
        if ($code -ne 0 -or -not (Test-Path -LiteralPath $j)) { Check ('속도 — ' + $label) '경고' ('실패 — logs 의 speed-{0}-{1}.log 를 보내 주세요' -f $label, $n); continue }
        try { $r = SpeedRow (ReadJson $j) } catch { Check ('속도 — ' + $label) '경고' '진단 결과를 읽지 못했습니다'; continue }
        if (-not $rows.ContainsKey($label)) { $rows[$label] = @() }
        $rows[$label] += , $r
    }
    # 판마다 칸의 가운데 값
    $out = [ordered]@{}
    $labels = @()
    foreach ($p in $plan) { if ($labels -notcontains $p[0]) { $labels += $p[0] } }
    foreach ($label in $labels) {
        if (-not $rows.ContainsKey($label)) { continue }
        $m = [ordered]@{}
        foreach ($key in $rows[$label][0].Keys) { $m[$key] = [Math]::Round((Median @($rows[$label] | ForEach-Object { $_[$key] })), 3) }
        $m['바퀴'] = $rows[$label].Count
        $out[$label] = $m
    }
    $EnvInfo.speed = $out
    $out | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $script:Out '속도.json') -Encoding UTF8
    # 글 — 판마다 칸, 그리고 지금 ÷ 34m
    $lines = @('칸(ms)' + (($labels | ForEach-Object { ' | ' + $_ }) -join ''))
    $keys = @()
    foreach ($label in $labels) { if ($out.Contains($label)) { $keys = @($out[$label].Keys | Where-Object { $_ -ne '바퀴' }); break } }
    foreach ($key in $keys) {
        $cells = @()
        foreach ($label in $labels) { if ($out.Contains($label)) { $cells += ('{0:N2}' -f $out[$label][$key]) } else { $cells += '-' } }
        $lines += ($key + ' | ' + ($cells -join ' | '))
    }
    $pairs = @(@('새협력', '옛협력'), @('새기본', '옛기본'))
    foreach ($pr in $pairs) {
        if ($out.Contains($pr[0]) -and $out.Contains($pr[1])) {
            $lines += ''
            $lines += ('{0} ÷ {1}:' -f $pr[0], $pr[1])
            foreach ($key in $keys) { $lines += ('  {0} {1:N3}' -f $key, ($out[$pr[0]][$key] / $out[$pr[1]][$key])) }
        }
    }
    [IO.File]::WriteAllText((Join-Path $script:Out '속도.txt'), (($lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    foreach ($l in $lines) { Write-Host $l }
    if ($out.Contains('새협력') -and $out.Contains('옛협력')) {
        $a = $out['새협력']; $b = $out['옛협력']
        Check '속도 — 협력 모듈' '정보' ('슬롯 여덟 걸음 {0:N1} → {1:N1} ms · 여덟 줄 {2:N1} → {3:N1} ms · 프롬프트 2048 {4:N0} → {5:N0} ms (34m → 지금)' -f `
            $b['슬롯 여덟 걸음(그래프)'], $a['슬롯 여덟 걸음(그래프)'], $b['여덟 줄 문맥 2048'], $a['여덟 줄 문맥 2048'], $b['프롬프트 2048'], $a['프롬프트 2048'])
    }
}

$failed = @($Checks | Where-Object { $_.state -eq '실패' }).Count
if ($failed -gt 0) {
    Finish ('환경 검사에서 실패 {0} 건 — 위 내용을 확인해 주세요.' -f $failed) 'Red'
    exit 1
}

# ================= 2. 소스에서 빌드 =================
Write-Host ''
Write-Host '--- 소스에서 빌드 (기준 PC 의 해시와 대조) ---'
$Build = [ordered]@{}
$want = $exp.build
$wantV = $exp.build_vulkan
if (-not $wantV) { Check '기준 해시 (Vulkan)' '경고' 'expected.json 에 build_vulkan 이 없습니다 — 저장소를 새로 받아 주세요' }
function BuildCheck([string]$name, [string]$path, [string]$wantSha) {
    if (-not (Test-Path -LiteralPath $path)) { Check $name '실패' '만들어지지 않았습니다 (logs 폴더를 보내 주세요)'; return $false }
    $s = FileSha $path
    $Build[$name] = $s
    if (-not $wantSha) { Check $name '경고' ('기준 해시 없음 ' + $s.Substring(0, 12)) }
    elseif ($s -eq $wantSha) { Check $name '통과' ('기준과 같음 ' + $s.Substring(0, 12)) }
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
# git 의 출력은 logs 의 git-*.log 로. 받다 만 저장소(끊긴 clone)는 지우고 한 번 더 받는다
$gitExe = (Get-Command git -ErrorAction SilentlyContinue).Source
function GitRun([string[]]$argv, [string]$name) { return (Tool $gitExe (@('-c', 'safe.directory=*') + $argv) $Work ('git-' + $name)) }
function GeulRepoReady([string]$tag) {
    if (-not (Test-Path -LiteralPath (Join-Path $GeulDir '.git'))) {
        if (Test-Path -LiteralPath $GeulDir) { Remove-Item -LiteralPath $GeulDir -Recurse -Force -ErrorAction SilentlyContinue }
        Say '글 저장소를 받습니다 (약 35 MB)...'
        $c = GitRun @('clone', '--quiet', $GeulRepo, $GeulDir) ('clone' + $tag)
        if ($c -ne 0) { return $false }
    }
    $c = GitRun @('-C', $GeulDir, '-c', 'advice.detachedHead=false', 'checkout', '--quiet', $pin) ('checkout' + $tag)
    if ($c -ne 0) {
        $null = GitRun @('-C', $GeulDir, 'fetch', '--quiet', 'origin') ('fetch' + $tag)
        $null = GitRun @('-C', $GeulDir, '-c', 'advice.detachedHead=false', 'checkout', '--quiet', $pin) ('checkout-after-fetch' + $tag)
    }
    $h = ((Native @('git', '-c', 'safe.directory=*', '-C', $GeulDir, 'rev-parse', 'HEAD')) -join '')
    return ($h -eq $pin)
}
if (-not (GeulRepoReady '')) {
    Say '글 저장소를 지우고 다시 받습니다...'
    Remove-Item -LiteralPath $GeulDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (GeulRepoReady '-2')) { Fail ('글 저장소(github.com/wwoosshh/geul-lang)를 고정 커밋 ' + $pin + ' 으로 받지 못했습니다 — logs 의 git-*.log 를 보내 주세요.') }
}
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

# d. Vulkan 장치 검사 — 장치 정보 도구(호스트/장치V.gl)로 모든 Vulkan 장치의 속성 · 기능 · 협력 행렬 모양을 적고, 엔진이 고르는 장치를
#    GeulPU 가 돌릴 수 있는지(서브그룹 32 · 공유 메모리 48 KB · 기능 · 확장)와 SPIR-V 뒷단에 줄 협력 행렬 모양을 정한다
Write-Host ''
Write-Host '--- Vulkan 장치 검사 ---'
$devExe = Join-Path $Work 'device_vulkan.exe'
$code = Tool $comp @('호스트/장치V.gl', '-o', $devExe) $Root 'build-device-tool'
if ($code -ne 0) { Fail '장치 정보 도구 빌드 실패. logs 폴더를 보내 주세요.' }
if ($Device) { [Environment]::SetEnvironmentVariable('GEULPU_VULKAN', $Device, 'Process') }
else { [Environment]::SetEnvironmentVariable('GEULPU_VULKAN', $null, 'Process') }
$devJson = Join-Path $Out 'vulkan-devices.json'
$code = Tool $devExe @($devJson) $Work 'vulkan-devices'
if (-not (Test-Path -LiteralPath $devJson)) { Fail 'Vulkan 장치를 읽지 못했습니다 — logs 의 vulkan-devices.log 를 보내 주세요.' }
$vk = ReadJson $devJson
$EnvInfo.vulkan = $vk
$sel = $null
foreach ($d in @($vk.'장치들')) {
    $mark = ''
    if ($d.'고름') { $sel = $d; $mark = ' ← 이것을 씀' }
    $coop = '없음'
    if ($d.'권하는_협력') { $coop = [string]$d.'권하는_협력' } elseif ($d.'협력기능') { $coop = '정수 모양 없음' }
    Check ('Vulkan 장치 ' + $d.'번호') '정보' ('{0} · Vulkan {1} · 드라이버 {2} {3} · 서브그룹 {4}~{5} · 공유 {6} KB · 장치 메모리 {7:N1} GB · 협력 행렬 {8}{9}' -f `
        $d.'이름', $d.'API', $d.'드라이버'.'이름', $d.'드라이버'.'정보', $d.'서브그룹'.'최소', $d.'서브그룹'.'최대', ([int]$d.'공유메모리' / 1024),
        ([double]$d.'장치메모리' / 1e9), $coop, $mark)
}
if (-not $sel) { Fail ('Vulkan 장치를 고르지 못했습니다 (GEULPU_VULKAN=' + $Device + ').') }
$gpu = [string]$sel.'이름'
[Environment]::SetEnvironmentVariable('GEULPU_VULKAN', $gpu, 'Process')      # 서버 · 진단도 같은 장치(이름의 일부로 고른다)
# 결과 폴더에 장치 이름을 붙인다(못 바꾸면 그대로)
$safeGpu = (($gpu -replace '[^A-Za-z0-9]+', '-').Trim('-'))
$newOut = Join-Path $Here ('result-V-' + $safeGpu + '-' + $Stamp)
try { Rename-Item -LiteralPath $Out -NewName (Split-Path -Leaf $newOut); $Out = $newOut; $LogDir = Join-Path $Out 'logs'; $devJson = Join-Path $Out 'vulkan-devices.json' } catch { }
if ($sel.'돌릴수있음') { Check 'GeulPU 가 쓰는 기능' '통과' ($gpu + ' — 엔진이 요구하는 것이 모두 있습니다') }
else { foreach ($m in @($sel.'막는것')) { Check 'GeulPU 가 쓰는 기능' '실패' ([string]$m) } }
foreach ($w in @($sel.'경고')) { Check 'Vulkan 장치 경고' '경고' ([string]$w) }
$Shape = [string]$vk.'고른_권하는_협력'
$useCoop = ($Shape -ne '') -and ($Modules -ne 'base')
$useBase = ($Modules -ne 'coop')
if ($Modules -eq 'coop' -and $Shape -eq '') { Check '협력 행렬' '실패' '-Modules coop 인데 이 장치에 정수 협력 행렬이 없습니다' }
elseif ($Shape) { Check '협력 행렬' '통과' ('SPIR-V 뒷단 --협력 ' + $Shape + ' (부호 있는 8 비트 × 8 비트 → 32 비트)') }
else { Check '협력 행렬' '정보' '없음 — 텐서곱을 흉내 내는 기본 모듈로만 돕니다' }
$EnvInfo.coop_shape = $Shape
# 34단계 — 모듈 판: 공유 메모리 48 KB · 푸시 상수 136 바이트 이상이면 보통, 아니면 공유32(커널생성 --공유32 — AMD · Intel 의 Vulkan 은
# 공유 32 KB). 한 번 할당의 한도를 넘는 가중치는 엔진이 층마다 따로 잡는다
$Variant = [string]$vk.'고른_모듈판'
if ($Variant -ne '공유32') { $Variant = '보통' }
$EnvInfo.module_variant = $Variant
if ($Variant -eq '공유32') {
    Check '모듈 판' '정보' ('공유32 — 공유 메모리 {0} KB · 푸시 상수 {1} 바이트 장치의 판(생성 줄 판 · 어텐션을 32 KB 안으로, 셈은 같다)' -f ([int]$sel.'공유메모리' / 1024), $sel.'푸시상수')
}
else { Check '모듈 판' '정보' '보통' }
if ($sel.'할당나눔') { Check '한 번 할당 한도' '정보' ('{0:N2} GB — 7B 가중치(gate·up 4.04 GB)를 층마다 따로 잡습니다' -f ([double]$sel.'실할당한도' / 1e9)) }
$emu = @()
foreach ($k in @('GEULPU_VULKAN_SHARED', 'GEULPU_VULKAN_PUSH', 'GEULPU_VULKAN_ALLOC')) {
    $v = [Environment]::GetEnvironmentVariable($k, 'Process')
    if ($v) { $emu += ($k + '=' + $v) }
}
if ($emu.Count -gt 0) { $EnvInfo.vulkan_emulation = ($emu -join ' '); Check 'Vulkan 한도 흉내' '경고' (($emu -join ' ') + ' — 시험용(다른 장치의 한도를 흉내 냄)') }
$vram = [int][Math]::Floor([double]$sel.'장치메모리' / 1MB)
$slotsList = @(8, 2, 1)
if ($vram -ge 11500) { Check 'VRAM' '통과' ('{0} MiB — 슬롯 8' -f $vram) }
elseif ($vram -ge 9800) { Check 'VRAM' '경고' ('{0} MiB — 슬롯 2 로 줄여 실행 (느림)' -f $vram); $slotsList = @(2, 1) }
else { Check 'VRAM' '실패' ('{0} MiB — 모델(8.1 GB)이 들어가지 않습니다. 12 GB 이상이 필요합니다' -f $vram) }
$used = GpuMemUsedMiB
if ($used -lt 0) { Check 'VRAM 사용 중' '정보' '윈도의 GPU 성능 카운터를 읽지 못했습니다' }
elseif ($used -gt 1500) { Check 'VRAM 사용 중' '경고' ('{0} MiB 를 다른 프로그램이 쓰고 있습니다. 게임·브라우저를 닫으면 안전합니다' -f $used) }
else { Check 'VRAM 사용 중' '통과' ('{0} MiB' -f $used) }
$failed = @($Checks | Where-Object { $_.state -eq '실패' }).Count
if ($failed -gt 0) { Fail ('이 GPU 에서는 GeulPU(Vulkan)를 돌릴 수 없습니다 — 실패 {0} 건 (위 내용과 vulkan-devices.json)' -f $failed) }

# e. SPIR-V 뒷단
Write-Host ''
Say 'SPIR-V 뒷단을 빌드합니다...'
$spvBackend = Join-Path $Work 'spirv_backend.exe'
$code = Tool $comp @('research/gpu/자체SPIRV/SPIRV.gl', '-o', $spvBackend) $GeulDir 'build-spirv-backend'
if ($code -ne 0) { Fail 'SPIR-V 뒷단 빌드 실패.' }
[void](BuildCheck 'SPIR-V 뒷단' $spvBackend $wantV.spirv_backend)

# f. 서버(Vulkan) — 저장소의 호스트 · 커널을 work\src 에 복사하고 토크나이저 두 곳만 고친다(토크나이저_R1.diff 와 같은 내용, run.ps1 과 같다)
Say '서버(Vulkan)를 빌드합니다 (토크나이저 두 곳만 이 모델에 맞춤)...'
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
# 36단계부터 저장소의 토크나이저에 이 덧댐이 들어 있다 — 그러면 그대로 둔다(빌드는 같은 바이트)
if ($t.Contains($new1) -and $t.Contains($new2)) { }
elseif ($t.Contains($old1) -and $t.Contains($old2)) { $t = $t.Replace($old1, $new1).Replace($old2, $new2) }
else { Fail '토크나이저.gl 이 예상과 달라 고칠 수 없습니다 (저장소 판을 확인해 주세요).' }
[IO.File]::WriteAllText($tk, $t, (New-Object System.Text.UTF8Encoding($false)))
$server = Join-Path $Work 'server_r1_vulkan.exe'
$code = Tool $comp @('호스트/서버V.gl', '-o', $server) $Src 'build-server-vulkan'
if ($code -ne 0) { Fail '서버(Vulkan) 빌드 실패.' }
[void](BuildCheck '서버 (R1 · Vulkan)' $server $wantV.server_r1_vulkan)

# g. 생성기 → 7B Q8_0 모듈 둘 → SPIR-V 묶음. 기본 모듈은 run.ps1 의 모듈 소스와 같은 파일(텐서곱을 서브그룹 셔플 · 정수 내적으로 흉내),
#    협력 모듈(--협력)은 타일 판의 정수 곱을 협력 행렬로 — 모양은 장치가 받는 것(--협력 MxNxK). 정수 곱의 합은 정확해 어느 모양이든 같은 비트
Say '커널 생성기 · 7B 모듈 · SPIR-V 묶음을 만듭니다 (1~2 분)...'
$gen = Join-Path $Work 'kernel_gen.exe'
$code = Tool $comp @('커널/커널생성.gl', '-o', $gen) $Root 'build-generator'
if ($code -ne 0) { Fail '커널 생성기 빌드 실패.' }
[void](BuildCheck '커널 생성기' $gen $want.generator)
# 34단계 — 공유32 판(공유 메모리 32 KB · 푸시 상수 128 바이트 장치): 생성기 --공유32, 파일 이름 · 기준 해시 열쇠에 _32
$vArg = @()
$vSuf = ''
$vName = ''
if ($Variant -eq '공유32') { $vArg = @('--공유32'); $vSuf = '_32'; $vName = '공유32 · ' }
$wantSrc = $want.module_source
$wantSpv = $wantV.module_spvs
$wantCoopSrc = $wantV.module_source_coop
$wantCoopSpv = $wantV.module_spvs_coop
if ($Variant -eq '공유32') { $wantSrc = $wantV.module_source_32; $wantSpv = $wantV.module_spvs_32; $wantCoopSrc = $wantV.module_source_coop_32; $wantCoopSpv = $wantV.module_spvs_coop_32 }
$modGl = Join-Path $Work ('qwen2Q8_7b' + $vSuf + '.gl')
$code = Tool $gen (@('qwen2Q8_7b', $modGl) + $vArg) $Root 'generate-module'
if ($code -ne 0) { Fail '모듈 소스 생성 실패.' }
[void](BuildCheck ('7B 모듈 소스' + $(if ($vSuf) { ' (공유32)' } else { '' })) $modGl $wantSrc)
$baseSpvs = Join-Path $Work ('q8_7b' + $vSuf + '.spvs')
$code = Tool $spvBackend @($modGl, '-o', $baseSpvs) $Root 'build-module-spirv'
if ($code -ne 0) { Fail '모듈 SPIR-V 빌드 실패.' }
[void](BuildCheck ('7B 모듈 SPIR-V' + $(if ($vSuf) { ' (공유32)' } else { '' })) $baseSpvs $wantSpv)
$coopSpvs = $null
if ($useCoop) {
    $coopGl = Join-Path $Work ('qwen2Q8_7b_coop' + $vSuf + '.gl')
    $code = Tool $gen (@('qwen2Q8_7b', $coopGl, '--협력') + $vArg) $Root 'generate-module-coop'
    if ($code -ne 0) { Fail '협력 모듈 소스 생성 실패.' }
    [void](BuildCheck ('7B 협력 모듈 소스' + $(if ($vSuf) { ' (공유32)' } else { '' })) $coopGl $wantCoopSrc)
    $coopSpvs = Join-Path $Work ('q8_7b_coop' + $vSuf + '_' + $Shape + '.spvs')
    $code = Tool $spvBackend @($coopGl, '-o', $coopSpvs, '--협력', $Shape) $Root 'build-module-coop-spirv'
    if ($code -ne 0) { Fail '협력 모듈 SPIR-V 빌드 실패.' }
    $wantCoop = $null
    if ($wantCoopSpv) { $wantCoop = $wantCoopSpv.$Shape }
    [void](BuildCheck ('7B 협력 모듈 SPIR-V (' + $vName + $Shape + ')') $coopSpvs $wantCoop)
}
# 35단계 — 속도만(-SpeedOnly)이고 공유32 장치이면 34단계(34m)의 공유32 모듈도(생성기 --35없이 — 34m 과 바이트까지 같다) 만들어 번갈아 잰다
$baseSpvsOld = $null
$coopSpvsOld = $null
if ($SpeedOnly -and $Variant -eq '공유32') {
    $oldGl = Join-Path $Work 'qwen2Q8_7b_32_34m.gl'
    $code = Tool $gen @('qwen2Q8_7b', $oldGl, '--공유32', '--35없이') $Root 'generate-module-34m'
    if ($code -ne 0) { Fail '34m 모듈 소스 생성 실패.' }
    [void](BuildCheck '7B 모듈 소스 (공유32 · 34m)' $oldGl $wantV.module_source_32_34m)
    $baseSpvsOld = Join-Path $Work 'q8_7b_32_34m.spvs'
    $code = Tool $spvBackend @($oldGl, '-o', $baseSpvsOld) $Root 'build-module-spirv-34m'
    if ($code -ne 0) { Fail '34m 모듈 SPIR-V 빌드 실패.' }
    [void](BuildCheck '7B 모듈 SPIR-V (공유32 · 34m)' $baseSpvsOld $wantV.module_spvs_32_34m)
    if ($useCoop) {
        $oldCoopGl = Join-Path $Work 'qwen2Q8_7b_coop_32_34m.gl'
        $code = Tool $gen @('qwen2Q8_7b', $oldCoopGl, '--협력', '--공유32', '--35없이') $Root 'generate-module-coop-34m'
        if ($code -ne 0) { Fail '34m 협력 모듈 소스 생성 실패.' }
        [void](BuildCheck '7B 협력 모듈 소스 (공유32 · 34m)' $oldCoopGl $wantV.module_source_coop_32_34m)
        $coopSpvsOld = Join-Path $Work ('q8_7b_coop_32_34m_' + $Shape + '.spvs')
        $code = Tool $spvBackend @($oldCoopGl, '-o', $coopSpvsOld, '--협력', $Shape) $Root 'build-module-coop-spirv-34m'
        if ($code -ne 0) { Fail '34m 협력 모듈 SPIR-V 빌드 실패.' }
        $wantOld = $null
        if ($wantV.module_spvs_coop_32_34m) { $wantOld = $wantV.module_spvs_coop_32_34m.$Shape }
        [void](BuildCheck ('7B 협력 모듈 SPIR-V (공유32 · 34m · ' + $Shape + ')') $coopSpvsOld $wantOld)
    }
}

# h. 자기 진단 도구 — 진단 커널(SPIR-V: 협력 행렬이 있으면 커널/진단협력.gl, 없으면 커널/진단V.gl) · 진단 프로그램(호스트/진단V.gl)
Say '자기 진단 도구를 빌드합니다...'
$diagSpvsBase = Join-Path $Work 'diag_vulkan.spvs'
$code = Tool $spvBackend @('커널/진단V.gl', '-o', $diagSpvsBase) $Root 'build-diag-spirv'
if ($code -ne 0) { Fail '진단 커널 빌드 실패.' }
$diagSpvsCoop = $null
if ($useCoop) {
    $diagSpvsCoop = Join-Path $Work ('diag_vulkan_coop_' + $Shape + '.spvs')
    $code = Tool $spvBackend @('커널/진단협력.gl', '-o', $diagSpvsCoop, '--협력', $Shape) $Root 'build-diag-coop-spirv'
    if ($code -ne 0) { Fail '진단 커널(협력) 빌드 실패.' }
}
$diagExe = Join-Path $Work 'diag_vulkan.exe'
$code = Tool $comp @('호스트/진단V.gl', '-o', $diagExe) $Root 'build-diag'
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

if ($SpeedOnly) {
    # 판마다 번갈아: 협력 모듈은 지금 · 34m · 34m · 지금(두 바퀴), 기본 모듈은 지금 · 34m(한 바퀴). 보통 장치는 지금 판만
    $plan = @()
    $ab = ($Variant -eq '공유32')
    if ($useCoop) {
        $plan += , @('새협력', $coopSpvs, $diagSpvsCoop)
        if ($ab) {
            $plan += , @('옛협력', $coopSpvsOld, $diagSpvsCoop)
            $plan += , @('옛협력', $coopSpvsOld, $diagSpvsCoop)
            $plan += , @('새협력', $coopSpvs, $diagSpvsCoop)
        }
    }
    if ($useBase) {
        $plan += , @('새기본', $baseSpvs, $diagSpvsBase)
        if ($ab) { $plan += , @('옛기본', $baseSpvsOld, $diagSpvsBase) }
    }
    RunSpeed $plan
    Finish '속도를 쟀습니다 (-SpeedOnly — 생성은 건너뜀). 속도.txt 에 판마다의 시간과 비가 있습니다.' 'Green'
    exit 0
}

if ($DiagOnly) {
    if ($useCoop) { RunDiag $coopSpvs $diagSpvsCoop } else { RunDiag $baseSpvs $diagSpvsBase }
    Finish '자기 진단을 마쳤습니다 (-DiagOnly — 생성은 건너뜀).' 'Green'
    exit 0
}

# ================= 4 · 5. 모듈마다: 서버를 띄우고(127.0.0.1 에서만) 32 문제를 한꺼번에 보낸 뒤 기준 PC 의 출력과 견준다 =================
[System.Net.ServicePointManager]::DefaultConnectionLimit = 64
[System.Net.ServicePointManager]::Expect100Continue = $false
Add-Type -AssemblyName System.Net.Http
$reqs = ReadJson (Join-Path $Here 'requests.json')

function CompareRun($results) {
    # run.ps1 과 같은 비교 — 출력 글의 SHA-256 이 기준과 같은가, 다르면 처음 갈린 글자
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
    return @{ same = $same; rows = $rows }
}

function RunModule([string]$tag, [string]$label, [string]$spvs) {
    $run = [ordered]@{ module = $tag; label = $label; spvs = (Split-Path -Leaf $spvs); spvs_sha256 = (FileSha $spvs); dir = $tag; slots = 0
                       ready_seconds = 0.0; generate_minutes = 0.0; same = 0; total = @($exp.items).Count; error = ''; items = @() }
    $respDir = Join-Path $script:Out (Join-Path $tag 'responses')
    New-Item -ItemType Directory -Path $respDir -Force | Out-Null
    $results = @{}
    $proc = $null
    $client = $null
    try {
        $ok = $false
        foreach ($s in $slotsList) {
            $argList = @((Quote $ModelPath), '--ptx', (Quote $spvs), '--슬롯', "$s", '--문맥', "$Context", '--포트', "$Port")
            Say ('[{0}] 서버를 띄웁니다 (슬롯 {1} — 처음에는 커널을 컴파일하고 판을 재느라 몇 분 걸릴 수 있음)...' -f $label, $s)
            $proc = Start-Process -FilePath $server -ArgumentList $argList -PassThru -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $script:LogDir ('server-{0}-{1}.log' -f $tag, $s)) -RedirectStandardError (Join-Path $script:LogDir ('server-{0}-{1}-err.log' -f $tag, $s))
            $t0 = Get-Date
            while (((Get-Date) - $t0).TotalMinutes -lt 20) {
                if ($proc.HasExited) { break }
                try {
                    $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:{0}/health' -f $Port) -TimeoutSec 3
                    if ($r.StatusCode -eq 200) { $ok = $true; break }
                } catch { }
                Start-Sleep -Seconds 1
            }
            if ($ok) { $run.slots = $s; $run.ready_seconds = [Math]::Round(((Get-Date) - $t0).TotalSeconds, 1); break }
            if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
            Say ('[{0}] 슬롯 {1} 로는 서버가 뜨지 않았습니다. 더 적은 슬롯으로 다시 시도합니다.' -f $label, $s)
        }
        if (-not $ok) { $run.error = '서버를 띄우지 못했습니다 (logs 의 server-' + $tag + '-*.log)'; Check ('생성 — ' + $label) '실패' $run.error; return $run }
        Say ('[{0}] 서버 준비 완료 (슬롯 {1}, {2:N0} 초).' -f $label, $run.slots, $run.ready_seconds)
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.UseProxy = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.Timeout = [TimeSpan]::FromHours(8)
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
            Say ('[{0}] 생성 중: {1}/{2} 완료 · {3:N1} 분 경과' -f $label, $done, $tasks.Count, ((Get-Date) - $tg).TotalMinutes)
            if ($done -eq $tasks.Count) { break }
            if ($proc.HasExited) { $run.error = '생성 도중에 서버가 끝났습니다 (logs 의 server-' + $tag + '-*.log)'; break }
            Start-Sleep -Seconds 30
        }
        $run.generate_minutes = [Math]::Round(((Get-Date) - $tg).TotalMinutes, 1)
        foreach ($id in ($tasks.Keys | Sort-Object)) {
            $tk2 = $tasks[$id]
            if (-not $tk2.IsCompleted) { continue }
            if ($tk2.IsFaulted -or $tk2.IsCanceled) { $results[$id] = @{ status = 0; error = [string]$tk2.Exception }; continue }
            $resp = $tk2.Result
            $bytes = $resp.Content.ReadAsByteArrayAsync().Result
            [IO.File]::WriteAllBytes((Join-Path $respDir ('{0:D2}.json' -f $id)), $bytes)
            $results[$id] = @{ status = [int]$resp.StatusCode; json = ([Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json) }
        }
    }
    finally {
        if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
        if ($client) { $client.Dispose() }
    }
    $c = CompareRun $results
    $run.same = $c.same
    $run.items = $c.rows
    $state = '경고'
    if ($run.same -eq $run.total) { $state = '통과' }
    $msg = ('{0}/{1} 문제가 기준 PC 와 같은 출력 · 슬롯 {2} · 생성 {3:N1} 분' -f $run.same, $run.total, $run.slots, $run.generate_minutes)
    if ($run.error) { $msg += (' — ' + $run.error) }
    Check ('생성 — ' + $label) $state $msg
    return $run
}

$Runs = @()
$coopStarted = $false
if ($useCoop) {
    Write-Host ''
    $r1 = RunModule 'coop' ('협력 행렬 모듈 ' + $Shape) $coopSpvs
    $coopStarted = ($r1.slots -gt 0)
    $Runs += New-Object psobject -Property $r1
}
if ($useBase) {
    Write-Host ''
    $r2 = RunModule 'base' '기본 모듈' $baseSpvs
    $Runs += New-Object psobject -Property $r2
}

$total = @($exp.items).Count
$summary = [ordered]@{ environment = $EnvInfo; build = $Build; runs = $Runs; reference = $exp.reference; total = $total; date = $Stamp }
$summary | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $Out 'summary.json') -Encoding UTF8

# ================= 6. 자기 진단 =================
if ($coopStarted) { RunDiag $coopSpvs $diagSpvsCoop } else { RunDiag $baseSpvs $diagSpvsBase }

$parts = @()
$allSame = ($Runs.Count -gt 0)
foreach ($r in $Runs) {
    if ($r.slots -eq 0) { $parts += ('{0} 서버가 뜨지 않음' -f $r.label) }
    else { $parts += ('{0} {1}/{2}' -f $r.label, $r.same, $r.total) }
    if ($r.same -ne $r.total) { $allSame = $false }
}
if ($allSame) { Finish ('결과: 32 문제 모두 기준 PC(NVIDIA · CUDA)와 똑같은 출력입니다 — ' + ($parts -join ' · ')) 'Green' }
else { Finish ('결과: 기준 PC 와 다른 출력이 있거나 끝나지 못한 실행이 있습니다 — ' + ($parts -join ' · ')) 'Yellow' }
