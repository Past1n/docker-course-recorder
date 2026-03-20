import subprocess
import time
import os
import re
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# ==============================================================================
# --- CONFIGURATION ---
# ==============================================================================
LOGIN_URL = "https://edu.genius.space/uk/login"
EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("MY_PASSWORD")
AUDIO_DEVICE_NAME = "CABLE Output (VB-Audio Virtual Cable)"  # For Windows local execution
DOWNLOAD_FOLDER = "video_recordings"

# Read video URLs from an external file
try:
    with open("urls.txt", "r", encoding="utf-8") as f:
        VIDEO_URLS = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    VIDEO_URLS = []

# --- SCRIPT SETTINGS ---
TEST_MODE = True
TEST_DURATION_SECONDS = 15
PLAYBACK_SPEED = 1.25


# --- HELPER FUNCTIONS ---
def parse_duration_to_seconds(duration_str):
    """Converts a time string (HH:MM:SS or MM:SS) to total seconds."""
    try:
        parts = list(map(int, duration_str.split(':')))
        seconds = 0
        if len(parts) == 3:
            seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            seconds = parts[0] * 60 + parts[1]
        return seconds
    except (ValueError, AttributeError):
        return 0


def js_click(driver, element):
    """Executes a click using JavaScript to bypass potential visibility issues."""
    driver.execute_script("arguments[0].click();", element)


def hide_cursor(driver):
    """Injects CSS to hide the mouse cursor on the page."""
    try:
        driver.execute_script("""
            var style = document.createElement('style');
            style.type = 'text/css';
            style.innerHTML = '* { cursor: none !important; }';
            document.head.appendChild(style);
        """)
    except Exception:
        pass


def set_highest_quality(driver, wait, actions):
    """Finds and sets the highest available video quality (up to 1080p)."""
    try:
        print("   - Setting video quality...")
        quality_button_selector = 'button.video-player-navigation-button:has(path[d^="M4.5 1a"])'
        quality_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, quality_button_selector)))
        actions.move_to_element(quality_button).perform()
        time.sleep(0.5)

        quality_options_elements = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//button[contains(@class, 'video-player-navigation-button-modal-item')]")))

        available_qualities = {}
        for element in quality_options_elements:
            text = element.text.strip().lower()
            if 'p' in text:
                try:
                    quality_num = int(text.replace('p', ''))
                    available_qualities[quality_num] = element
                except ValueError:
                    continue

        if not available_qualities:
            print("     - No quality options found.")
            actions.move_to_element(quality_button).perform()
            return

        best_quality = 0
        for q in available_qualities.keys():
            if q <= 1080 and q > best_quality:
                best_quality = q

        if best_quality == 0:
            print("     - No suitable quality (<=1080p) found.")
            actions.move_to_element(quality_button).perform()
            return

        element_to_click = available_qualities[best_quality]
        js_click(driver, element_to_click)
        print(f"   - Quality set to {best_quality}p.")
        time.sleep(3)  # Allow time for the stream to switch

    except TimeoutException:
        print("   - WARNING: Quality settings button not found. Continuing with default.")


# --- MAIN SCRIPT ---
def main():
    if not os.path.exists(DOWNLOAD_FOLDER): os.makedirs(DOWNLOAD_FOLDER)

    if not VIDEO_URLS: print("URL list is empty. Exiting."); return
    if not EMAIL or not PASSWORD: print(
        "ERROR: EMAIL/PASSWORD not found in .env file. Please check your configuration."); return

    # Determine the execution environment (local Windows vs. Docker/Linux)
    is_docker = platform.system() == "Linux"

    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    if is_docker:
        print("--- Running in Docker (Linux) mode ---")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--kiosk")  # True fullscreen mode without window decorations
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=options)
    else:
        print("--- Running in local (Windows) mode ---")
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # 1. Authentication
    print("1. Authenticating...")
    driver.get(LOGIN_URL)
    hide_cursor(driver)
    time.sleep(3)
    driver.find_element(By.NAME, "login").send_keys(EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, ".main-button").click()
    time.sleep(5)
    print("Authentication successful.")

    successful_videos = []
    failed_videos = []

    # 2. Main recording loop
    for i, url in enumerate(VIDEO_URLS, 1):
        recorder_process = None
        try:
            print(f"\n--- Processing video {i}/{len(VIDEO_URLS)}: {url} ---")
            driver.get(url)
            hide_cursor(driver)
            time.sleep(7)
            wait = WebDriverWait(driver, 20)
            actions = ActionChains(driver)

            try:
                print("1. Configuring player settings (speed and quality)...")
                video_container = driver.find_element(By.CSS_SELECTOR, ".video-player-pseudo")
                actions.move_to_element(video_container).perform()
                time.sleep(1)

                print("   - Setting playback speed...")
                speed_button_selector = 'button.video-player-navigation-button:has(path[d^="M13 2.05"])'
                speed_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, speed_button_selector)))
                actions.move_to_element(speed_button).perform()
                time.sleep(0.5)

                speed_option_xpath = f"//button[contains(@class, 'video-player-navigation-button-modal-item')][contains(., '{PLAYBACK_SPEED}')]"
                speed_option = wait.until(EC.element_to_be_clickable((By.XPATH, speed_option_xpath)))
                js_click(driver, speed_option)
                print(f"   - Speed set to {PLAYBACK_SPEED}x.")
                time.sleep(1)

                set_highest_quality(driver, wait, actions)

            except TimeoutException:
                print("   - WARNING: Could not find player settings. Continuing with defaults.")

            print("2. Entering fullscreen mode...")
            fullscreen_button_selector = 'button.video-player-navigation-button:has(path[d^="M4 15a1"])'
            fullscreen_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, fullscreen_button_selector)))
            actions.move_to_element(fullscreen_button).click().perform()
            time.sleep(2)

            print("3. Starting video to get duration...")
            initial_play_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".video-player-play-button")))
            js_click(driver, initial_play_button)
            time.sleep(3)

            print("4. Pausing and retrieving duration...")
            video_container = driver.find_element(By.CSS_SELECTOR, ".video-player-pseudo")
            actions.move_to_element(video_container).perform()
            time.sleep(1)

            control_panel_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".video-player-navigation-button:nth-of-type(1)")))
            js_click(driver, control_panel_button)  # Pauses the video
            time.sleep(1)

            duration_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".video-player-time span:nth-child(2)")))
            duration_text = duration_element.text.strip()
            record_seconds = parse_duration_to_seconds(duration_text)

            if record_seconds < 5:
                raise Exception("Failed to retrieve valid video duration.")

            print(f"   - Full video duration: {duration_text} ({record_seconds} seconds).")

            if TEST_MODE:
                record_seconds = TEST_DURATION_SECONDS
                print(f"   - *** TEST MODE ENABLED: Recording for {record_seconds} seconds. ***")

            js_click(driver, control_panel_button)  # Resumes the video
            print("   - Playback resumed.")
            time.sleep(0.5)

            print("5. Starting screen recording...")
            try:
                url_slug = url.strip('/').split('/')[-1]
                if not url_slug: url_slug = f"video_{i}"
                safe_lesson_title = re.sub(r'[\\/:*?"<>|]+', '', url_slug).replace('-', '_')
                output_filename = os.path.join(DOWNLOAD_FOLDER, f"{i:02d}_{safe_lesson_title}.mp4")
            except Exception:
                output_filename = os.path.join(DOWNLOAD_FOLDER, f"lesson_{i:02d}.mp4")

            if is_docker:
                ffmpeg_command = [
                    'ffmpeg', '-f', 'x11grab', '-video_size', '1920,1080', '-framerate', '30', '-i', ':99.0',
                    '-f', 'pulse', '-i', 'default', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-preset', 'ultrafast', '-c:a', 'aac', '-b:a', '192k', '-y', output_filename
                ]
            else:  # Windows
                ffmpeg_command = [
                    'ffmpeg', '-f', 'gdigrab', '-framerate', '30', '-i', 'desktop',
                    '-f', 'dshow', '-i', f'audio={AUDIO_DEVICE_NAME}',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-y', output_filename
                ]

            recorder_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

            actual_wait_time = (record_seconds / PLAYBACK_SPEED) if not TEST_MODE else record_seconds
            print(f"6. Recording in progress... (waiting for {int(actual_wait_time)} seconds)")
            time.sleep(actual_wait_time - 6)

            print("7. Stopping recording...")
            recorder_process.communicate(b'q')
            recorder_process.wait()
            print(f"   - Video saved to: {output_filename}")

            print("8. Exiting fullscreen mode...")
            actions.send_keys(Keys.ESCAPE).perform()
            time.sleep(2)
            successful_videos.append({'url': url, 'filename': output_filename})
        except TimeoutException:
            error_message = "ERROR: A player element was not found within the 20-second timeout."
            print(error_message)
            failed_videos.append({'url': url, 'error': error_message})
            if recorder_process and recorder_process.poll() is None:
                recorder_process.terminate()
        except Exception as e:
            error_message = f"An error occurred: {type(e).__name__} - {str(e).splitlines()[0]}"
            print(error_message)
            failed_videos.append({'url': url, 'error': str(e).splitlines()[0]})
            if recorder_process and recorder_process.poll() is None:
                recorder_process.terminate()
    driver.quit()

    # Final report generation
    print("\n\n" + "=" * 60)
    print(" " * 24 + "FINAL REPORT")
    print("=" * 60)

    print(f"\n✅ SUCCESSFULLY RECORDED: {len(successful_videos)} of {len(VIDEO_URLS)}\n")
    for video in successful_videos:
        print(f"  - File: {video['filename']}")
        print(f"    URL: {video['url']}\n")

    if failed_videos:
        print(f"\n❌ FAILED TO RECORD: {len(failed_videos)} of {len(VIDEO_URLS)}\n")
        for video in failed_videos:
            print(f"  - URL: {video['url']}")
            print(f"    Error: {video['error']}\n")

    print("=" * 60)
    print("\nScript finished.")


if __name__ == "__main__":
    main()