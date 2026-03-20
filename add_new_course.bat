@echo off
cls
echo ========================================
echo  New Course Setup Wizard
echo ========================================
echo This script will create all necessary files and folders for a new course.
echo.

:askCourseName
set "courseName="
set /p courseName="[1/4] Enter a short name for the course (e.g., ai, java, python): "
if "%courseName%"=="" (
    echo ERROR: Course name cannot be empty.
    goto askCourseName
)

if exist "config_course_%courseName%" (
    echo.
    echo WARNING: A configuration for '%courseName%' already exists.
    echo Aborting to prevent overwriting data.
    echo.
    pause
    exit /b
)

:askEmail
set "userEmail="
set /p userEmail="[2/4] Enter the login (email) for this course: "
if "%userEmail%"=="" (
    echo ERROR: Email cannot be empty.
    goto askEmail
)

:askPassword
set "userPassword="
set /p userPassword="[3/4] Enter the password for this course: "
if "%userPassword%"=="" (
    echo ERROR: Password cannot be empty.
    goto askPassword
)

echo.
echo "[4/4] Enter video URLs one by one. Type 'done' and press Enter when finished."

mkdir "config_course_%courseName%"
mkdir "video_recordings_%courseName%"

(
    echo MY_EMAIL="%userEmail%"
    echo MY_PASSWORD="%userPassword%"
) > "config_course_%courseName%\.env"

:url_loop
set "urlInput="
set /p urlInput="URL> "
if /i "%urlInput%"=="done" goto end_url_loop
if "%urlInput%"=="" goto url_loop
echo %urlInput%>> "config_course_%courseName%\urls.txt"
goto url_loop
:end_url_loop

REM --- ИСПРАВЛЕНИЕ: Экранируем все символы ^, чтобы они записались в файл ---
(
    echo @echo off
    echo cls
    echo ===================================
    echo  Running Video Recorder for course: %courseName%
    echo ===================================
    echo.
    echo Starting container...
    echo ===================================
    echo.
    echo docker run --rm -it ^^
    echo   -v "%%cd%%\config_course_%courseName%\.env:/app/.env" ^^
    echo   -v "%%cd%%\config_course_%courseName%\urls.txt:/app/urls.txt" ^^
    echo   -v "%%cd%%\video_recordings_%courseName%:/app/video_recordings" ^^
    echo   course-recorder
    echo.
    echo ===================================
    echo  Container finished its work.
    echo ===================================
    echo.
    echo pause
) > "docker_run_%courseName%.bat"

echo.
echo ========================================
echo  SUCCESS! Setup for course '%courseName%' is complete.
echo ========================================
echo.
echo Created:
echo  - Folder: config_course_%courseName% (with .env and urls.txt)
echo  - Folder: video_recordings_%courseName%
echo  - Run script: docker_run_%courseName%.bat
echo.
echo You can now run the new script to start recording.
echo.
pause