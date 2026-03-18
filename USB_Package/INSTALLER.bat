@echo off
chcp 1252 >nul 2>&1
title Installation Inventaire AV
color 0A

echo.
echo  ========================================================
echo     INVENTAIRE AV - Installation / Mise a jour
echo  ========================================================
echo.

set "USB_DIR=%~dp0"
set "INSTALL_DIR=%USERPROFILE%\InventaireAV"
set "IS_UPDATE=0"

:: Detecter si une installation existe deja
if exist "%INSTALL_DIR%\inventaire-app\app\data\inventaire.db" (
    set "IS_UPDATE=1"
    echo  Installation existante detectee dans :
    echo    %INSTALL_DIR%
    echo.
    echo  Mode MISE A JOUR : vos donnees seront conservees.
    echo    - Base de donnees (inventaire.db)
    echo    - Configuration (settings.json)
    echo    - Sauvegardes (backups/)
    echo.
) else (
    echo  Nouvelle installation dans :
    echo    %INSTALL_DIR%
    echo.
)

set /p CONFIRM="  Continuer ? (O/N) : "
if /i "%CONFIRM%" neq "O" exit /b 0

echo.

:: ── Si mise a jour : sauvegarde de securite ──
if "%IS_UPDATE%"=="1" (
    echo [0/5] Sauvegarde de securite des donnees...
    set "BACKUP_TMP=%INSTALL_DIR%\_update_backup"
    if exist "%INSTALL_DIR%\_update_backup" rmdir /S /Q "%INSTALL_DIR%\_update_backup"
    mkdir "%INSTALL_DIR%\_update_backup"

    if exist "%INSTALL_DIR%\inventaire-app\app\data\inventaire.db" (
        mkdir "%INSTALL_DIR%\_update_backup\data" 2>nul
        copy /Y "%INSTALL_DIR%\inventaire-app\app\data\inventaire.db" "%INSTALL_DIR%\_update_backup\data\" >nul
        echo        - Base de donnees sauvegardee.
    )
    if exist "%INSTALL_DIR%\inventaire-app\app\config\settings.json" (
        mkdir "%INSTALL_DIR%\_update_backup\config" 2>nul
        copy /Y "%INSTALL_DIR%\inventaire-app\app\config\settings.json" "%INSTALL_DIR%\_update_backup\config\" >nul
        echo        - Configuration sauvegardee.
    )
    if exist "%INSTALL_DIR%\inventaire-app\app\backups" (
        mkdir "%INSTALL_DIR%\_update_backup\backups" 2>nul
        xcopy /E /I /Y "%INSTALL_DIR%\inventaire-app\app\backups" "%INSTALL_DIR%\_update_backup\backups" >nul
        echo        - Sauvegardes copiees.
    )
    echo.
)

echo [1/5] Creation du dossier d'installation...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo [2/5] Copie de Python embarque...
xcopy /E /I /Y "%USB_DIR%python_embed\python" "%INSTALL_DIR%\python" >nul
echo        - Python copie.

echo [3/5] Copie de l'application...
:: Copier le code (ecrase les anciens fichiers de code)
xcopy /E /I /Y "%USB_DIR%inventaire-app\app\core" "%INSTALL_DIR%\inventaire-app\app\core" >nul
xcopy /E /I /Y "%USB_DIR%inventaire-app\app\ui" "%INSTALL_DIR%\inventaire-app\app\ui" >nul
copy /Y "%USB_DIR%inventaire-app\app\__init__.py" "%INSTALL_DIR%\inventaire-app\app\" >nul
copy /Y "%USB_DIR%inventaire-app\app\main.py" "%INSTALL_DIR%\inventaire-app\app\" >nul
:: Copier les fichiers racine de l'app
copy /Y "%USB_DIR%inventaire-app\requirements.txt" "%INSTALL_DIR%\inventaire-app\" >nul 2>&1
copy /Y "%USB_DIR%inventaire-app\README.md" "%INSTALL_DIR%\inventaire-app\" >nul 2>&1
copy /Y "%USB_DIR%inventaire-app\Lanceur.bat" "%INSTALL_DIR%\inventaire-app\" >nul 2>&1
copy /Y "%USB_DIR%inventaire-app\lanceur.py" "%INSTALL_DIR%\inventaire-app\" >nul 2>&1
:: Copier les defaults de config (sans ecraser settings.json)
if not exist "%INSTALL_DIR%\inventaire-app\app\config" mkdir "%INSTALL_DIR%\inventaire-app\app\config"
copy /Y "%USB_DIR%inventaire-app\app\config\__init__.py" "%INSTALL_DIR%\inventaire-app\app\config\" >nul 2>&1
xcopy /E /I /Y "%USB_DIR%inventaire-app\app\config\defaults" "%INSTALL_DIR%\inventaire-app\app\config\defaults" >nul 2>&1
:: Copier les wheels
xcopy /E /I /Y "%USB_DIR%inventaire-app\wheels" "%INSTALL_DIR%\inventaire-app\wheels" >nul 2>&1
:: Creer les dossiers s'ils n'existent pas
if not exist "%INSTALL_DIR%\inventaire-app\app\data" mkdir "%INSTALL_DIR%\inventaire-app\app\data"
if not exist "%INSTALL_DIR%\inventaire-app\app\backups" mkdir "%INSTALL_DIR%\inventaire-app\app\backups"

:: ── Si mise a jour : restaurer les donnees ──
if "%IS_UPDATE%"=="1" (
    echo        - Code mis a jour.
    echo        Restauration des donnees...
    if exist "%INSTALL_DIR%\_update_backup\data\inventaire.db" (
        copy /Y "%INSTALL_DIR%\_update_backup\data\inventaire.db" "%INSTALL_DIR%\inventaire-app\app\data\" >nul
        echo        - Base de donnees restauree.
    )
    if exist "%INSTALL_DIR%\_update_backup\config\settings.json" (
        copy /Y "%INSTALL_DIR%\_update_backup\config\settings.json" "%INSTALL_DIR%\inventaire-app\app\config\" >nul
        echo        - Configuration restauree.
    )
    if exist "%INSTALL_DIR%\_update_backup\backups" (
        xcopy /E /I /Y "%INSTALL_DIR%\_update_backup\backups" "%INSTALL_DIR%\inventaire-app\app\backups" >nul
        echo        - Sauvegardes restaurees.
    )
    rmdir /S /Q "%INSTALL_DIR%\_update_backup" 2>nul
) else (
    echo        - Application copiee.
    :: Premiere installation : copier settings.json par defaut
    if not exist "%INSTALL_DIR%\inventaire-app\app\config\settings.json" (
        copy /Y "%USB_DIR%inventaire-app\app\config\settings.json" "%INSTALL_DIR%\inventaire-app\app\config\" >nul 2>&1
    )
)

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
if "%IS_UPDATE%"=="1" (
    echo  ========================================================
    echo     Mise a jour terminee !
    echo  ========================================================
    echo.
    echo  Vos donnees ont ete conservees.
) else (
    echo  ========================================================
    echo     Installation terminee !
    echo  ========================================================
)
echo.
echo  - Raccourci "Inventaire AV" sur le Bureau
echo  - Dossier : %INSTALL_DIR%
echo.
echo  Double-cliquez sur le raccourci pour demarrer.
echo.
pause
