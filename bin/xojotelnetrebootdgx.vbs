REM Option Explicit
REM On Error Resume Next

Dim WshShell
set WshShell=CreateObject("WScript.Shell")

strPath = Wscript.ScriptFullName
Set objFSO = CreateObject("Scripting.FileSystemObject")		'All this is to get the current directory, assuming telnetUltra and this script are in the same directory
Set objFile = objFSO.GetFile(strPath)
strFolder = objFSO.GetParentFolderName(objFile)

Set args = Wscript.Arguments	'We'll pass the arguments: device IP
IP = args(0)
'Wscript.echo strFolder
WshShell.run "cmd.exe"
WScript.Sleep 1000
WshShell.SendKeys strFolder & "\telnetUltra.exe " & IP
WshShell.SendKeys ("{Enter}")

WScript.Sleep 500
WshShell.SendKeys "administrator"
WScript.Sleep 500
WshShell.SendKeys ("{Enter}")

WScript.Sleep 500
WshShell.SendKeys "password"
WScript.Sleep 500
WshShell.SendKeys ("{Enter}")

WScript.Sleep 500
WshShell.SendKeys "reboot"
WScript.Sleep 500
WshShell.SendKeys ("{Enter}")

WScript.Sleep 30000
WshShell.SendKeys ("{Enter}")
WScript.Sleep 500
WshShell.SendKeys "exit"
WScript.Sleep 500
WshShell.SendKeys ("{Enter}")
WScript.Quit 