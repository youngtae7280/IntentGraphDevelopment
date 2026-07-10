[CmdletBinding()]
param(
    [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot "..\..")).Path
}

function Test-RequiredPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $fullPath = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Required path is missing: $RelativePath"
    }

    Write-Host "[ok] $RelativePath"
}

$requiredPaths = @(
    "WindowsUtility.sln",
    "src\WindowsUtility.App\WindowsUtility.App.csproj",
    "src\WindowsUtility.Shell\WindowsUtility.Shell.csproj",
    "tests\RegressionSmoke\Invoke-WindowsUtilityRegressionSmoke.ps1"
)

foreach ($path in $requiredPaths) {
    Test-RequiredPath -RelativePath $path
}

Write-Host "IntentGraph shell/workspace source-application preflight passed."
