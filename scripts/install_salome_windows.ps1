param(
  [string]$Version = "9.16.0",
  [string]$InstallRoot = "C:\SAL"
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Version -ne "9.16.0") { throw 'Only SALOME 9.16.0 is approved for this smoke test' }
$os = (Get-CimInstance Win32_OperatingSystem).Caption
if ($os -notmatch 'Windows') { throw 'Windows test machine required' }
if ((Get-PSDrive C).Free -lt 24GB) { throw 'Less than 24GB free on C; refusing large package extraction' }
$listing = 'https://www.salome-platform.org/?sdm_downloads=salome-9-16-0-zip'
$checksumUrl = 'https://files.salome-platform.org/Salome/md5/9.16.0/SALOME-9.16.0.zip.md5'
$headers = @{'User-Agent'='Mozilla/5.0 (compatible; CFD-Automation/1.0)'}
Write-Host "Reading official SALOME archive listing..."
$page = (Invoke-WebRequest -Uri $listing -Headers $headers -TimeoutSec 90).Content
if ($page -notmatch 'SALOME-9.16.0.zip') { throw 'Official listing page does not show requested ZIP' }
$linkMatches = [regex]::Matches($page, '(?i)(?:href|data-download-url)\s*=\s*["'']([^"'']+)["'']')
$candidates = @()
foreach ($m in $linkMatches) {
  $raw = [System.Net.WebUtility]::HtmlDecode($m.Groups[1].Value)
  if ($raw -match '(sdm_process_download|download_id|SALOME-9\.16\.0\.zip)') {
    try {
      $u = [uri]::new([uri]$listing, $raw)
      if ($u.Scheme -eq 'https' -and $u.Host -match '(^|\.)salome-platform\.org$') {
        $candidates += $u.AbsoluteUri
      }
    } catch {}
  }
}
$candidates = @($candidates | Select-Object -Unique)
if ($candidates.Count -eq 0) { throw 'No official ZIP download endpoint found on SALOME page' }
$downloadUrl = $candidates[0]
Write-Host "Approved official download endpoint: $downloadUrl"
$checksumText=(Invoke-WebRequest -Uri $checksumUrl -Headers $headers -TimeoutSec 90).Content
$hashMatch=[regex]::Match($checksumText, '(?i)[a-f0-9]{32}')
if (!$hashMatch.Success) { throw 'Official SALOME MD5 checksum could not be read' }
$expected=$hashMatch.Value.ToLowerInvariant()
Write-Host "Expected official MD5: $expected"
New-Item -ItemType Directory $InstallRoot -Force | Out-Null
$zip = Join-Path $InstallRoot 'SALOME-9.16.0.zip'
Write-Host 'Downloading official SALOME Windows ZIP (large package)...'
& curl.exe --fail --location --retry 3 --connect-timeout 30 --max-time 2700 --output $zip $downloadUrl
if ($LASTEXITCODE -ne 0) { throw "Official SALOME download failed with curl code $LASTEXITCODE" }
if ((Get-Item $zip).Length -lt 500MB) { throw 'Downloaded file is too small to be SALOME full Windows archive' }
$actual=(Get-FileHash -Algorithm MD5 $zip).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "Official MD5 mismatch: $actual vs $expected" }
Write-Host 'SALOME download MD5 verified against official published checksum.'
if ((Get-PSDrive C).Free -lt 14GB) { throw 'Insufficient free disk before extracting SALOME' }
$sevenZip = 'C:\Program Files\7-Zip\7z.exe'
if (!(Test-Path $sevenZip)) { throw '7-Zip was not found' }
& $sevenZip t $zip | Select-Object -Last 8
if ($LASTEXITCODE -ne 0) { throw 'SALOME ZIP archive integrity test failed' }
Write-Host 'Extracting into short path C:\SAL ...'
& $sevenZip x $zip "-o$InstallRoot" -y | Select-Object -Last 8
if ($LASTEXITCODE -ne 0) { throw "SALOME ZIP extraction failed with code $LASTEXITCODE" }
$bat=Get-ChildItem $InstallRoot -Filter 'run_salome.bat' -File -Recurse | Select-Object -First 1
if (!$bat) { throw 'SALOME Windows command launcher run_salome.bat missing from extracted package' }
$bat.FullName | Set-Content -Path (Join-Path $env:RUNNER_TEMP 'salome-launcher.txt') -Encoding ascii
Write-Host "Verified SALOME Windows launcher: $($bat.FullName)"
Write-Host "CFD_SALOME_INSTALL_OK archive MD5=$actual"
