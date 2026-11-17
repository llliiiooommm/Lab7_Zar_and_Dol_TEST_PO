FROM jenkins/jenkins:lts-jdk21

USER root

RUN apt-get update && apt-get install -y \
      qemu-system-arm \
      python3 python3-pip python3-venv \
      chromium chromium-driver xvfb curl procps \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

USER jenkins
