@echo off
title HD ASCII Video Player - Launcher

:MENU
cls
echo ========================================================
echo           ASCII VIDEO PLAYER - SETTINGS
echo ========================================================
echo.
set "VIDEO=video.mp4"
set /p "VIDEO=Enter video filename [Enter = video.mp4]: "

echo.
echo Select visual filter:
echo   1 - Original colors (default)
echo   2 - Matrix (phosphor green)
echo   3 - Cyberpunk (neon magenta-cyan)
echo   4 - Amber CRT monitor
echo   5 - Black & White monochrome
echo.
set "F_CHOICE=1"
set /p "F_CHOICE=Your choice [1-5]: "

set "FILTER=none"
if "%F_CHOICE%"=="2" set "FILTER=matrix"
if "%F_CHOICE%"=="3" set "FILTER=cyberpunk"
if "%F_CHOICE%"=="4" set "FILTER=amber"
if "%F_CHOICE%"=="5" set "FILTER=bw"

echo.
echo Select character set:
echo   1 - Ultra (maximum detail, 70 chars)
echo   2 - Hacker (brackets and symbols focus [';&)
echo   3 - Standard (classic)
echo.
set "C_CHOICE=1"
set /p "C_CHOICE=Your choice [1-3]: "

set "CHARSET=ultra"
if "%C_CHOICE%"=="2" set "CHARSET=hacker"
if "%C_CHOICE%"=="3" set "CHARSET=standard"

echo.
echo Starting... (Controls: Space = Pause, Left/Right = Seek, F = Filter, C = Charset, +/- = Saturation, Q = Quit)
py main.py "%VIDEO%" --charset %CHARSET% --filter %FILTER% --font-size 4 --loop

goto MENU