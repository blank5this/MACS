# deploy_hf_pack.ps1 — Package MACS for one-click Hugging Face Spaces deploy.
#
# What this does:
#   1. Creates a clean dist_hf/ directory
#   2. Copies only what HF Spaces needs:
#        app.py, requirements_hf.txt, README_HF.md, macs_pkg/, data/erp_kb/
#   3. Removes __pycache__ (HF rebuilds anyway)
#   4. Initializes a git repo
#   5. Optionally adds HF remote + pushes (if you provide a Space URL)
#
# Usage:
#   # 1. Just package locally (no push)
#   pwsh -File scripts/deploy_hf_pack.ps1
#
#   # 2. Package + push to an existing Space
#   pwsh -File scripts/deploy_hf_pack.ps1 -SpaceRepo "https://huggingface.co/spaces/blank5this/macs-erp-copilot"
#
# After this script finishes:
#   - dist_hf/ has the deployable code
#   - dist_hf/README_HF.md → must be renamed to README.md (HF reads README.md only)
#   - dist_hf/.gitignore excludes secrets, __pycache__, dist_hf itself

param(
    [string]$SpaceRepo = "",
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = Resolve-Path "$PSScriptRoot/.."
$DIST = Join-Path $PROJECT_ROOT "dist_hf"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MACS → Hugging Face Spaces — deployment packager" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project root: $PROJECT_ROOT"
Write-Host "  Output dir:   $DIST"
Write-Host ""

# Step 1: clean slate
if (Test-Path $DIST) {
    Write-Host "[1/6] Removing old dist_hf/ ..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $DIST
}
New-Item -ItemType Directory -Path $DIST | Out-Null

# Step 2: copy deployment files
Write-Host "[2/6] Copying app.py, requirements_hf.txt, README_HF.md ..." -ForegroundColor Yellow
Copy-Item (Join-Path $PROJECT_ROOT "app.py") $DIST
Copy-Item (Join-Path $PROJECT_ROOT "requirements_hf.txt") $DIST
Copy-Item (Join-Path $PROJECT_ROOT "README_HF.md") $DIST

# Step 3: copy macs_pkg (the whole framework — it's needed because app.py
# imports from macs_pkg.llm, macs_pkg.rag, macs_pkg.erp.*)
Write-Host "[3/6] Copying macs_pkg/ (whole framework) ..." -ForegroundColor Yellow
Copy-Item -Recurse (Join-Path $PROJECT_ROOT "macs_pkg") $DIST

# Step 4: copy data/erp_kb (sample documents for RAG)
Write-Host "[4/6] Copying data/erp_kb/ (18 policy documents) ..." -ForegroundColor Yellow
Copy-Item -Recurse (Join-Path $PROJECT_ROOT "data") (Join-Path $DIST "data")

# Step 5: cleanup (strip __pycache__, pyc, etc.)
Write-Host "[5/6] Stripping __pycache__ / .pyc ..." -ForegroundColor Yellow
Get-ChildItem -Path $DIST -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $DIST -Recurse -File -Filter "*.pyc" |
    Remove-Item -Force

# Step 6: rename README_HF.md → README.md (HF Spaces reads README.md only)
Write-Host "[6/6] Renaming README_HF.md → README.md ..." -ForegroundColor Yellow
Move-Item (Join-Path $DIST "README_HF.md") (Join-Path $DIST "README.md") -Force

# Write a .gitignore so users don't accidentally commit secrets
$gitignore = @"
__pycache__/
*.pyc
*.pyo
*.db
*.sqlite
.env
*.local
dist_hf/
"@
Set-Content -Path (Join-Path $DIST ".gitignore") -Value $gitignore

# Show what we built
Write-Host ""
Write-Host "✅  Deployment package ready:" -ForegroundColor Green
Write-Host ""
Get-ChildItem $DIST | ForEach-Object {
    $size = if ($_.PSIsContainer) { "<DIR>" } else { "{0:N1} KB" -f ($_.Length / 1KB) }
    Write-Host ("    {0,-30}  {1}" -f $_.Name, $size) -ForegroundColor White
}

# Initialize git
Push-Location $DIST
try {
    git init -q 2>$null
    git checkout -b main 2>$null
    git add . 2>$null
    git -c user.email="deploy@local" -c user.name="Deploy Bot" commit -q -m "Deploy MACS ERP Copilot to HF Spaces" 2>$null
    Write-Host ""
    Write-Host "  git init + commit done in dist_hf/" -ForegroundColor Green
}
finally {
    Pop-Location
}

# Optional: add HF remote and push
if (-not $NoPush -and $SpaceRepo) {
    Write-Host ""
    Write-Host "[push] Adding HF remote and pushing ..." -ForegroundColor Yellow
    Push-Location $DIST
    try {
        git remote remove origin 2>$null
        git remote add origin $SpaceRepo
        # HF Spaces uses 'main' or 'master' branch
        git push -u origin main --force
    } finally {
        Pop-Location
    }
    Write-Host ""
    Write-Host "✅  Pushed to $SpaceRepo" -ForegroundColor Green
    Write-Host "    Now go to Space Settings → Variables and secrets:" -ForegroundColor White
    Write-Host "      New secret: MINIMAX_API_KEY = sk-cp-..." -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Create a Space at https://huggingface.co/new-space" -ForegroundColor White
    Write-Host "     - Name: macs-erp-copilot" -ForegroundColor White
    Write-Host "     - SDK:   Gradio" -ForegroundColor White
    Write-Host "     - Hardware: CPU basic (free)" -ForegroundColor White
    Write-Host ""
    Write-Host "  2. Push the package:" -ForegroundColor White
    Write-Host "     cd dist_hf" -ForegroundColor Yellow
    Write-Host "     git remote add origin https://huggingface.co/spaces/<your-name>/macs-erp-copilot" -ForegroundColor Yellow
    Write-Host "     git push -u origin main" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. Set the API key in Space Settings → Variables and secrets:" -ForegroundColor White
    Write-Host "     MINIMAX_API_KEY = sk-cp-..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  4. Wait ~2 minutes for the Space to build, then visit the URL." -ForegroundColor White
    Write-Host ""
    Write-Host "  Or run this script with -SpaceRepo to do steps 1-2 in one go:" -ForegroundColor Cyan
    Write-Host "     pwsh -File scripts/deploy_hf_pack.ps1 -SpaceRepo `"https://huggingface.co/spaces/blank5this/macs-erp-copilot`"" -ForegroundColor Yellow
}
Write-Host ""