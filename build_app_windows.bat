@echo off
REM Build script for SUB11 Windows app

echo Checking FFmpeg...
if not exist "ffmpeg_bin" mkdir ffmpeg_bin

if exist "ffmpeg_bin\ffmpeg.exe" if exist "ffmpeg_bin\ffprobe.exe" (
    echo FFmpeg already downloaded, skipping...
) else (
    echo Downloading FFmpeg...
    cd ffmpeg_bin
    
    REM Download static FFmpeg build for Windows
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg.zip'"
    
    powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath '.' -Force"
    
    REM Move binaries from extracted folder
    for /d %%i in (ffmpeg-*) do (
        move "%%i\bin\ffmpeg.exe" .
        move "%%i\bin\ffprobe.exe" .
        rmdir /s /q "%%i"
    )
    
    del ffmpeg.zip
    cd ..
)

echo Building SUB11...
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: pyinstaller not found. Installing...
    pip install pyinstaller
)

pyinstaller SUB11_windows.spec --clean

if not exist "dist\SUB11" (
    echo Error: Build failed. dist\SUB11 not found.
    exit /b 1
)

echo Creating installer...
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    echo Creating NSIS installer...
    "C:\Program Files (x86)\NSIS\makensis.exe" SUB11_installer.nsi
    echo Installer created: SUB11-Setup.exe
) else (
    echo Warning: NSIS not found. Skipping installer creation.
    echo Install NSIS to create Windows installer.
)

echo Build complete!
echo Executable: dist\SUB11\SUB11.exe
if exist "SUB11-Setup.exe" (
    echo Installer: SUB11-Setup.exe
)
echo.
echo To run: dist\SUB11\SUB11.exe
pause