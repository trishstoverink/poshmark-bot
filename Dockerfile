FROM python:3.11-slim

# Install dependencies for Chrome
RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg2 jq \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 fonts-liberation \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing + matching ChromeDriver
RUN CHROME_JSON=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json) \
    && CHROME_URL=$(echo "$CHROME_JSON" | jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64") | .url') \
    && DRIVER_URL=$(echo "$CHROME_JSON" | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && wget -q "$CHROME_URL" -O /tmp/chrome.zip \
    && wget -q "$DRIVER_URL" -O /tmp/chromedriver.zip \
    && unzip -q /tmp/chrome.zip -d /opt/ \
    && unzip -q /tmp/chromedriver.zip -d /opt/ \
    && chmod +x /opt/chrome-linux64/chrome \
    && chmod +x /opt/chromedriver-linux64/chromedriver \
    && rm /tmp/chrome.zip /tmp/chromedriver.zip

# Set paths so Selenium can find them
ENV CHROME_BIN=/opt/chrome-linux64/chrome
ENV CHROMEDRIVER_PATH=/opt/chromedriver-linux64/chromedriver
ENV PATH="/opt/chrome-linux64:/opt/chromedriver-linux64:${PATH}"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
