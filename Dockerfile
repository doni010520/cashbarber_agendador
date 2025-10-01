# Dockerfile for CashBarber automation
#
# This Dockerfile builds a container for the CashBarber automation project.  It
# installs Google Chrome and the matching ChromeDriver and sets up a
# Brazilian Portuguese locale and the São Paulo time zone so that date and time
# fields on CashBarber are interpreted correctly.  Python dependencies are
# installed from ``requirements.txt`` and the application is started via
# Gunicorn.

# Use Python 3.11 slim image as a lightweight base
FROM python:3.11-slim

# Use non‑interactive mode for any Debian frontends
ENV DEBIAN_FRONTEND=noninteractive
# Set timezone and locale to Brazil/São Paulo
ENV TZ=America/Sao_Paulo
ENV LANG=pt_BR.UTF-8
ENV LC_ALL=pt_BR.UTF-8

# Install required packages: locales, tzdata, and Chrome dependencies
#
#  - ``locales`` and ``tzdata`` enable us to generate the Brazilian locale
#    and configure the correct time zone.  Without these, headless Chrome
#    defaults to an English/US locale which can cause dates like ``15/10/2025``
#    to be interpreted as ``12/10/2025``.
#  - ``wget``, ``gnupg``, and ``unzip`` are used to download and verify
#    Google's Chrome packages.
#  - ``curl`` is used to discover the appropriate ChromeDriver version.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        locales \
        tzdata \
        wget \
        gnupg \
        unzip \
        curl \
    # Configure the pt_BR locale and set the time zone
    && echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    # Add Google's signing key and repository for Chrome
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    # Download and install the ChromeDriver that matches the installed Chrome
    && CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1) \
    && CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -q -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver-linux64.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver* \
    # Clean up apt caches and remove unnecessary packages to keep the image slim
    && apt-get purge -y --auto-remove curl gnupg unzip \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy dependency information and install Python dependencies separately for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code into the image
COPY schedule_cashbarber.py ./
COPY api.py ./

# Expose the port that the Flask/Gunicorn server listens on
EXPOSE 5000

# Set environment variables used by Python and Gunicorn
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Start the application with Gunicorn.  The ``timeout`` value is increased
# because the Selenium flows sometimes take longer than the default.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "api:app"]
