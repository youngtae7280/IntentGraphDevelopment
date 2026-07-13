[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Programs\IntentGraph'),
    [switch]$NoPathUpdate
)

$ErrorActionPreference = 'Stop'
$ManifestName = 'igd-bundle-manifest.json'
$ExpectedRole = 'intentgraph-windows-portable-bundle-manifest'

function Resolve-FullPath([string]$Value) {
    return [System.IO.Path]::GetFullPath($Value).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
}

function Test-SamePath([string]$Left, [string]$Right) {
    try { return (Resolve-FullPath $Left) -eq (Resolve-FullPath $Right) } catch { return $false }
}

function Assert-SafeInstallRoot([string]$Value, [string]$BundleRoot) {
    $full = Resolve-FullPath $Value
    $root = [System.IO.Path]::GetPathRoot($full).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    if (-not $full -or $full -eq $root) { throw 'InstallRoot must not be a filesystem root.' }
    if ($full -eq (Resolve-FullPath $BundleRoot)) { throw 'InstallRoot must not equal the bundle root.' }
    return $full
}

function Assert-SafeRelativePath([string]$Value) {
    if (-not $Value -or $Value.Contains('\') -or [System.IO.Path]::IsPathRooted($Value)) {
        throw "Unsafe bundle record path: $Value"
    }
    foreach ($part in $Value.Split('/')) {
        if (-not $part -or $part -eq '.' -or $part -eq '..' -or $part.IndexOfAny([System.IO.Path]::GetInvalidFileNameChars()) -ge 0) {
            throw "Unsafe bundle record path: $Value"
        }
    }
}

function Get-RelativePath([string]$Root, [string]$FullName) {
    return $FullName.Substring($Root.Length).TrimStart(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ).Replace([System.IO.Path]::DirectorySeparatorChar, '/')
}

function Assert-ExactInventory([string]$Root, [hashtable]$ExpectedFiles, [hashtable]$ExpectedDirectories) {
    $rootItem = Get-Item -LiteralPath $Root -Force
    if (-not $rootItem.PSIsContainer -or ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw 'Bundle root must be a non-reparse-point directory.'
    }
    $pending = New-Object System.Collections.Stack
    $pending.Push($Root)
    $observedFiles = @{}
    while ($pending.Count -gt 0) {
        $directory = [string]$pending.Pop()
        foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
            $relative = Get-RelativePath $Root $item.FullName
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "Bundle must not contain reparse points: $relative"
            }
            if ($item.PSIsContainer) {
                if (-not $ExpectedDirectories.ContainsKey($relative)) {
                    throw "Bundle contains an unknown directory: $relative"
                }
                $pending.Push($item.FullName)
            } else {
                if (-not $ExpectedFiles.ContainsKey($relative)) {
                    throw "Bundle contains an unknown file: $relative"
                }
                $observedFiles[$relative] = $true
            }
        }
    }
    foreach ($relative in $ExpectedFiles.Keys) {
        if (-not $observedFiles.ContainsKey($relative)) { throw "Missing bundle file: $relative" }
    }
}

function Get-ValidatedManifest([string]$Root) {
    $manifestPath = Join-Path $Root $ManifestName
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Missing bundle manifest: $manifestPath" }
    if ((Get-Item -LiteralPath $manifestPath -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Bundle manifest must not be a reparse point.'
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.artifactRole -ne $ExpectedRole) { throw 'Unexpected bundle manifest role.' }
    if ($manifest.status -ne 'intentgraph-windows-portable-bundle-built') { throw 'Unexpected bundle manifest status.' }
    if (-not $manifest.files -or $manifest.files.Count -lt 1) { throw 'Bundle manifest has no file records.' }
    if ([int]$manifest.fileCount -ne $manifest.files.Count) { throw 'Bundle manifest fileCount mismatch.' }
    foreach ($key in @('networkAccessed', 'downloadPerformed', 'credentialAccessed', 'artifactSigned', 'releasePublished', 'providerApiCalled', 'targetRepositoryMutated')) {
        if ($manifest.authority.$key -ne $false) { throw "Unsafe bundle authority boundary: $key" }
    }
    $expectedFiles = @{$ManifestName = $true}
    $expectedDirectories = @{}
    foreach ($record in $manifest.files) {
        $relative = [string]$record.path
        Assert-SafeRelativePath $relative
        if ($expectedFiles.ContainsKey($relative)) { throw "Duplicate bundle record path: $relative" }
        $expectedFiles[$relative] = $true
        $parts = $relative.Split('/')
        for ($index = 1; $index -lt $parts.Count; $index++) {
            $expectedDirectories[($parts[0..($index - 1)] -join '/')] = $true
        }
        $source = Join-Path $Root ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing bundle file: $relative" }
        $item = Get-Item -LiteralPath $source -Force
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw "Bundle file must not be a reparse point: $relative" }
        $actual = 'sha256:' + (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne [string]$record.sha256) { throw "Bundle digest mismatch: $relative" }
        if ($item.Length -ne [long]$record.byteLength) { throw "Bundle byte length mismatch: $relative" }
    }
    Assert-ExactInventory $Root $expectedFiles $expectedDirectories
    return $manifest
}

function Get-PathLaunchers {
    $launchers = @()
    $extensions = @('') + @($env:PATHEXT -split ';' | Where-Object { $_ -and $_.Trim() }) + @('.PS1')
    foreach ($raw in @($env:Path -split ';' | Where-Object { $_ -and $_.Trim() })) {
        try {
            $entry = [Environment]::ExpandEnvironmentVariables($raw.Trim().Trim('"'))
            $directory = Resolve-FullPath $entry
            foreach ($extension in @($extensions | Select-Object -Unique)) {
                $candidate = Join-Path $directory ('igd' + $extension)
                if (Test-Path -LiteralPath $candidate -PathType Leaf) { $launchers += (Resolve-FullPath $candidate) }
            }
        } catch {
            throw "PATH contains an invalid entry that cannot be checked safely: $raw"
        }
    }
    return @($launchers | Select-Object -Unique)
}

function Assert-NoPathShadowing([string]$Entry) {
    $expected = Resolve-FullPath (Join-Path $Entry 'igd.cmd')
    $shadowing = @(Get-PathLaunchers | Where-Object { -not (Test-SamePath $_ $expected) })
    if ($shadowing.Count -gt 0) {
        throw "PATH already resolves igd outside InstallRoot: $($shadowing -join ', '). Use -NoPathUpdate or remove the shadowing launcher."
    }
}

function Add-UserPathEntry([string]$Entry) {
    $current = [Environment]::GetEnvironmentVariable('Path', 'User')
    $kept = @($current -split ';' | Where-Object { $_ -and $_.Trim() -and -not (Test-SamePath $_ $Entry) })
    [Environment]::SetEnvironmentVariable('Path', ((@($Entry) + $kept) -join ';'), 'User')

    $processKept = @($env:Path -split ';' | Where-Object { $_ -and $_.Trim() -and -not (Test-SamePath $_ $Entry) })
    $env:Path = ((@($Entry) + $processKept) -join ';')
    $resolved = Get-Command 'igd' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $resolved -or -not (Test-SamePath $resolved.Source (Join-Path $Entry 'igd.cmd'))) {
        throw 'PATH update did not resolve igd to the new IntentGraph installation.'
    }
}

$bundleRoot = Resolve-FullPath $PSScriptRoot
$destination = Assert-SafeInstallRoot $InstallRoot $bundleRoot
$manifest = Get-ValidatedManifest $bundleRoot

if (Test-Path -LiteralPath $destination) {
    throw "InstallRoot already exists; uninstall it or choose another path: $destination"
}
if (-not $NoPathUpdate) { Assert-NoPathShadowing $destination }

$parent = Split-Path -Parent $destination
if (-not $parent) { throw 'InstallRoot must have a parent directory.' }
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$staging = Join-Path $parent ('.igd-install-' + [Guid]::NewGuid().ToString('N'))

try {
    New-Item -ItemType Directory -Path $staging | Out-Null
    foreach ($record in $manifest.files) {
        $relative = [string]$record.path
        $source = Join-Path $bundleRoot ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        $target = Join-Path $staging ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target
    }
    Copy-Item -LiteralPath (Join-Path $bundleRoot $ManifestName) -Destination (Join-Path $staging $ManifestName)
    Get-ValidatedManifest $staging | Out-Null
    Move-Item -LiteralPath $staging -Destination $destination
} finally {
    if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
}

if (-not $NoPathUpdate) { Add-UserPathEntry $destination }
Write-Output "IntentGraph installed at $destination"
if ($NoPathUpdate) { Write-Output "PATH was not changed. Launch with: $destination\igd.cmd" }
else { Write-Output 'Open a new terminal and run: igd doctor' }
