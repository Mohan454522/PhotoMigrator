@echo off
echo Installing requirements...
pip install pillow pyinstaller customtkinter tkinterdnd2 pandas openpyxl

echo Converting icon...
python -c "from PIL import Image; Image.open(r'C:\Users\mohan\.gemini\antigravity\brain\0458aea5-99fe-4c27-906a-e6e8148e70f9\photo_migration_icon_1774215719363.png').save('app_icon.ico', format='ICO', sizes=[(256, 256)])"

echo Building executable...
pyinstaller --noconfirm --onedir --windowed --icon "app_icon.ico" --name "PhotoMigrator" --collect-all customtkinter --collect-all tkinterdnd2 "convt2.py"

echo Build complete!
