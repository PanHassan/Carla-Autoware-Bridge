#!/usr/bin/env bash
# Uruchamia serwer CARLA (kontenery carla i carla-master) na tym komputerze.
# Użycie:
#   ./scripts/carla_server.sh            bez okna (szybciej; np. serwer bez monitora)
#   ./scripts/carla_server.sh --window   z oknem symulatora na monitorze tego komputera
#   ./scripts/carla_server.sh stop       zatrzymaj
# Działa też przez SSH: okno otwiera się na monitorze serwera (wymaga zalogowanej sesji graficznej).
# Zmiana trybu restartuje CARLA - podłączone Autoware trzeba uruchomić ponownie.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Argumenty z .env (CARLA_ARGS), bez -RenderOffScreen - tę flagę dokłada tryb bez okna.
ARGS="${CARLA_ARGS:-$(sed -n 's/^CARLA_ARGS=//p' .env | tr -d '"')}"
ARGS=$(echo " $ARGS " | sed 's/ -RenderOffScreen / /g' | xargs)

case "${1:-}" in
    stop)
        exec docker compose stop carla carla-master
        ;;
    --window)
        export DISPLAY="${DISPLAY:-:0}"
        # Przez SSH brakuje pliku autoryzacji X sesji graficznej - bierzemy go z GDM.
        if [ -z "${XAUTHORITY:-}" ] && [ -f "/run/user/$(id -u)/gdm/Xauthority" ]; then
            export XAUTHORITY="/run/user/$(id -u)/gdm/Xauthority"
        fi
        if ! xhost +local:docker >/dev/null 2>&1; then
            echo "Brak dostępu do ekranu $DISPLAY. Czy na tym komputerze jest zalogowana sesja graficzna?" >&2
            exit 1
        fi
        export CARLA_ARGS="$ARGS"
        echo "CARLA z oknem na ekranie $DISPLAY ($CARLA_ARGS)"
        ;;
    "")
        export CARLA_ARGS="-RenderOffScreen $ARGS"
        echo "CARLA bez okna ($CARLA_ARGS)"
        ;;
    *)
        sed -n '3,6p' "$0" >&2
        exit 1
        ;;
esac

docker compose up -d carla carla-master
