#!/usr/bin/env bash
# Buduje obraz Autoware i wypycha go do GHCR (dla prowadzącego, studenci robią tylko pull).
# Jednorazowo: docker login ghcr.io -u <login GitHub>  (hasło: token z uprawnieniem write:packages)
# Użycie: ./scripts/publish_image.sh [jazzy|humble ...]   (domyślnie ROS_DISTRO z .env)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

distros=("$@")
if [ ${#distros[@]} -eq 0 ]; then
    distros=("$(sed -n 's/^ROS_DISTRO=//p' .env)")
fi

for distro in "${distros[@]}"; do
    ROS_DISTRO="$distro" docker compose build --pull autoware
    ROS_DISTRO="$distro" docker compose push autoware
done
