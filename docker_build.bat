@echo off
cls
echo ===================================
echo  Building Docker Image...
echo ===================================
echo.

docker build -t course-recorder .

echo.
echo ===================================
IF %ERRORLEVEL% EQU 0 (
    echo  Build completed successfully!
) ELSE (
    echo  ERROR: Build failed. See messages above.
)
echo ===================================
echo.
pause