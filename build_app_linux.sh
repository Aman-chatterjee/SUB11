#!/bin/bash

# Build script for SUB11 Linux app

echo "Checking FFmpeg..."
mkdir -p ffmpeg_bin

if [ -f "ffmpeg_bin/ffmpeg" ] && [ -f "ffmpeg_bin/ffprobe" ]; then
    echo "FFmpeg already downloaded, skipping..."
else
    echo "Downloading FFmpeg..."
    cd ffmpeg_bin
    
    # Download static FFmpeg build for Linux
    wget -O ffmpeg-release-amd64-static.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    
    tar -xf ffmpeg-release-amd64-static.tar.xz --strip-components=1
    rm ffmpeg-release-amd64-static.tar.xz
    
    chmod +x ffmpeg ffprobe
    cd ..
fi

echo "Building SUB11..."
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: pyinstaller not found. Installing..."
    pip install pyinstaller
fi

pyinstaller SUB11_linux.spec --clean

if [ ! -d "dist/SUB11" ]; then
    echo "Error: Build failed. dist/SUB11 not found."
    exit 1
fi

echo "Creating AppImage..."
if command -v appimagetool &> /dev/null; then
    # Create AppDir structure
    mkdir -p SUB11.AppDir/usr/bin
    mkdir -p SUB11.AppDir/usr/share/applications
    mkdir -p SUB11.AppDir/usr/share/icons/hicolor/256x256/apps
    
    # Copy built app
    cp -r dist/SUB11/* SUB11.AppDir/usr/bin/
    
    # Create desktop file
    cat > SUB11.AppDir/SUB11.desktop << EOF
[Desktop Entry]
Type=Application
Name=SUB11
Exec=SUB11
Icon=SUB11
Categories=AudioVideo;
EOF
    
    # Convert icon (if available)
    if [ -f "icon.icns" ] && command -v convert &> /dev/null; then
        convert icon.icns[0] SUB11.AppDir/SUB11.png
    else
        echo "Warning: Icon conversion skipped (ImageMagick not found or icon missing)"
    fi
    
    # Create AppRun
    cat > SUB11.AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin/:${PATH}"
cd "${HERE}/usr/bin"
exec ./SUB11 "$@"
EOF
    chmod +x SUB11.AppDir/AppRun
    
    # Build AppImage
    appimagetool SUB11.AppDir SUB11-x86_64.AppImage
    
    echo "AppImage created: SUB11-x86_64.AppImage"
else
    echo "Warning: appimagetool not found. Skipping AppImage creation."
    echo "Install appimagetool to create portable AppImage."
fi

echo "Build complete!"
echo "Executable: dist/SUB11/SUB11"
if [ -f "SUB11-x86_64.AppImage" ]; then
    echo "AppImage: SUB11-x86_64.AppImage"
fi
echo ""
echo "To run: ./dist/SUB11/SUB11"
if [ -f "SUB11-x86_64.AppImage" ]; then
    echo "Or run AppImage: ./SUB11-x86_64.AppImage"
fi