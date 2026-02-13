@echo off
echo Building Squat Reminder...
python -m PyInstaller --onefile --noconsole --windowed ^
  --name SquatReminder ^
  --icon icon.ico ^
  --add-data "src\assets\overlay.html;assets" ^
  --add-data "src\assets\font.ttf;assets" ^
  --add-data "thunder_sfx.mp3;." ^
  --add-data "music\*.mp3;music" ^
  --hidden-import webview ^
  --hidden-import pystray ^
  --hidden-import PIL ^
  --hidden-import pygame.mixer ^
  --hidden-import psutil ^
  src\main.py
echo.
echo Build complete! Executable at: dist\SquatReminder.exe
pause
