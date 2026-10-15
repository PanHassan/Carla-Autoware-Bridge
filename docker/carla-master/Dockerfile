# carla-master: taktuje świat CARLA dla wszystkich podłączonych Autoware.
FROM python:3.12-slim

ARG CARLA_VERSION=0.9.16
LABEL org.opencontainers.image.source=https://github.com/PanHassan/Carla-Autoware-Bridge

RUN pip install --no-cache-dir --root-user-action=ignore "carla==${CARLA_VERSION}"

COPY carla_master.py /usr/local/bin/carla_master.py
CMD ["python3", "-u", "/usr/local/bin/carla_master.py"]
