"""
Build script for PSA packaging
Run: python build.py
"""

import os
import shutil
import subprocess
import sys

def clean_build():
    """Clean previous build artifacts"""
    print(" Cleaning previous builds...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Removed {dir_name}/")
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def build_exe():
    """Build executable using PyInstaller"""
    print(" Building PSA executable...")
    
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'psa.spec'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Build successful!")
        print(f" Executable created in: dist/PSA.exe")
        return True
    else:
        print(" Build failed!")
        print(result.stderr)
        return False

def create_release_package():
    """Create release package with necessary files"""
    print(" Creating release package...")
    
    release_dir = "PSA_v2.0_Release"
    
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    
    os.makedirs(release_dir)
    
    # Copy executable
    shutil.copy('dist/PSA.exe', release_dir)
    
    # Create README
    readme = """
# PSA v2.0 - Personal Smart Assistant

## Installation

1. Extract this folder anywhere
2. Double-click PSA.exe to run
3. Create an account on first launch

## Features

-  Automatic memory learning
-  Web search
-  Image analysis
-  Voice input
-  Conversation export
-  Pin & favorite chats
-  Encrypted local storage

## System Requirements

- Windows 10/11
- 4GB RAM minimum
- Internet connection for web features

## Support

Email: nandngroupoftech@gmail.com

## Created by Nachiketh Guduri
    """
    
    with open(os.path.join(release_dir, 'README.txt'), 'w') as f:
        f.write(readme)
    
    # Create ZIP
    print(" Creating ZIP archive...")
    shutil.make_archive('PSA_v2.0_Release', 'zip', release_dir)
    
    print(f" Release package created: PSA_v2.0_Release.zip")
    print(f" Size: {os.path.getsize('PSA_v2.0_Release.zip') / 1024 / 1024:.1f} MB")

def main():
    """Main build process"""
    print("=" * 50)
    print("PSA v2.0 Build Script")
    print("=" * 50)
    print()
    
    # Step 1: Clean
    clean_build()
    print()
    
    # Step 2: Build
    if not build_exe():
        print(" Build failed. Exiting.")
        sys.exit(1)
    print()
    
    # Step 3: Package
    create_release_package()
    print()
    
    print("=" * 50)
    print(" BUILD COMPLETE!")
    print("=" * 50)
    print()
    print(" Ready to distribute:")
    print("   → PSA_v2.0_Release.zip")
    print()

    print()

if __name__ == "__main__":
    main()