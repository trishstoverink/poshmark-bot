FROM python:3.11-slim

# Install Chrome + matching ChromeDriver via Chrome for Testing
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing (bundled with matching chromedriver)
RUN CHROME_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
    | jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64") | .url') \
    && DRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
    | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && wget -q "$CHROME_URL" -O /tmp/chrome.zip \
    && wget -q "$DRIVER_URL" -O /tmp/chromedriver.zip \
    && unzip -q /tmp/chrome.zip -d /opt/ \
    && unzip -q /tmp/chromedriver.zip -d /opt/ \
    && ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome \
    && ln -s /opt/chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && rm /tmp/chrome.zip /tmp/chromedriver.zip

# Install Chrome's runtime dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
