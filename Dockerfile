FROM python:3.9-slim

MAINTAINER Erik J. Olson <hello@erikjolson.com>

WORKDIR /usr/src/app

# Install system dependencies, including Chromium and other necessary packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libnss3 \
    libxss1 \
    libxtst6 \
    chromium \
    chromium-driver \
    libgles2-mesa-dev \
  && rm -rf /var/lib/apt/lists/*

# Set environment variables to tell Chromium to use SwiftShader
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMIUM_FLAGS="--use-gl=swiftshader --headless --no-sandbox --disable-software-rasterizer"

# Create a virtual environment
RUN python3 -m venv /env

# Set the virtual environment's binary directory to the PATH
ENV PATH="/env/bin:$PATH"

# Copy the requirements file into the container
COPY ./requirements.txt .

# Upgrade pip and install the required Python packages
RUN pip install --upgrade pip \
  && pip install -r requirements.txt

# Create output directory
RUN mkdir -p /output

# Copy the source code
COPY ./src/ .

# Set the entry point to run the webshot script
ENTRYPOINT ["./webshot.py"]
