#!/usr/bin/env bash
# Pobiera mapę CARLA w formacie Autoware (lanelet2 + pointcloud) i układa ją
# w strukturze oczekiwanej przez autoware_launch:
#   $AUTOWARE_DATA/maps/<Town>/{lanelet2_map.osm,pointcloud_map.pcd,map_projector_info.yaml}
#
# Użycie: ./scripts/download_map.sh [Town01|Town02|Town03|Town04|Town05|Town06|Town07|Town10HD]
set -euo pipefail

TOWN="${1:-Town01}"
AUTOWARE_DATA="${AUTOWARE_DATA:-$HOME/autoware_data}"
BASE_URL="https://bitbucket.org/carla-simulator/autoware-contents/raw/master/maps"

case "$TOWN" in
  Town01|Town02|Town03|Town04|Town05|Town06|Town07|Town10HD) ;;
  *) echo "Nieznana mapa: $TOWN" >&2; exit 1 ;;
esac

MAP_DIR="$AUTOWARE_DATA/maps/$TOWN"
mkdir -p "$MAP_DIR"

download() {
  local url="$1" dest="$2"
  if [[ -s "$dest" ]]; then
    echo "Pomijam (już istnieje): $dest"
    return
  fi
  echo "Pobieram $url"
  curl -fL --retry 3 --progress-bar -o "$dest.part" "$url"
  mv "$dest.part" "$dest"
}

download "$BASE_URL/vector_maps/lanelet2/$TOWN.osm" "$MAP_DIR/lanelet2_map.osm"
download "$BASE_URL/point_cloud_maps/$TOWN.pcd" "$MAP_DIR/pointcloud_map.pcd"

# Mapy CARLA są w lokalnym układzie współrzędnych (bez georeferencji).
echo "projector_type: Local" > "$MAP_DIR/map_projector_info.yaml"

echo "Mapa gotowa: $MAP_DIR"
