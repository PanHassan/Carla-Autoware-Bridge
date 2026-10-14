#!/usr/bin/env bash
# Pobiera modele ML Autoware (percepcja: CenterPoint, wykrywanie świateł itd., ~3 GB)
# do $AUTOWARE_DATA/ml_models oficjalnym playbookiem Ansible z repozytorium Autoware.
# Działa w kontenerze Autoware, więc na hoście nie trzeba instalować Ansible ani podawać sudo.
# Wymaga zbudowanego obrazu: docker compose build autoware
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose run --rm --no-deps autoware bash -c '
set -e
source /etc/profile.d/carla_autoware.sh
WORK=$(mktemp -d)
git clone --quiet --depth 1 --branch "$AUTOWARE_VERSION" \
    https://github.com/autowarefoundation/autoware.git "$WORK/autoware"
cd "$WORK/autoware"
pipx run --spec "ansible==10.*" ansible-galaxy collection install -f -r ansible-galaxy-requirements.yaml
pipx run --spec "ansible==10.*" ansible-playbook autoware.dev_env.install_dev_env \
    --tags artifacts \
    -e "data_dir=$HOME/autoware_data/ml_models" \
    -e "prompt_download_artifacts=y"
sudo chown -R aw:aw "$HOME/autoware_data/ml_models"
rm -rf "$WORK"
'
echo "Modele pobrane do ${AUTOWARE_DATA:-$HOME/autoware_data}/ml_models"
