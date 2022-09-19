FROM public.ecr.aws/lambda/python:3.8

COPY requirements.txt /tmp/
COPY install-chrome.sh /tmp/

# install chrome dependecies
RUN yum install unzip atk at-spi2-atk gtk3 cups-libs pango libdrm \ 
    libXcomposite libXcursor libXdamage libXext libXtst libXt \
    libXrandr libXScrnSaver alsa-lib -y

# Install chromium, chrome-driver
RUN /usr/bin/bash /tmp/install-chrome.sh

# Install Python dependencies for function
RUN pip install --upgrade pip -q
RUN pip install -r /tmp/requirements.txt -q

# Remove unused packages
RUN yum remove unzip -y

COPY app.py /var/task/
CMD [ "app.lambda_handler" ] 