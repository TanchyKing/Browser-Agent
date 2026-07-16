param(
    [string]$ResumeFromCheckpoint = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$env:HF_HOME = "D:\OllamaModels\hf-cache"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

$RuntimeDir = Join-Path $ProjectRoot "artifacts\finetune\r12_50step_runtime"
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
$StatusPath = Join-Path $RuntimeDir "supervisor_status.json"
$StartedAt = Get-Date

$Arguments = @(
    "-u",
    "finetune\train_qlora.py",
    "--model", "Qwen/Qwen3-8B",
    "--revision", "b968826d9c46dd6066d109eabc6255188de91218",
    "--local-model-path", "D:\OllamaModels\hf-cache\hub\models--Qwen--Qwen3-8B\snapshots\b968826d9c46dd6066d109eabc6255188de91218",
    "--dataset", "finetune\data\processed\sft_r10e_reviewed.jsonl",
    "--output-dir", "artifacts\finetune\R12_50step_qwen3_8b_qlora",
    "--max-length", "1024",
    "--max-steps", "50",
    "--learning-rate", "0.0002"
)
if ($ResumeFromCheckpoint) {
    $Arguments += @("--resume-from-checkpoint", $ResumeFromCheckpoint)
}

$ExitCode = 1
$ErrorText = $null
try {
    & ".\.venv-finetune\Scripts\python.exe" @Arguments
    $ExitCode = $LASTEXITCODE
} catch {
    $ErrorText = $_.Exception.Message
    $ExitCode = 1
} finally {
    $CompletedAt = Get-Date
    $Status = [ordered]@{
        status = if ($ExitCode -eq 0) { "completed" } else { "failed" }
        exit_code = $ExitCode
        error = $ErrorText
        started_at = $StartedAt.ToString("o")
        completed_at = $CompletedAt.ToString("o")
        elapsed_seconds = [math]::Round(($CompletedAt - $StartedAt).TotalSeconds, 2)
        resume_from_checkpoint = if ($ResumeFromCheckpoint) { $ResumeFromCheckpoint } else { $null }
        output_dir = "artifacts/finetune/R12_50step_qwen3_8b_qlora"
    }
    $Status | ConvertTo-Json | Set-Content -LiteralPath $StatusPath -Encoding UTF8
}

exit $ExitCode
