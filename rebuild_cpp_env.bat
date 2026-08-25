@echo off
setlocal enabledelayedexpansion

REM -----------------------------------------------------------------------------
REM Unreal C++ one-click cleanup/regenerate/build script
REM Usage:
REM   - Double click this file in project root
REM   - Optional engine path parameter:
REM       rebuild_cpp_env.bat "F:\3_UE_Editor\UE_5.8"
REM -----------------------------------------------------------------------------

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "UPROJECT=%PROJECT_DIR%\InteractiveGrassMy.uproject"
set "PROJECT_NAME=InteractiveGrassMy"

if not exist "%UPROJECT%" (
    echo [ERROR] Could not find uproject:
    echo         %UPROJECT%
    pause
    exit /b 1
)

if "%~1"=="" (
    set "UE_ROOT=F:\3_UE_Editor\UE_5.8"
) else (
    set "UE_ROOT=%~1"
)

set "GEN_BAT=%UE_ROOT%\Engine\Build\BatchFiles\GenerateProjectFiles.bat"
set "BUILD_BAT=%UE_ROOT%\Engine\Build\BatchFiles\Build.bat"

if not exist "%BUILD_BAT%" (
    echo [ERROR] Build.bat not found:
    echo         %BUILD_BAT%
    pause
    exit /b 1
)

set "CAN_USE_GEN_BAT=0"
if exist "%GEN_BAT%" set "CAN_USE_GEN_BAT=1"

echo =========================================================
echo Project : %PROJECT_NAME%
echo UProject: %UPROJECT%
echo UE Root : %UE_ROOT%
if "%CAN_USE_GEN_BAT%"=="1" (
echo Gen PF  : GenerateProjectFiles.bat
) else (
echo Gen PF  : Build.bat -projectfiles (fallback)
)
echo =========================================================
echo.

echo [1/5] Closing UnrealEditor/UBT if running...
taskkill /f /im UnrealEditor.exe >nul 2>nul
taskkill /f /im UnrealBuildTool.exe >nul 2>nul
taskkill /f /im ShaderCompileWorker.exe >nul 2>nul

echo [2/5] Cleaning generated folders/files...
if exist "%PROJECT_DIR%\.vs" rmdir /s /q "%PROJECT_DIR%\.vs"
if exist "%PROJECT_DIR%\Binaries" rmdir /s /q "%PROJECT_DIR%\Binaries"
if exist "%PROJECT_DIR%\Intermediate" rmdir /s /q "%PROJECT_DIR%\Intermediate"
if exist "%PROJECT_DIR%\DerivedDataCache" rmdir /s /q "%PROJECT_DIR%\DerivedDataCache"
if exist "%PROJECT_DIR%\Saved\Logs" rmdir /s /q "%PROJECT_DIR%\Saved\Logs"
if exist "%PROJECT_DIR%\%PROJECT_NAME%.sln" del /f /q "%PROJECT_DIR%\%PROJECT_NAME%.sln"

echo [3/5] Regenerating Visual Studio project files...
if "%CAN_USE_GEN_BAT%"=="1" (
    call "%GEN_BAT%" -project="%UPROJECT%" -game -engine
) else (
    call "%BUILD_BAT%" -projectfiles -project="%UPROJECT%" -game -engine
)
if errorlevel 1 (
    echo [ERROR] GenerateProjectFiles failed.
    pause
    exit /b 1
)

echo [4/5] Building Editor target...
call "%BUILD_BAT%" %PROJECT_NAME%Editor Win64 Development -Project="%UPROJECT%" -WaitMutex -FromMsBuild -architecture=x64
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo [5/5] Done.
echo.
echo Success: C++ environment rebuilt.
echo You can now open:
echo   %PROJECT_DIR%\%PROJECT_NAME%.sln
echo.
pause
exit /b 0
