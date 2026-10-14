# Autoware (oficjalny obraz) + CARLA Python API.
# Interfejs CARLA (autoware_carla_interface) i sensor kit (carla_sensor_kit_*) są już
# częścią Autoware - brakuje tylko pakietu `carla` dla Pythona.
#
# Obraz bazowy jest przypięty po digeście: tag w GHCR można nadpisać, a digest zawsze wskazuje
# ten sam obraz. Przy zmianie AUTOWARE_VERSION zaktualizuj digesty:
#   docker buildx imagetools inspect ghcr.io/autowarefoundation/autoware:universe-cuda-jazzy-<wersja>
ARG ROS_DISTRO=jazzy
FROM ghcr.io/autowarefoundation/autoware:universe-cuda-jazzy-1.9.0@sha256:1db2988caa5dc5bae41548a8d556d0b57f55eb4dd63685426d94fd9c7a786034 AS base-jazzy
FROM ghcr.io/autowarefoundation/autoware:universe-cuda-humble-1.9.0@sha256:78d2d47128ade548c2216deee80aa998f1d97e995f910f52348bfe0d23ff1383 AS base-humble
FROM base-${ROS_DISTRO}

ARG CARLA_VERSION=0.9.16
# Łączy pakiet w GHCR z repozytorium na GitHubie.
LABEL org.opencontainers.image.source=https://github.com/PanHassan/Carla-Autoware-Bridge

# Oficjalne wheele CARLA 0.9.16 na PyPI: cp310 (humble/22.04) i cp312 (jazzy/24.04).
# PIP_BREAK_SYSTEM_PACKAGES jest wymagane na Ubuntu 24.04 (PEP 668), starszy pip je ignoruje.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --no-cache-dir "carla==${CARLA_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

COPY bashrc.sh /etc/profile.d/carla_autoware.sh
COPY aw-carla /usr/local/bin/aw-carla
RUN chmod +x /usr/local/bin/aw-carla \
    && echo "source /etc/profile.d/carla_autoware.sh" >> /home/aw/.bashrc

WORKDIR /home/aw/ws
