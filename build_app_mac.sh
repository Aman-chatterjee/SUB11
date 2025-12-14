#!/bin/bash

# Build script for SUB11 macOS app

echo "Checking FFmpeg..."
mkdir -p ffmpeg_bin

if [ -f "ffmpeg_bin/ffmpeg" ] && [ -f "ffmpeg_bin/ffprobe" ]; then
    echo "FFmpeg already downloaded, skipping..."
else
    echo "Downloading FFmpeg..."
    cd ffmpeg_bin
    
    # Download static FFmpeg build
    curl -L https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip -o ffmpeg.zip
    curl -L https://evermeet.cx/ffmpeg/ffprobe-6.1.zip -o ffprobe.zip
    
    unzip -o ffmpeg.zip
    unzip -o ffprobe.zip
    rm ffmpeg.zip ffprobe.zip
    
    chmod +x ffmpeg ffprobe
    cd ..
fi

echo "Building SUB11..."
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: pyinstaller not found. Installing..."
    pip install pyinstaller
fi

pyinstaller SUB11_mac.spec --clean

if [ ! -d "dist/SUB11.app" ]; then
    echo "Error: Build failed. dist/SUB11.app not found."
    exit 1
fi

# Optional: Code sign the app (requires Apple Developer account)
# Uncomment these lines if you have a signing certificate:
# echo "Code signing app..."
# codesign --force --deep --sign "Developer ID Application: Your Name" dist/SUB11.app

echo "Creating DMG installer..."
if [ -d "dist/SUB11.app" ]; then
    hdiutil create -volname "SUB11" -srcfolder dist/SUB11.app -ov -format UDZO dist/SUB11.dmg
else
    echo "Error: Cannot create DMG, app not found."
    exit 1
fi

# Optional: Notarize DMG (requires Apple Developer account)
# xcrun notarytool submit dist/SUB11.dmg --apple-id "your@email.com" --password "app-specific-password" --team-id "TEAMID" --wait

echo "Build complete!"
echo "App: dist/SUB11.app"
echo "Installer: dist/SUB11.dmg"
echo ""
echo "⚠️  Note: App is not code-signed. Users must right-click → Open on first launch."
echo "To distribute widely, get an Apple Developer account ($99/year) and code-sign."
