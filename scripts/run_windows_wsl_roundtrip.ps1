param(
    [string]$WindowsPython = "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe",
    [string]$WslRepo = "~/codex-demo",
    [string]$SourceUrl = "https://example.com/article",
    [ValidateSet("mock", "http", "browser")]
    [string]$ExportMode = "mock",
    [string]$SharedRoot = (Join-Path $env:TEMP "content-ingestion-roundtrip"),
    [ValidateSet("html", "txt", "md")]
    [string]$ContentType = "html",
    [string]$Platform,
    [string]$ProfileDir,
    [string]$BrowserChannel,
    [string]$WaitUntil,
    [int]$TimeoutMs,
    [int]$SettleMs,
    [string]$WaitForSelector,
    [string]$WaitForSelectorState,
    [switch]$Headed,
    [switch]$KeepArtifacts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Assert-PathExists {
    param([string]$PathValue)
    if (-not (Test-Path $PathValue)) {
        throw "Expected path does not exist: $PathValue"
    }
}

function Read-JsonFile {
    param([string]$PathValue)
    return Get-Content -Path $PathValue -Raw | ConvertFrom-Json
}

function Assert-PropertyEquals {
    param(
        [object]$ObjectValue,
        [string]$PropertyName,
        [object]$ExpectedValue,
        [string]$Context
    )
    if ($null -eq $ObjectValue) {
        throw "Expected object is null: $Context"
    }
    if (-not ($ObjectValue.PSObject.Properties.Name -contains $PropertyName)) {
        throw "Missing property '$PropertyName' in $Context"
    }
    $actualValue = $ObjectValue.$PropertyName
    if ($actualValue -ne $ExpectedValue) {
        throw "Unexpected value for $Context.$PropertyName. expected='$ExpectedValue' actual='$actualValue'"
    }
}

function Add-OptionalArgument {
    param(
        [System.Collections.Generic.List[string]]$ArgumentList,
        [string]$Flag,
        [object]$Value
    )
    if ($null -eq $Value) {
        return
    }
    $stringValue = "$Value"
    if ($stringValue -eq "") {
        return
    }
    $ArgumentList.Add($Flag) | Out-Null
    $ArgumentList.Add($stringValue) | Out-Null
}

function Convert-ToWslPath {
    param([string]$WindowsPath)
    $resolved = Resolve-Path $WindowsPath
    $wslPath = & wsl.exe -e wslpath -a $resolved.Path
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to convert Windows path to WSL path: $WindowsPath"
    }
    return ($wslPath | Select-Object -First 1).Trim()
}

if (Test-Path $SharedRoot) {
    Remove-Item $SharedRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $SharedRoot | Out-Null

$env:CONTENT_INGESTION_SHARED_INBOX_ROOT = $SharedRoot
$wslSharedRoot = Convert-ToWslPath -WindowsPath $SharedRoot

Write-Host "shared_root=$SharedRoot"
Write-Host "wsl_shared_root=$wslSharedRoot"
Write-Host "export_mode=$ExportMode"

Push-Location $repoRoot
try {
    $exportArgs = [System.Collections.Generic.List[string]]::new()
    $exportArgs.Add("main.py") | Out-Null
    switch ($ExportMode) {
        "mock" {
            $exportArgs.Add("export-mock-job") | Out-Null
            $exportArgs.Add($SourceUrl) | Out-Null
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--content-type" -Value $ContentType
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--platform" -Value $Platform
        }
        "http" {
            $exportArgs.Add("export-url-job") | Out-Null
            $exportArgs.Add($SourceUrl) | Out-Null
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--content-type" -Value $ContentType
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--platform" -Value $Platform
        }
        "browser" {
            $exportArgs.Add("export-browser-job") | Out-Null
            $exportArgs.Add($SourceUrl) | Out-Null
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--platform" -Value $Platform
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--profile-dir" -Value $ProfileDir
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--browser-channel" -Value $BrowserChannel
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--wait-until" -Value $WaitUntil
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--timeout-ms" -Value $TimeoutMs
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--settle-ms" -Value $SettleMs
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--wait-for-selector" -Value $WaitForSelector
            Add-OptionalArgument -ArgumentList $exportArgs -Flag "--wait-for-selector-state" -Value $WaitForSelectorState
            if ($Headed) {
                $exportArgs.Add("--headed") | Out-Null
            }
        }
    }

    Write-Host "step=windows_export_$ExportMode"
    & $WindowsPython @exportArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Windows export failed for mode '$ExportMode'"
    }

    Write-Host "step=wsl_validate_inbox"
    & wsl.exe -e bash -lc "export CONTENT_INGESTION_SHARED_INBOX_ROOT='$wslSharedRoot'; cd $WslRepo && python3 main.py validate-inbox"
    if ($LASTEXITCODE -ne 0) {
        throw "WSL validate-inbox failed"
    }

    Write-Host "step=wsl_watch_inbox_once"
    & wsl.exe -e bash -lc "export CONTENT_INGESTION_SHARED_INBOX_ROOT='$wslSharedRoot'; cd $WslRepo && python3 main.py watch-inbox --once"
    if ($LASTEXITCODE -ne 0) {
        throw "WSL watch-inbox --once failed"
    }
}
finally {
    Pop-Location
}

$processedDirs = @(Get-ChildItem (Join-Path $SharedRoot "processed") -Directory -ErrorAction SilentlyContinue)
if ($processedDirs.Count -ne 1) {
    throw "Expected exactly one processed job, found $($processedDirs.Count)"
}

$processedDir = $processedDirs[0].FullName
Write-Host "processed_dir=$processedDir"

Assert-PathExists (Join-Path $processedDir "metadata.json")
Assert-PathExists (Join-Path $processedDir "normalized.json")
Assert-PathExists (Join-Path $processedDir "normalized.md")
Assert-PathExists (Join-Path $processedDir "pipeline.json")
Assert-PathExists (Join-Path $processedDir "status.json")

$processedMetadata = Read-JsonFile (Join-Path $processedDir "metadata.json")
$normalized = Read-JsonFile (Join-Path $processedDir "normalized.json")

Assert-PropertyEquals $normalized "job_id" $processedMetadata.job_id "normalized"
Assert-PropertyEquals $normalized "content_type" $processedMetadata.content_type "normalized"
Assert-PropertyEquals $normalized.asset "source_url" $processedMetadata.source_url "normalized.asset"

$expectedCanonicalUrl = if ($processedMetadata.PSObject.Properties.Name -contains "final_url" -and $processedMetadata.final_url) {
    $processedMetadata.final_url
} else {
    $processedMetadata.source_url
}
Assert-PropertyEquals $normalized.asset "canonical_url" $expectedCanonicalUrl "normalized.asset"
Assert-PropertyEquals $normalized.asset.metadata "job_id" $processedMetadata.job_id "normalized.asset.metadata"
Assert-PropertyEquals $normalized.asset.metadata "content_type" $processedMetadata.content_type "normalized.asset.metadata"

$handoffKeys = @(
    "collector",
    "collected_at",
    "collection_mode",
    "browser_channel",
    "profile_slug",
    "wait_until",
    "wait_for_selector",
    "wait_for_selector_state"
)
$expectedHandoff = @{}
foreach ($key in $handoffKeys) {
    if (($processedMetadata.PSObject.Properties.Name -contains $key) -and $null -ne $processedMetadata.$key -and "$($processedMetadata.$key)" -ne "") {
        $expectedHandoff[$key] = "$($processedMetadata.$key)"
    }
}

if ($expectedHandoff.Count -gt 0) {
    if (-not ($normalized.asset.metadata.PSObject.Properties.Name -contains "handoff")) {
        throw "Missing normalized.asset.metadata.handoff"
    }
    $actualHandoff = $normalized.asset.metadata.handoff
    $actualKeys = @($actualHandoff.PSObject.Properties.Name)
    if ($actualKeys.Count -ne $expectedHandoff.Count) {
        throw "Unexpected handoff field count. expected=$($expectedHandoff.Count) actual=$($actualKeys.Count)"
    }
    foreach ($key in $expectedHandoff.Keys) {
        Assert-PropertyEquals $actualHandoff $key $expectedHandoff[$key] "normalized.asset.metadata.handoff"
    }
}

Write-Host "roundtrip_status=success"

if (-not $KeepArtifacts) {
    Remove-Item $SharedRoot -Recurse -Force
    Write-Host "artifacts=removed"
}
