<div align="center">

# CARLA-Autoware-Bridge - Enables the use of CARLA for Testing and Development of Autoware Core/Universe
[![Linux](https://img.shields.io/badge/os-ubuntu22.04-blue.svg)](https://www.linux.org/)
[![Docker](https://badgen.net/badge/icon/docker?icon=docker&label)](https://www.docker.com/)
[![ROS2humble](https://img.shields.io/badge/ros2-humble-blue.svg)](https://docs.ros.org/en/humble/index.html)

</div>

## Overview
The simulation framework around the CARLA-Autoware-Bridge consists of the components:
- carla-autoware-bridge: This repository holding the CARLA-Autoware-Bridge.
- ros-bridge: Fork of the ros-bridge with our changes needed for the CARLA-Autoware-Bridge.
- carla-t2: Vehicle model and sensor kit packages of the CARLA T2 2021 Vehicle for Autoware.
- carla-ros-msgs:  Fork of the carla-ros-msg with our changes needed for the CARLA-Autoware-Bridge.

## Prerequisites
Install ubuntu 24.04
 
https://ubuntu.com/download/desktop

Install Terminator 
```
sudo apt update
sudo apt install terminator
```

Install docker
https://docs.docker.com/engine/install/ubuntu/
```
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

 sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

```

Fixing sudo's problem
```
sudo groupadd -f docker
sudo usermod -a docker $USER

logout from system and log in

```



Dockers handling
```
# Download an image from a registry
docker pull [OPTIONS] NAME[:TAG|@DIGEST]
# Example 
docker pull debian

# Create and run a new container from an image
docker run
# Example
docker run --name test -d nginx:alpine

# Execute a command in a running container
docker exec
# Example
docker exec -it container-name /bin/bash

# Load an image from a tar archive or STDIN
docker load [OPTIONS]
# Example
docker load --input fedora.tar

# Save one or more images to a tar archive (streamed to STDOUT by default)
docker save [OPTIONS] IMAGE [IMAGE...]
# Example
docker save --output busybox.tar busybox

# List images
docker images

# List containers
docker ps
```


Install Nvidia docker toolkit

[Nvidia docker toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
```
Configure the production repository:

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

Update the packages list from the repository:

sudo apt-get update

Install the NVIDIA Container Toolkit packages:

sudo apt-get install -y nvidia-container-toolkit

Configure the container runtime by using the nvidia-ctk command:

sudo nvidia-ctk runtime configure --runtime=docker

Restart the Docker daemon:

sudo systemctl restart docker
```

## Introduction
The CARLA-Autoware-Bridge is a package to connect the CARLA simulator to Autoware Core/Universe with the help of the CARLA-ROS-Bridge. Currently the **latest Autoware Core/Universe** and **CARLA 0.9.15** is supported.
### Youtube Demo Video + Quickstart
| Demo                                            | Quickstart                                         |
| ----------------------------------------------------- | ---------------------------------------------- |
| [![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/aEx8yBY06Jw/0.jpg)](https://youtu.be/aEx8yBY06Jw)                                       | [![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/OmnMnvz949Y/0.jpg)](https://youtu.be/OmnMnvz949Y)                             |


## Paper
If you use this or the other associated repos, please cite our Paper:

**CARLA-Autoware-Bridge: Facilitating Autonomous Driving Research
with a Unified Framework for Simulation and Module Development**<br>Gemb Kaljavesi, Tobias Kerbl, Tobias Betz, Kirill Mitkovskii, Frank Diermeyer [[PDF](https://arxiv.org/abs/2402.11239)]

```
@inproceedings{carla_aw_bridge24,
  title = {CARLA-Autoware-Bridge: Facilitating Autonomous Driving Research
with a Unified Framework for Simulation and Module Development,
  author = {Kaljavesi, Gemb and Kerbl, Tobias and Betz, Tobias and Mitkovskii, Kirill and Diermeyer, Frank},
  year = {2024}
}
```

The Paper is currently under review and only published as preprint.



## How to Build and Install the Bridge
The easiest way to use the CARLA-Autoware-Bridge is to use our prebuilt docker image or to build the docker image by yourself. Bu we also provide a tutorial for local usage.

#### Docker Workflow(Recommended)
You can build the docker image by yourself or use the image from our github registry.
```
# Pull our latest docker image
docker pull tumgeka/carla-autoware-bridge:latest

# Alternatively build it yourself by running our build_docker.sh
./docker/build_docker.sh
```

#### Local Workflow
Comming Soon. Until then, take a look at our Dockerfile.

#### Maps
Autoware needs the maps in a special lanelet2 format, we will upload all converted maps in the future under the following link: [carla-autoware-bridge/maps](https://syncandshare.lrz.de/getlink/fiBgYSNkmsmRB28meoX3gZ/)

## General Installation and Usage
The installation and usage of the CARLA-Autoware-Bridge is described in the following tutourial. In order to function properly the packages should be started in the order CARLA --> CARLA-Autoware-Bridge --> Autoware. 

### 1) CARLA
We recommended to use the dockerized version of CARLA 0.9.15. To pull and start CARLA for usage with the CARLA-Autoware-Bridge follow the steps below.
```bash
# Pull CARLA 0.9.15
docker pull carlasim/carla:0.9.15
```
```bash
# Start CARLA
docker run --privileged --gpus all --net=host -e DISPLAY=$DISPLAY carlasim/carla:0.9.15 /bin/bash ./CarlaUE4.sh -carla-rpc-port=1403 
```
Additional information:
- `-prefernvidia` - use NVIDIA GPU for hardware acceleration
- `-carla-rpc-port=3000` - use other than default port (2000) for RPC service's port
- `-quality-level=Low` - use low quality level mode for a minimal video memory consumption

### 2) CARLA-Autoware-Bridge
Run the carla-autoware-bridge
```bash
# If you are using a docker start the docker first
docker run -it -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp --network host tumgeka/carla-autoware-bridge:latest

# Launch the bridge
ros2 launch carla_autoware_bridge carla_aw_bridge.launch.py port:=1403 town:=Town10HD
```

Additional information:
- `-port:=3000` to switch to a different CARLA port for it's RPC port
- `-timeout:=10` to increase waiting time of loading a CARLA town before raising error
- `-view:=true` to show third-person-view window
- `-town:=Town10HD` to set the town
- `-traffic_manager=False` to turn off traffic manager server (True by default)
- `-tm_port=8000` to switch the traffic manager server port to a different one (8000 by default)

If you want to spawn traffic run the following script inside the docker:
```
python3 src/carla_autoware_bridge/utils/generate_traffic.py -p 1403
```

### 3) Autoware
To use Autoware some minor [adjustments](/doc/autoware-changes.md) are required. Additionally you will need our sensorkit and vehicle model.
```
git clone https://github.com/TUMFTM/Carla_t2.git
```

Launch autoware
```bash
ros2 launch autoware_launch e2e_simulator.launch.xml vehicle_model:=carla_t2_vehicle sensor_model:=carla_t2_sensor_kit map_path:=<path to /wsp/map>
```

Autoware changes often, for a reproducible behaviour we recommend you to use a tagged autoware version:
https://github.com/autowarefoundation/autoware/tree/2024.01

```bash
docker pull ghcr.io/autowarefoundation/autoware:humble-2024.01-cuda-amd64

rocker --network=host -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e LIBGL_ALWAYS_SOFTWARE=1 --x11 --nvidia --volume /path/to/code -- ghcr.io/autowarefoundation/autoware-universe:humble-2024.01-cuda-amd64
```

## Limitations and Future Work
- We are currently working on making traffic light detection possible, at least for Town10HD
- Autoware is a map-based approach and some maps may not allow some positions to be reached or some lane changes may not be possible. We are continuously trying to improve our map conversion
- We aim to enhance future efficiency by ensuring that the bridge is Python-free, utilizing native DDS connection with the CARLA simulator

## Known issues
- University network could block some network traffic so you should be able to manage it using alternative one.
