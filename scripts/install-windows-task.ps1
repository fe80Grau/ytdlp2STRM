# Registers a per-user, least-privilege task at sign-in; never starts the app.
# -WhatIf / -DryRun validate inputs and print XML without changing files/tasks.
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [ValidatePattern('^[A-Za-z0-9_.-]+$')][string]$TaskName = 'ytdlp2STRM',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'

foreach ($path in @($ProjectPath, $PythonExe)) {
    # cmd expands percent variables even inside quotes. Reject ambiguous input.
    if ($path -notmatch '^[A-Za-z]:[\\/]' -or $path -match '[%"\r\n]') {
        throw 'ProjectPath and PythonExe must be absolute local paths without %, quotes or newlines.'
    }
}
$ProjectPath = (Get-Item -LiteralPath $ProjectPath).FullName
$PythonExe = (Get-Item -LiteralPath $PythonExe).FullName
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf) -or
    [IO.Path]::GetFileName($PythonExe) -ine 'python.exe') {
    throw 'PythonExe must point to python.exe (not pythonw.exe or the py launcher).'
}
foreach ($relative in @('main.py', 'scripts\start-windows.cmd')) {
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath $relative) -PathType Leaf)) {
        throw "Missing project file: $relative"
    }
}
# Validate the interpreter without importing main.py, dependencies or crons.
& $PythonExe -c 'import sys; assert sys.version_info.major == 3, "Python 3 is required"'
if ($LASTEXITCODE -ne 0) { throw "Python validation failed: exit code $LASTEXITCODE" }

[xml]$task = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\config\MS-TASK-ytdlp2STRM.xml') -Raw
$ns = $task.DocumentElement.NamespaceURI
$user = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
# InteractiveToken needs a logged-on user, so pair it with sign-in, not boot.
$triggers = $task.Task.Triggers
$triggers.RemoveAll()
$trigger = $task.CreateElement('LogonTrigger', $ns)
[void]$triggers.AppendChild($trigger)
$trigger.InnerXml = "<Enabled>true</Enabled><UserId>$user</UserId>"
$principals = $task.CreateElement('Principals', $ns)
[void]$task.Task.InsertBefore($principals, $task.Task.Settings)
$principals.InnerXml = "<Principal id='Author'><UserId>$user</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal>"
$task.Task.Actions.SetAttribute('Context', 'Author')
$task.Task.RegistrationInfo.URI = "\$TaskName"
$task.GetElementsByTagName('Command')[0].InnerText = [string](Join-Path $env:SystemRoot 'System32\cmd.exe')
$launcher = Join-Path $ProjectPath 'scripts\start-windows.cmd'
$task.Task.Actions.Exec.Arguments = '/d /s /c ""{0}" "{1}""' -f $launcher, $PythonExe
$task.Task.Actions.Exec.WorkingDirectory = $ProjectPath
# Return only the XML element, avoiding an encoding declaration for console text.
$xml = $task.DocumentElement.OuterXml
if ($DryRun -or $WhatIfPreference) { Write-Output $xml; return }

if ($PSCmdlet.ShouldProcess($TaskName, 'Register sign-in task for the current user')) {
    if (Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction SilentlyContinue) {
        throw "Task '$TaskName' already exists. Review it manually or choose a different -TaskName."
    }
    # Deliberately no -Force; never silently replace an existing installation.
    Register-ScheduledTask -TaskName $TaskName -TaskPath '\' -Xml $xml | Out-Null
    # Read back the exact target after registration. Do not launch the application.
    Get-ScheduledTask -TaskName $TaskName -TaskPath '\'
}
