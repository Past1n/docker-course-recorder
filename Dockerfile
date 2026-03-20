# Указываем архитектуру для надежности
 FROM --platform=linux/amd64 python:3.10-slim

 ENV DEBIAN_FRONTEND=noninteractive

# Установка системных зависимостей, включая VNC-сервер и unclutter
RUN apt-get update && apt-get install -y \
    gnupg \
    wget \
    xvfb \
    pulseaudio \
    ffmpeg \
    curl \
    unzip \
    jq \
    x11vnc \
    unclutter \
    --no-install-recommends
# ... (остальной код) ...

 # Установка Google Chrome
 RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-archive-keyring.gpg \
     && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
     && apt-get update \
     && apt-get install -y google-chrome-stable --no-install-recommends

 # Установка ChromeDriver
 RUN CHROME_VERSION=$(google-chrome --version | cut -f 3 -d ' ' | cut -d '.' -f 1-3) \
     && DRIVER_URL=$(curl -sS "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | jq -r ".versions[] | select(.version | startswith(\"$CHROME_VERSION\")) | .downloads.chromedriver[] | select(.platform==\"linux64\") | .url" | tail -n 1) \
     && if [ -z "$DRIVER_URL" ]; then echo "Failed to find ChromeDriver for Chrome $CHROME_VERSION"; exit 1; fi \
     && wget -q -O /tmp/chromedriver.zip "$DRIVER_URL" \
     && unzip -o /tmp/chromedriver.zip -d /usr/local/bin/ \
     && rm /tmp/chromedriver.zip \
     && chmod +x /usr/local/bin/chromedriver-linux64/chromedriver \
     && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

 # Очистка
 RUN apt-get clean && rm -rf /var/lib/apt/lists/*

 # Настройка рабочей директории и копирование кода
 WORKDIR /app
 COPY . .

 # Установка Python-библиотек
 RUN python -m pip install --no-cache-dir -r requirements.txt

# Обновленная команда запуска со стартом VNC и unclutter
CMD ["/bin/bash", "-c", " \
    Xvfb :99 -screen 0 1920x1080x24 & \
    x11vnc -display :99 -nopw -forever & \
    unclutter -idle 1 -root & \
    export DISPLAY=:99 && \
    pulseaudio -D --exit-idle-time=-1 && \
    pactl load-module module-null-sink sink_name=MySink && \
    pactl set-default-source MySink.monitor && \
    echo '--- Starting Python script ---' && \
    python main_recorder.py \
"]