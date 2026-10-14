# Środowisko ROS 2 + Autoware + workspace studenta (ws/ zamontowany z repozytorium).
source "/opt/ros/${ROS_DISTRO}/setup.bash"
source /opt/autoware/setup.bash
if [ -f /home/aw/ws/install/setup.bash ]; then
    source /home/aw/ws/install/setup.bash
fi
