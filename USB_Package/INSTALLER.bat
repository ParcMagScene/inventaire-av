@echo off
chcp 1252 >nul 2>&1
title Installation Inventaire AV
color 0A

echo.
echo  ========================================================
echo     INVENTAIRE AV - Installation depuis USB
echo  ========================================================
echo.
echo  Ce programme va installer Inventaire AV sur votre PC.
echo.

set "USB_DIR=%~dp0"
set "INSTALL_DIR=%USERPROFILE%\InventaireAV"

echo  Dossier d'installation : %INSTALL_DIR%
echo.
set /p CONFIRM="  Continuer ? (O/N) : "
if /i "%CONFIRM%" neq "O" exit /b 0

echo.
echo [1/5] Creation du dossier d'installation...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo [2/5] Copie de Python embarque...
xcopy /E /I /Y "%USB_DIR%python_embed\python" "%INSTALL_DIR%\python" >nul
echo        - Python copie.

echo [3/5] Copie de l'application...
xcopy /E /I /Y "%USB_DIR%inventaire-app" "%INSTALL_DIR%\inventaire-app" >nul
if not exist "%INSTALL_DIR%\inventaire-app\app\backups" mkdir "%INSTALL_DIR%\inventaire-app\app\backups"
echo        - Application copiee.

:: Mettre a jour le fichier ._pth avec le chemin absolu de l'app
for %%F in ("%INSTALL_DIR%\python\python*._pth") do (
    echo python311.zip> "%%F"
    echo .>> "%%F"
    echo %INSTALL_DIR%\inventaire-app>> "%%F"
    echo import site>> "%%F"
)
echo        - Chemin Python configure.

echo [4/5] Installation des dependances...

if exist "%INSTALL_DIR%\python\get-pip.py" (
    "%INSTALL_DIR%\python\python.exe" "%INSTALL_DIR%\python\get-pip.py" --no-warn-script-location >nul 2>&1
    del "%INSTALL_DIR%\python\get-pip.py" 2>nul
)

"%INSTALL_DIR%\python\python.exe" -m pip install --no-index --find-links="%INSTALL_DIR%\inventaire-app\wheels" -r "%INSTALL_DIR%\inventaire-app\requirements.txt" --no-warn-script-location >nul 2>&1
echo        - Dependances installees.

echo [5/5] Creation du raccourci Bureau...

set "VBS_FILE=%TEMP%\inventaire_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Inventaire AV.lnk" >> "%VBS_FILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_FILE%"
echo oLink.TargetPath = "%INSTALL_DIR%\python\pythonw.exe" >> "%VBS_FILE%"
echo oLink.Arguments = "-m app.main" >> "%VBS_FILE%"
echo oLink.WorkingDirectory = "%INSTALL_DIR%\inventaire-app" >> "%VBS_FILE%"
echo oLink.Description = "Inventaire AV" >> "%VBS_FILE%"
echo oLink.WindowStyle = 1 >> "%VBS_FILE%"
echo oLink.Save >> "%VBS_FILE%"
cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%" 2>nul
echo        - Raccourci cree sur le Bureau.

:: Lanceur VBS invisible (pas de fenetre cmd)
set "VBSLAUNCHER=%INSTALL_DIR%\Lancer_InventaireAV.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%VBSLAUNCHER%"
echo WshShell.CurrentDirectory = "%INSTALL_DIR%\inventaire-app" >> "%VBSLAUNCHER%"
echo WshShell.Run Chr(34) ^& "%INSTALL_DIR%\python\pythonw.exe" ^& Chr(34) ^& " -m app.main", 0, False >> "%VBSLAUNCHER%"

echo.
echo  ========================================================
echo     Installation terminee !
echo  ========================================================
echo.
echo  - Raccourci "Inventaire AV" cree sur le Bureau
echo  - Dossier : %INSTALL_DIR%
echo.
echo  Double-cliquez sur le raccourci pour demarrer.
echo.
pause
