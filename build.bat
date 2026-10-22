@echo off
rem ---------------------------------------------------------------------------
rem  Builds the C++ parking core with g++ (MSYS2 UCRT64 / MinGW-w64) when CMake
rem  is not installed.  Output: build\parkinglot.exe and build\parking_tests.exe
rem
rem    build.bat          build both executables
rem    build.bat test     build, then run the unit tests
rem
rem  With CMake installed, prefer:  cmake -S . -B build  &&  cmake --build build
rem ---------------------------------------------------------------------------
setlocal EnableDelayedExpansion
cd /d "%~dp0"

where g++ >nul 2>nul
if errorlevel 1 (
    echo g++ was not found on PATH. Install MSYS2 UCRT64 ^(pacman -S mingw-w64-ucrt-x86_64-gcc^)
    echo and add C:\msys64\ucrt64\bin to PATH, or build with CMake + Visual Studio.
    exit /b 1
)

set "CORE="
for /r src %%f in (*.cpp) do (
    set "NAME=%%~nxf"
    if /i not "!NAME!"=="main.cpp" if /i not "!NAME:~0,5!"=="MySql" set CORE=!CORE! "%%f"
)
set "TESTS="
for %%f in (tests\*.cpp) do set TESTS=!TESTS! "%%f"

if not exist build mkdir build
set "FLAGS=-std=c++17 -O2 -Wall -Wextra -Wpedantic -Wshadow -Isrc"

echo Building build\parkinglot.exe ...
g++ %FLAGS% !CORE! src\main.cpp -static -o build\parkinglot.exe
if errorlevel 1 exit /b 1

echo Building build\parking_tests.exe ...
g++ %FLAGS% -Itests !CORE! !TESTS! -static -o build\parking_tests.exe
if errorlevel 1 exit /b 1

echo Done.
if /i "%~1"=="test" (
    build\parking_tests.exe
    exit /b !errorlevel!
)
exit /b 0
