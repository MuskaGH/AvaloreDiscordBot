Option Explicit

Dim WshShell, Fso, ScriptDir, BotScript, Pythonw, Command

Set WshShell = CreateObject("WScript.Shell")
Set Fso = CreateObject("Scripting.FileSystemObject")

ScriptDir = Fso.GetParentFolderName(WScript.ScriptFullName)
BotScript = Fso.BuildPath(ScriptDir, "bot_gui.py")
Pythonw = Fso.BuildPath(WshShell.ExpandEnvironmentStrings("%LocalAppData%"), "Programs\Python\Python314\pythonw.exe")

If Not Fso.FileExists(Pythonw) Then
    Pythonw = "pythonw.exe"
End If

WshShell.CurrentDirectory = ScriptDir
Command = Chr(34) & Pythonw & Chr(34) & " " & Chr(34) & BotScript & Chr(34)

On Error Resume Next
WshShell.Run Command, 1, False

If Err.Number <> 0 Then
    MsgBox "Could not start Avalore Discord Bot." & vbCrLf & vbCrLf & _
        "Command: " & Command & vbCrLf & _
        "Error: " & Err.Description, vbCritical, "Avalore Bot"
End If

Set Fso = Nothing
Set WshShell = Nothing
