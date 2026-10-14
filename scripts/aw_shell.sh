#!/usr/bin/env bash
# Otwiera terminal (bash) w działającym kontenerze Autoware jako użytkownik aw.
# Można otworzyć dowolnie wiele terminali.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec docker compose exec -u aw autoware bash "$@"
