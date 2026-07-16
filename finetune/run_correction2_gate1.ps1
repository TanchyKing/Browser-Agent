param(
    [string]$Python = ".venv-finetune\Scripts\python.exe",
    [string]$Manifest = "artifacts\finetune\correction2_qwen3_8b_manifest.json",
    [string]$RuntimeDir = "artifacts\finetune\correction2_gate1_runtime",
    [string]$HfHome = "D:\OllamaModels\hf-cache",
    [string]$Proxy = "http://127.0.0.1:7897"
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

Write-Output "CORRECTION2_GATE1 mirror_direct_start"
& $Python finetune\download_model_gate.py `
    --manifest $Manifest `
    --hf-home $HfHome `
    --runtime-dir $RuntimeDir `
    --route mirror_direct `
    --endpoint https://hf-mirror.com `
    --direct `
    --max-workers 2 `
    --max-attempts-per-file 2 `
    --download-timeout 300
if ($LASTEXITCODE -eq 0) {
    Write-Output "CORRECTION2_GATE1 complete route=mirror_direct"
    exit 0
}

Write-Output "CORRECTION2_GATE1 mirror_failed installing_hf_xet=1.5.1"
$env:HTTP_PROXY = $Proxy
$env:HTTPS_PROXY = $Proxy
Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:no_proxy -ErrorAction SilentlyContinue
& $Python -m pip install "hf-xet==1.5.1"
$installExit = $LASTEXITCODE

$xetReady = $false
if ($installExit -eq 0) {
    & $Python -c "import hf_xet; print('HF_XET_IMPORT_OK')"
    $xetReady = $LASTEXITCODE -eq 0
}

if ($xetReady) {
    Write-Output "CORRECTION2_GATE1 official_proxy_xet_start"
    & $Python finetune\download_model_gate.py `
        --manifest $Manifest `
        --hf-home $HfHome `
        --runtime-dir $RuntimeDir `
        --route official_proxy_xet `
        --endpoint https://huggingface.co `
        --proxy $Proxy `
        --max-workers 1 `
        --max-attempts-per-file 5 `
        --download-timeout 300
    if ($LASTEXITCODE -eq 0) {
        Write-Output "CORRECTION2_GATE1 complete route=official_proxy_xet"
        exit 0
    }
    Write-Output "CORRECTION2_GATE1 xet_route_exhausted fallback=plain_http"
} else {
    Write-Output "CORRECTION2_GATE1 hf_xet_import_blocked_or_install_failed fallback=plain_http"
    if ($installExit -eq 0) {
        & $Python -m pip uninstall -y hf-xet
    }
}

Write-Output "CORRECTION2_GATE1 official_proxy_plain_start"
& $Python finetune\download_model_gate.py `
    --manifest $Manifest `
    --hf-home $HfHome `
    --runtime-dir $RuntimeDir `
    --route official_proxy_plain `
    --endpoint https://huggingface.co `
    --proxy $Proxy `
    --disable-xet `
    --max-workers 1 `
    --max-attempts-per-file 8 `
    --download-timeout 300
exit $LASTEXITCODE
