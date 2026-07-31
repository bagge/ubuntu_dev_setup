ARG UBUNTU_VERSION=26.04
FROM ubuntu:${UBUNTU_VERSION}

ARG UBUNTU_VERSION
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
        python3-pip \
    && if [ "${UBUNTU_VERSION}" = "26.04" ]; then \
        apt-get install -y --no-install-recommends sudo-rs; \
    else apt-get install -y --no-install-recommends sudo; fi \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash devtester \
    && printf 'devtester ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/devtester \
    && chmod 0440 /etc/sudoers.d/devtester

COPY tests/container/run-in-container.sh /usr/local/bin/run-in-container
RUN chmod 0755 /usr/local/bin/run-in-container

ENTRYPOINT ["/usr/local/bin/run-in-container"]
