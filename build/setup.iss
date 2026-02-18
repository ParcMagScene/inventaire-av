; ═══════════════════════════════════════════════
; setup.iss — Script Inno Setup pour Inventaire AV
; ═══════════════════════════════════════════════
;
; Prérequis :
;   - Inno Setup 6.x installé
;   - L'EXE a été généré via PyInstaller dans dist/
;
; Compilation :
;   Ouvrir ce fichier dans Inno Setup Compiler → Build

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=Inventaire AV
AppVersion=1.0.0
AppVerName=Inventaire AV 1.0.0
AppPublisher=Inventaire AV
AppPublisherURL=https://github.com/inventaire-av
DefaultDirName={autopf}\InventaireAV
DefaultGroupName=Inventaire AV
AllowNoIcons=yes
; Chemin de sortie du setup.exe
OutputDir=..\dist\installer
OutputBaseFilename=InventaireAV_Setup_1.0.0
; Icône du setup
SetupIconFile=..\app\ui\icons\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Désinstallation
UninstallDisplayIcon={app}\InventaireAV.exe
UninstallDisplayName=Inventaire AV

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked
Name: "startmenuicon"; Description: "Créer un raccourci dans le menu Démarrer"; GroupDescription: "Raccourcis :"

[Files]
; EXE principal généré par PyInstaller
Source: "..\dist\InventaireAV.exe"; DestDir: "{app}"; Flags: ignoreversion

; Données de configuration (seront copiées si absentes)
Source: "..\app\config\settings.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist
Source: "..\app\config\defaults\*"; DestDir: "{app}\config\defaults"; Flags: ignoreversion recursesubdirs

; Icônes
Source: "..\app\ui\icons\*"; DestDir: "{app}\icons"; Flags: ignoreversion recursesubdirs

; Thème
Source: "..\app\ui\styles_dark.qss"; DestDir: "{app}\ui"; Flags: ignoreversion

[Icons]
Name: "{group}\Inventaire AV"; Filename: "{app}\InventaireAV.exe"
Name: "{group}\Désinstaller Inventaire AV"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Inventaire AV"; Filename: "{app}\InventaireAV.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\InventaireAV.exe"; Description: "Lancer Inventaire AV"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
// Installation silencieuse supportée via /SILENT ou /VERYSILENT
