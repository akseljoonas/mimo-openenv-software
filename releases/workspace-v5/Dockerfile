FROM ghcr.io/akseljoonas/mimo-openenv-software@sha256:2031f3313b3a94474fcb8f9d0b2d416eb0bb86346dd32d8dbf177384c7a681c9
USER root
ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://github.com/akseljoonas/mimo-openenv-software" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.description="Fixed public data workflows with shell artifact grading"
COPY workflow_server.py cases.json /opt/arena/
COPY vendor /opt/arena/vendor
RUN chmod 700 /opt/arena && chmod 755 /workspace
WORKDIR /opt/arena
EXPOSE 8000
ENTRYPOINT []
CMD ["/opt/arena-python/bin/python3", "-m", "uvicorn", "workflow_server:app", "--host", "0.0.0.0", "--port", "8000"]
