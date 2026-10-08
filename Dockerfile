ARG TASK_IMAGE
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements.lock

FROM ${TASK_IMAGE}
USER root
ARG TASK_ID
LABEL org.opencontainers.image.source="https://github.com/akseljoonas/mimo-openenv-software"
COPY --from=runtime /usr/local /opt/arena-python
COPY server.py prepare.py /opt/arena/
COPY tasks/${TASK_ID}.json /opt/arena/instance.json
RUN chmod 700 /opt/arena \
 && useradd --uid 2000 --create-home --home-dir /home/arena-agent arena-agent \
 && chmod 755 /root \
 && /opt/arena-python/bin/python3 /opt/arena/prepare.py
ENV PYTHONUNBUFFERED=1 ENABLE_WEB_INTERFACE=false
WORKDIR /opt/arena
EXPOSE 8000
ENTRYPOINT []
CMD ["/opt/arena-python/bin/python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
