param()
$ErrorActionPreference = 'Stop'
$launcherProject = Split-Path -Parent $PSScriptRoot
$compilerCandidates = @(
    (Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'),
    (Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe')
)
$launcherCompiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $launcherCompiler) { throw 'The Windows .NET Framework C# compiler is missing.' }
$launcherSource = Join-Path $PSScriptRoot 'SoundDetectiveLauncher.cs'
$launcherBuildDirectory = Join-Path $launcherProject '.runtime/launcher-build'
$launcherOutput = Join-Path $launcherProject 'SoundDetective.exe'
New-Item -ItemType Directory -Path $launcherBuildDirectory -Force | Out-Null
$launcherBuild = Join-Path $launcherBuildDirectory 'SoundDetective.exe'
$compilerArguments = @('/nologo', '/target:winexe', '/platform:anycpu', '/optimize+', '/codepage:65001',
    '/reference:System.Windows.Forms.dll', ('/out:' + $launcherBuild), $launcherSource)
& $launcherCompiler @compilerArguments
if ($LASTEXITCODE -ne 0) { throw "C# compilation failed: $LASTEXITCODE" }
Copy-Item -LiteralPath $launcherBuild -Destination $launcherOutput -Force
Get-Item -LiteralPath $launcherOutput | Select-Object FullName, Length, LastWriteTime
