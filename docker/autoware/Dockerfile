# Autoware (oficjalny obraz) + CARLA Python API.
# Interfejs CARLA (autoware_carla_interface) i sensor kit (carla_sensor_kit_*) są już
# częścią Autoware - brakuje tylko pakietu `carla` dla Pythona.
ARG ROS_DISTRO=jazzy
ARG AUTOWARE_VERSION=1.9.0
FROM ghcr.io/autowarefoundation/autoware:universe-cuda-${ROS_DISTRO}-${AUTOWARE_VERSION}

ARG CARLA_VERSION=0.9.16

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
