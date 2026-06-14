# push_to_hf.ps1 — One-shot push of MACS ERP Copilot to Hugging Face Spaces.
#
# Why this script:
#   * The MACS repository on this machine can't reach huggingface.co
#     directly (firewall / proxy at the egress). This script lets the
#     user run it locally on a machine that *can* reach HF, with
#     minimal typing.
#   * Honors HTTP_PROXY / HTTPS_PROXY env vars — set them to your
#     local proxy (Clash: 7890, v2ray: 10809, etc.) if needed.
#
# Usage:
#   # If you can reach HF directly:
#   powershell -ExecutionPolicy Bypass -File scripts/push_to_hf.ps1 `
#       -HfUsername gkf123 `
#       -HfToken hf_xxxxxxxxxxxxxxxxxxxxxxxxxx
#
#   # If you need a proxy:
#   $env:HTTPS_PROXY = "http://127.0.0.1:7890"
#   $env:HTTP_PROXY  = "http://127.0.0.1:7890"
#   powershell -ExecutionPolicy Bypass -File scripts/push_to_hf.ps1 `
#       -HfUsername gkf123 `
#       -HfToken hf_xxxxxxxxxxxxxxxxxxxxxxxxxx
#
# After success, your Space will be live at:
#   https://huggingface.co/spaces/<HfUsername>/macs-erp-copilot

param(
    [Parameter(Mandatory=$true)] [string]$HfUsername,
    [Parameter(Mandatory=$true)] [string]$HfToken,
    [string]$SpaceName = "macs-erp-copilot",
    [string]$DistDir = "dist_hf"
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = Resolve-Path "$PSScriptRoot/.."
$DIST = Join-Path $PROJECT_ROOT $DistDir

# Auto-detect proxy from environment if not set
if (-not $env:HTTPS_PROXY -and -not $env:HTTP_PROXY) {
    foreach ($port in @(7890, 7891, 10809, 1080, 8888, 8080)) {
        $test = Test-NetConnection -ComputerName "127.0.0.1" -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($test) {
            Write-Host "[proxy] Detected proxy on 127.0.0.1:$port" -ForegroundColor Yellow
            $env:HTTPS_PROXY = "http://127.0.0.1:$port"
            $env:HTTP_PROXY  = "http://127.0.0.1:$port"
            break
        }
    }
}

if (-not (Test-Path $DIST)) {
    Write-Host "[error] $DIST not found. Run scripts/deploy_hf_pack.ps1 first." -ForegroundColor Red
    exit 1
}

Push-Location $DIST
try {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Push MACS ERP Copilot to HF Spaces" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  HF user:    $HfUsername"
    Write-Host "  Space:      $HfUsername/$SpaceName"
    Write-Host "  Dist dir:   $DIST"
    $proxyDisplay = if ([string]::IsNullOrEmpty($env:HTTPS_PROXY)) { "(none — direct connection)" } else { $env:HTTPS_PROXY }
    Write-Host "  Proxy:      $proxyDisplay"
    Write-Host ""

    # Sanity: dist_hf must already have a commit (deploy_hf_pack.ps1 makes one)
    $head = git rev-parse --verify HEAD 2>$null
    if (-not $head) {
        Write-Host "[git] No commit in $DIST — creating one ..." -ForegroundColor Yellow
        git -c user.email="deploy@local" -c user.name="Deploy Bot" add .
        git -c user.email="deploy@local" -c user.name="Deploy Bot" commit -m "Deploy MACS ERP Copilot to HF Spaces"
    }

    # Build the authenticated remote URL.
    $remoteUrl = "https://${HfToken}@huggingface.co/spaces/${HfUsername}/${SpaceName}"
    git remote remove origin 2>$null
    git remote add origin $remoteUrl
    Write-Host "[git] remote set to origin (auth embedded; safe for HTTPS HF Spaces)" -ForegroundColor Green

    # Push with a long timeout. --force in case the Space was init-empty.
    Write-Host "[git] pushing ... (this can take 1-2 minutes for 1.6 MB)" -ForegroundColor Yellow
    git push -u origin main --force
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[error] push failed. Common causes:" -ForegroundColor Red
        Write-Host "  1. HF token is wrong or expired (https://huggingface.co/settings/tokens)" -ForegroundColor White
        Write-Host "  2. HF can't be reached — try setting HTTPS_PROXY" -ForegroundColor White
        Write-Host "  3. Space name already taken — pick a different -SpaceName" -ForegroundColor White
        exit 1
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  ✅  Push succeeded!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  URL:  https://huggingface.co/spaces/$HfUsername/$SpaceName" -ForegroundColor White
    Write-Host ""
    Write-Host "  Next:" -ForegroundColor Cyan
    Write-Host "    1. Wait 2-3 minutes for the Space to build (check the Logs tab)" -ForegroundColor White
    Write-Host "    2. Set MINIMAX_API_KEY in Space Settings → Variables and secrets" -ForegroundColor White
    Write-Host "    3. Visit the URL to verify" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}