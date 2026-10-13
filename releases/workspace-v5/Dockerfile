FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
COPY requirements.txt /tmp/artifact-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends git sqlite3 ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r /tmp/artifact-requirements.txt \
    && pip check \
    && useradd --uid 2000 --create-home --home-dir /home/user arena-agent \
    && useradd --uid 2001 --no-create-home arena-grader
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/akseljoonas/mimo-openenv-software" \
      org.opencontainers.image.revision=$SOURCE_REVISION
WORKDIR /opt/arena
COPY runtime_server.py bundles.json LICENSE ./
RUN touch container.marker && chmod 700 /opt/arena
ENV PYTHONUNBUFFERED=1 ENABLE_WEB_INTERFACE=false
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "runtime_server:app", "--host", "0.0.0.0", "--port", "8000"]
