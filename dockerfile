# Используем официальный образ Python

FROM python:3.11.11


# Устанавливаем рабочую директорию внутри контейнера

WORKDIR /OFD_parser_bot


# Устанавливаем необходимые системные зависимости для Chrome и Chromedriver

RUN apt-get update && apt-get install -y --no-install-recommends \

    wget \

    unzip \

    gnupg \

    fonts-liberation \

    libappindicator3-1 \

    libasound2 \

    libatk-bridge2.0-0 \

    libatk1.0-0 \

    libc6 \

    libcairo2 \

    libcups2 \

    libdbus-1-3 \

    libexpat1 \

    libfontconfig1 \

    libgbm1 \

    libgcc1 \

    libglib2.0-0 \

    libgtk-3-0 \

    libnspr4 \

    libnss3 \

    libpango-1.0-0 \

    libpangocairo-1.0-0 \

    libstdc++6 \

    libx11-6 \

    libx11-xcb1 \

    libxcb1 \

    libxcomposite1 \

    libxcursor1 \

    libxdamage1 \

    libxext6 \

    libxfixes3 \

    libxi6 \

    libxrandr2 \

    libxrender1 \

    libxss1 \

    libxtst6 \

    ca-certificates \

    lsb-release \

    xdg-utils \

    && rm -rf /var/lib/apt/lists/*


# Установка Google Chrome версии 131.0.6778.204

RUN wget https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.204/linux64/chrome-linux64.zip && \

    unzip chrome-linux64.zip -d /opt/ && \

    ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \

    rm chrome-linux64.zip


# Установка Chromedriver версии 131.0.6778.204

RUN wget https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.204/linux64/chromedriver-linux64.zip && \

    unzip -j chromedriver-linux64.zip chromedriver-linux64/chromedriver -d /usr/local/bin/ && \

    rm chromedriver-linux64.zip && \

    chmod +x /usr/local/bin/chromedriver


# Копируем файл зависимостей в рабочую директорию

COPY requirements.txt .


# Обновляем pip и устанавливаем зависимости

RUN pip install --upgrade pip setuptools && \

    pip install --no-cache-dir -r requirements.txt && \

    pip list  # Для отладки


# Копируем все остальные файлы проекта в рабочую директорию

COPY . .


# Указываем команду для запуска приложения

CMD ["python", "main.py"]

