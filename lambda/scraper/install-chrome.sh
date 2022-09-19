#!/usr/bin/bash

# VERSIONS
# https://omahaproxy.appspot.com/
CHROMIUM_VERSION="105.0.5195.125"
CHROMIUM_BASE_POSITION="1027016"
CHROMIUM_URL="https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F$CHROMIUM_BASE_POSITION%2Fchrome-linux.zip?alt=media"

CHROME_DRIVER_VERSION="105.0.5195.52"
CHROME_DRIVER_URL="https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip"

# install chromium
mkdir -p "/opt/chromium"
curl -Lo "/opt/chromium/chrome-linux.zip" $CHROMIUM_URL
unzip -q "/opt/chromium/chrome-linux.zip" -d "/opt/chromium"
mv /opt/chromium/chrome-linux/* /opt/chromium/

# install chrome-driver
mkdir -p "/opt/chromedriver"
curl -Lo "/opt/chromedriver/chromedriver_linux64.zip" $CHROME_DRIVER_URL
unzip -q "/opt/chromedriver/chromedriver_linux64.zip" -d "/opt/chromedriver"
chmod +x "/opt/chromedriver/chromedriver"

# cleanup
rm -rf "/opt/chromium/chrome-linux" "/opt/chromium/chrome-linux.zip"
rm -rf "/opt/chromedriver/chromedriver_linux64.zip" 
