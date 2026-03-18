Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strUSB = fso.GetParentFolderName(WScript.ScriptFullName)
strPython = strUSB & "\python_embed\python\pythonw.exe"
strCheck = strUSB & "\python_embed\python\python.exe"
strApp = strUSB & "\inventaire-app"
WshShell.CurrentDirectory = strApp

' 1) Installer pip si necessaire (AVANT tout)
strGetPip = strUSB & "\python_embed\python\get-pip.py"
If fso.FileExists(strGetPip) Then
    WshShell.Run """"& strCheck &""" """ & strGetPip & """ --no-warn-script-location", 1, True
    fso.DeleteFile strGetPip
End If

' 2) Verifier si PySide6 est installe
Set oExec = WshShell.Exec(""""& strCheck &""" -c ""import PySide6""")
Do While oExec.Status = 0
    WScript.Sleep 100
Loop
If oExec.ExitCode <> 0 Then
    ' 3) Installer les dependances depuis les wheels
    strPip = """"& strCheck &""" -m pip install --no-index --find-links=""" & strApp & "\wheels"" -r """ & strApp & "\requirements.txt"" --no-warn-script-location"
    WshShell.Run strPip, 1, True
End If

' 4) Lancer l application (invisible)
WshShell.Run """"& strPython &""" -m app.main", 0, False
