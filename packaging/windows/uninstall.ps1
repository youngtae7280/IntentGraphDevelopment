[CmdletBinding()]
param(
    [string]$InstallRoot = $PSScriptRoot,
    [switch]$NoPathUpdate
)

$ErrorActionPreference = 'Stop'
$ManifestName = 'igd-bundle-manifest.json'
$ExpectedRole = 'intentgraph-windows-portable-bundle-manifest'

function Resolve-FullPath([string]$Value) {
    return [System.IO.Path]::GetFullPath($Value).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
}

function Assert-SafeRelativePath([string]$Value) {
    if (-not $Value -or $Value.Contains('\') -or [System.IO.Path]::IsPathRooted($Value)) {
        throw "Unsafe installed bundle record path: $Value"
    }
    foreach ($part in $Value.Split('/')) {
        if (-not $part -or $part -eq '.' -or $part -eq '..' -or $part.IndexOfAny([System.IO.Path]::GetInvalidFileNameChars()) -ge 0) {
            throw "Unsafe installed bundle record path: $Value"
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
        throw 'Refusing to remove an install root that is not a normal directory.'
    }
    $pending = New-Object System.Collections.Stack
    $pending.Push($Root)
    $observedFiles = @{}
    while ($pending.Count -gt 0) {
        $directory = [string]$pending.Pop()
        foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
            $relative = Get-RelativePath $Root $item.FullName
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "Refusing to remove an install tree containing a reparse point: $relative"
            }
            if ($item.PSIsContainer) {
                if (-not $ExpectedDirectories.ContainsKey($relative)) {
                    throw "Refusing to remove an install tree containing an unknown directory: $relative"
                }
                $pending.Push($item.FullName)
            } else {
                if (-not $ExpectedFiles.ContainsKey($relative)) {
                    throw "Refusing to remove an install tree containing an unknown file: $relative"
                }
                $observedFiles[$relative] = $true
            }
        }
    }
    foreach ($relative in $ExpectedFiles.Keys) {
        if (-not $observedFiles.ContainsKey($relative)) {
            throw "Refusing to remove an install tree missing a manifest file: $relative"
        }
    }
}

function Get-ValidatedInstallation([string]$Value) {
    $full = Resolve-FullPath $Value
    $root = [System.IO.Path]::GetPathRoot($full).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    if (-not $full -or $full -eq $root) { throw 'InstallRoot must not be a filesystem root.' }
    if (-not (Test-Path -LiteralPath $full -PathType Container)) { throw "InstallRoot must be an existing directory: $full" }
    $rootItem = Get-Item -LiteralPath $full -Force
    if ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'InstallRoot must not be a reparse point.' }

    $manifestPath = Join-Path $full $ManifestName
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Refusing to remove a directory without ${ManifestName}: $full" }
    if ((Get-Item -LiteralPath $manifestPath -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Refusing to remove an installation with a reparse-point manifest.'
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.artifactRole -ne $ExpectedRole) { throw 'Refusing to remove a directory with an unexpected manifest role.' }
    if ($manifest.status -ne 'intentgraph-windows-portable-bundle-built') { throw 'Refusing to remove a directory with an unexpected manifest status.' }
    if (-not $manifest.files -or $manifest.files.Count -lt 1 -or [int]$manifest.fileCount -ne $manifest.files.Count) {
        throw 'Refusing to remove a directory with an invalid manifest inventory.'
    }
    foreach ($key in @('networkAccessed', 'downloadPerformed', 'credentialAccessed', 'artifactSigned', 'releasePublished', 'providerApiCalled', 'targetRepositoryMutated')) {
        if ($manifest.authority.$key -ne $false) { throw "Refusing unsafe installed authority boundary: $key" }
    }

    $expectedFiles = @{$ManifestName = $true}
    $expectedDirectories = @{}
    foreach ($record in $manifest.files) {
        $relative = [string]$record.path
        Assert-SafeRelativePath $relative
        if ($expectedFiles.ContainsKey($relative)) { throw "Duplicate installed bundle record path: $relative" }
        $expectedFiles[$relative] = $true
        $parts = $relative.Split('/')
        for ($index = 1; $index -lt $parts.Count; $index++) {
            $expectedDirectories[($parts[0..($index - 1)] -join '/')] = $true
        }
        $path = Join-Path $full ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Refusing to remove an installation missing: $relative" }
        $item = Get-Item -LiteralPath $path -Force
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to remove an install tree containing a reparse point: $relative"
        }
        $actual = 'sha256:' + (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne [string]$record.sha256) { throw "Refusing to remove an installation with a digest mismatch: $relative" }
        if ($item.Length -ne [long]$record.byteLength) { throw "Refusing to remove an installation with a byte length mismatch: $relative" }
    }
    if (-not $expectedFiles.ContainsKey('igd.cmd')) { throw 'Refusing to remove an installation whose manifest omits igd.cmd.' }
    Assert-ExactInventory $full $expectedFiles $expectedDirectories
    return [pscustomobject]@{
        Root = $full
        Manifest = $manifest
        ExpectedDirectories = $expectedDirectories
    }
}

function Assert-SafePathChain([string]$Root, [string]$Relative) {
    $parts = $Relative.Split('/')
    if ($parts.Count -le 1) { return }
    $current = $Root
    for ($index = 0; $index -lt $parts.Count - 1; $index++) {
        $current = Join-Path $current $parts[$index]
        $item = Get-Item -LiteralPath $current -Force
        if (-not $item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Install tree changed before removal at: $($parts[0..$index] -join '/')"
        }
    }
}

function Remove-ValidatedTree($Installation) {
    $root = [string]$Installation.Root
    $fileRelatives = @($Installation.Manifest.files | ForEach-Object { [string]$_.path }) + @($ManifestName)
    foreach ($relative in $fileRelatives) {
        Assert-SafePathChain $root $relative
        $path = Join-Path $root ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        $item = Get-Item -LiteralPath $path -Force
        if ($item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Install tree changed before file removal: $relative"
        }
        Remove-Item -LiteralPath $path -Force
    }
    $directories = @($Installation.ExpectedDirectories.Keys | Sort-Object @{Expression={($_ -split '/').Count}; Descending=$true}, @{Expression={$_}; Descending=$true})
    foreach ($relative in $directories) {
        $path = Join-Path $root ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        $item = Get-Item -LiteralPath $path -Force
        if (-not $item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or @(Get-ChildItem -LiteralPath $path -Force).Count -ne 0) {
            throw "Install tree changed before directory removal: $relative"
        }
        Remove-Item -LiteralPath $path -Force
    }
    $rootItem = Get-Item -LiteralPath $root -Force
    if (($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or @(Get-ChildItem -LiteralPath $root -Force).Count -ne 0) {
        throw 'Install tree changed before root removal.'
    }
    Remove-Item -LiteralPath $root -Force
}

function Remove-UserPathEntry([string]$Entry) {
    $current = [Environment]::GetEnvironmentVariable('Path', 'User')
    $kept = @($current -split ';' | Where-Object {
        if (-not $_ -or -not $_.Trim()) { return $false }
        try { return (Resolve-FullPath $_) -ne $Entry } catch { return $true }
    })
    [Environment]::SetEnvironmentVariable('Path', ($kept -join ';'), 'User')
}

$installation = Get-ValidatedInstallation $InstallRoot
Remove-ValidatedTree $installation
if (-not $NoPathUpdate) { Remove-UserPathEntry $installation.Root }
Write-Output "IntentGraph removed from $($installation.Root)"
