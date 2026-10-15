<div align="center">

# CARLA ↔ Autoware — środowisko startowe

[![Ubuntu](https://img.shields.io/badge/ubuntu-22.04%20%7C%2024.04-blue.svg)](https://ubuntu.com/download/desktop)
[![ROS 2](https://img.shields.io/badge/ros2-jazzy%20%7C%20humble-blue.svg)](https://docs.ros.org/en/jazzy/)
[![Autoware](https://img.shields.io/badge/autoware-1.9.0-orange.svg)](https://github.com/autowarefoundation/autoware/releases/tag/1.9.0)
[![CARLA](https://img.shields.io/badge/carla-0.9.16-green.svg)](https://carla.org/2025/09/16/release-0.9.16/)

</div>

Gotowe środowisko do pracy z **Autoware 1.9.0** w symulatorze **CARLA 0.9.16**. Wszystko działa
w kontenerach Docker, więc nie trzeba niczego kompilować ani łatać w Autoware.

## Jak to działa

```
┌──────────────── kontener "carla" ────────────────┐   ┌─── kontener "carla-master" ───┐
│  CARLA 0.9.16 (serwer, Unreal Engine 4)          │◀──│  mapa (CARLA_MAP), taktowanie │
└──────────────▲───────────────────────────────────┘   │  świata, czeka na klientów    │
               │ CARLA Python API (TCP 2000)           └──────────────▲────────────────┘
               │                                     "krok gotowy" (UDP 2005)
┌──────────────┴──── kontener "autoware" ──────────────────────────────┴┐
│  autoware_carla_interface  ── czujniki ──▶  Autoware 1.9.0             │
│  (spawn auta i czujników,   ◀─ sterowanie ─  (lokalizacja, percepcja,  │
│   /clock)                                     planowanie, sterowanie)  │
│                                                                        │
│  ws/  ← Twój workspace ROS 2 (zamontowany z repozytorium)              │
└────────────────────────────────────────────────────────────────────────┘
```

Świat CARLA taktuje tylko `carla-master`. Po każdym kroku czeka, aż wszystkie podłączone
Autoware przetworzą dane z czujników, więc do jednej CARLA może podłączyć się kilka Autoware
naraz, każde z własnym autem (patrz [Wspólny serwer CARLA](#wspólny-serwer-carla)).

- **[`autoware_carla_interface`](https://github.com/autowarefoundation/autoware_universe/tree/main/simulator/autoware_carla_interface)**
  to oficjalny most CARLA ↔ Autoware, utrzymywany w Autoware Universe. Łączy się z CARLA
  bezpośrednio przez Python API, więc nie potrzebuje `carla-ros-bridge`.
- Autoware uruchamia go samo po podaniu `simulator_type:=carla`. Sensor kit
  (`carla_sensor_kit`) i model pojazdu (`sample_vehicle`, w CARLA: Toyota Prius) są już
  w oficjalnym obrazie Autoware.
- Repozytorium dodaje do obrazu Autoware tylko pakiet `carla==0.9.16` dla Pythona
  ([`docker/autoware/Dockerfile`](docker/autoware/Dockerfile)), skrypty i przykłady.
  Gotowy obraz leży w GHCR (`ghcr.io/panhassan/carla-autoware`), więc nie zależy od tego,
  czy oficjalny obraz Autoware w tej wersji nadal istnieje.
- Most jest w obrazie lekko zmieniony ([`docker/autoware/external_tick.py`](docker/autoware/external_tick.py)):
  zamiast sam taktować świat, zgłasza gotowość do `carla-master`. Nie może też zmienić mapy
  ani ustawień świata, bo to zepsułoby symulację pozostałym klientom.

> **Skąd zmiana?** Poprzednia wersja tego repo używała mostu TUM (`carla-ros-bridge` +
> `autoware_auto_msgs`), który działał tylko z Autoware 2024.01 i wymagał ręcznych zmian
> w `autoware_launch`. Autoware od tamtej pory przeszło na `autoware_msgs`, a most TUM nie jest
> rozwijany. Stara wersja jest dostępna w historii git (gałąź `main` sprzed zmiany).

## Wymagania

| | Minimum | Zalecane |
|---|---|---|
| System | Ubuntu 22.04 / 24.04 | Ubuntu 24.04 |
| GPU | NVIDIA, 6 GB VRAM (lekka konfiguracja czujników) | NVIDIA ≥ 8 GB VRAM |
| RAM | 16 GB | 32 GB |
| Dysk | ~45 GB (obrazy ~30 GB, modele ML, mapy) | |

### 1. Sterownik NVIDIA

*Oprogramowanie i aktualizacje → Dodatkowe sterowniki* → wybierz sterownik NVIDIA
„proprietary, tested”. Sprawdź: `nvidia-smi`.

### 2. Docker

Według [oficjalnej instrukcji](https://docs.docker.com/engine/install/ubuntu/):

```bash
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker bez sudo (potem wyloguj się i zaloguj ponownie)
sudo usermod -aG docker $USER
```

### 3. NVIDIA Container Toolkit

Według [instrukcji NVIDII](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html):

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Kontenery dostają GPU przez CDI (montuje też sterownik Vulkan, którego CARLA potrzebuje).
Sprawdź, czy spec CDI istnieje:

```bash
nvidia-ctk cdi list            # musi pokazać nvidia.com/gpu=all
# jeśli pusto:
sudo nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml
docker run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
```

## Instalacja (jednorazowo)

```bash
git clone https://github.com/PanHassan/Carla-Autoware-Bridge.git
cd Carla-Autoware-Bridge

# Mapa (lanelet2 + chmura punktów) -> ~/autoware_data/maps/Town01
./scripts/download_map.sh Town01          # dostępne: Town01-07, Town10HD

# Pobranie obrazów CARLA i Autoware (długo, ~30 GB)
docker compose pull

# Modele sieci neuronowych dla percepcji -> ~/autoware_data/ml_models (~3 GB)
# Działa w kontenerze Autoware, więc wymaga pobranego obrazu (krok wyżej).
./scripts/download_artifacts.sh
```

## Uruchomienie

```bash
xhost +local:docker            # zezwól kontenerom na otwieranie okien (po każdym logowaniu)
docker compose up -d           # start CARLA, carla-master i kontenera Autoware w tle
./scripts/aw_shell.sh          # terminal w kontenerze Autoware
```

W terminalu kontenera:

```bash
aw-carla
```

`aw-carla` używa mapy załadowanej w CARLA (`CARLA_MAP` w `.env`, domyślnie Town01).
Mapa musi być pobrana (`./scripts/download_map.sh`). Po ok. minucie otworzy się RViz. Dalej:

1. **Lokalizacja**: w panelu stanu Autoware (po lewej) kliknij **Initialize with GNSS**
   (albo ustaw pozycję narzędziem *2D Pose Estimate*).
2. **Cel**: narzędziem **2D Goal Pose** kliknij i przeciągnij na pasie ruchu.
3. **Jazda**: po wyznaczeniu trasy kliknij **Auto** w sekcji trybu pracy.

To samo bez klikania, z drugiego terminala (`./scripts/aw_shell.sh`):

```bash
ros2 run carla_autoware_examples drive_to_goal --ros-args -p goal_x:=<x> -p goal_y:=<y> -p goal_yaw_deg:=<yaw>
```

Zatrzymanie: `Ctrl+C` w terminalu z `aw-carla`, a na koniec `docker compose down`.
Przed ponownym `aw-carla` upewnij się, że poprzednie uruchomienie się zakończyło. Dwa
Autoware na jednym komputerze widzą nawzajem swoje tematy ROS i się mieszają. W razie
wątpliwości: `docker compose restart autoware`.

Pierwsze uruchomienie z percepcją trwa kilka minut dłużej, bo TensorRT kompiluje modele
(`Applying optimizations and building TensorRT CUDA engine`). Kolejne starty są szybkie.

### Przydatne argumenty `aw-carla`

Argumenty są przekazywane do `ros2 launch`, np. `aw-carla perception:=false`:

| Argument | Działanie |
|---|---|
| `use_light_weight_sensor_mapping:=False` | 6 kamer 1600×900 zamiast jednej przedniej (domyślnej). Tylko z CARLA na tym samym komputerze: przez sieć to ~350 MB/s |
| `perception:=false` | bez percepcji. Uwaga: wtedy planowanie nie wyznacza trajektorii i auto nie pojedzie |
| `spawn_point:="x,y,z,roll,pitch,yaw"` | pozycja startowa auta (domyślnie losowa) |
| `vehicle_type:=...` | inny pojazd CARLA. Sterowanie jest skalibrowane dla `vehicle.toyota.prius` |
| `rviz:=false` | bez RViz |

### Ruch uliczny

W kontenerze Autoware (ruch jest wspólny dla wszystkich aut na serwerze):

```bash
python3 ~/utils/generate_traffic.py --host $CARLA_HOST -n 30 -w 10    # 30 aut, 10 pieszych
```

## Praca własna: workspace `ws/`

Katalog [`ws/`](ws/) jest zamontowany w kontenerze jako `~/ws`. Pakiety ROS 2 trzymaj
w `ws/src/`; edytujesz je na hoście (np. VS Code), budujesz w kontenerze:

```bash
cd ~/ws
colcon build --symlink-install
source install/setup.bash      # nowe terminale robią to automatycznie
```

Przykładowy pakiet [`carla_autoware_examples`](ws/src/carla_autoware_examples):

- `speed_monitor`: subskrybuje prędkość i pozycję auta z Autoware, publikuje prędkość w km/h
  i ostrzega po przekroczeniu limitu (`ros2 launch carla_autoware_examples speed_monitor.launch.xml`).
- `drive_to_goal`: pełny scenariusz przez
  [Autoware AD API](https://autowarefoundation.github.io/autoware-documentation/main/design/autoware-interfaces/ad-api/):
  inicjalizacja lokalizacji → trasa → tryb autonomiczny → dojazd.

Najważniejsze tematy:

| Temat | Co to |
|---|---|
| `/sensing/lidar/top/pointcloud_before_sync` | lidar z CARLA |
| `/sensing/camera/CAM_FRONT/image_raw` | przednia kamera |
| `/sensing/gnss/pose_with_covariance`, `/sensing/imu/tamagawa/imu_raw` | GNSS, IMU |
| `/localization/kinematic_state` | pozycja i prędkość z lokalizacji Autoware |
| `/perception/object_recognition/objects` | wykryte obiekty |
| `/planning/trajectory` | zaplanowana trajektoria |
| `/control/command/control_cmd` | polecenia sterowania z Autoware |
| `/vehicle/status/velocity_status`, `/vehicle/status/steering_status` | stan pojazdu z CARLA |

## Konfiguracja

Wersje i opcje są w pliku [`.env`](.env):

- `ROS_DISTRO=jazzy` (domyślnie) albo `humble`. Humble kończy wsparcie w maju 2027.
  Po zmianie: `docker compose pull autoware`.
- `CARLA_ARGS`: argumenty serwera CARLA. Domyślnie `-RenderOffScreen` (bez okna symulatora,
  dużo szybciej). Usuń tę flagę, jeśli chcesz okno CARLA, albo zmień jakość
  (`-quality-level=Epic`).
- `AUTOWARE_DATA`: gdzie na hoście leżą mapy i modele.
- `CARLA_MAP`: mapa ładowana przez `carla-master`. Po zmianie: `docker compose up -d`.
- `CARLA_HOST`, `CARLA_PORT`: adres serwera CARLA, z którym łączy się Autoware.
  `localhost` = CARLA na tym samym komputerze.

### Wspólny serwer CARLA

Jedna CARLA może obsłużyć kilka Autoware naraz, każde na innym komputerze i z własnym
autem w tym samym świecie. Wszyscy jeżdżą na tej samej mapie.

**Serwer** (komputer z mocnym GPU, instalacja jak wyżej, bez modeli ML):

```bash
docker compose pull carla carla-master
docker compose up -d carla carla-master
docker compose logs -f carla-master        # kto jest podłączony
```

Firewall serwera musi przepuszczać TCP 2000–2002 (CARLA) i UDP 2005 (`carla-master`).

**Komputer studenta**: w `.env` ustaw `CARLA_HOST=<adres IP serwera>`, a potem:

```bash
docker compose up -d autoware
./scripts/aw_shell.sh
aw-carla
```

Jak to działa i na co uważać:

- `carla-master` po każdym kroku czeka na wszystkich klientów, ale najwyżej
  `CARLA_STEP_TIMEOUT` (domyślnie 0,25 s). Wolniejszy komputer spowalnia więc symulację
  wszystkim, ale zawieszony klient jej nie zatrzyma: po 3 s bez odpowiedzi jest odłączany,
  a jego auto usuwane.
- Serwer liczy czujniki wszystkich aut (domyślnie 1 kamera + lidar na auto), więc każde
  kolejne auto zwalnia symulację. Najwięcej kosztuje lidar, liczony na procesorze serwera.
- Dane z czujników jednego auta to ~20–40 MB/s. Wi-Fi wystarcza dla jednej osoby,
  przy kilku lepiej kabel 1 Gbit/s.
- Auta mają nazwy `ego_<nazwa komputera>`, więc na jednym komputerze uruchamiaj jedno Autoware.

### CARLA bez ekranu (np. serwer w laboratorium)

| `CARLA_ARGS` | Okno | Kamery | Lidar / GNSS / IMU | Uwagi |
|---|---|---|---|---|
| `-RenderOffScreen -quality-level=Low -nosound` (domyślnie) | nie | tak | tak | renderuje na GPU bez okna |
| `-quality-level=Low -nosound` | tak | tak | tak | okno symulatora, wolniej |
| `-nullrhi -nosound` | nie | **nie** | tak | bez renderowania, najlżejsze. Tylko z `perception:=false` lub percepcją z samego lidaru |

RViz z kontenera Autoware nadal potrzebuje ekranu. Bez ekranu dodaj `rviz:=false`
i steruj przez `drive_to_goal`.

Lokalne zmiany w `compose.yaml` (inny obraz CARLA, dodatkowe wolumeny) wpisuj do
`compose.override.yaml`. Wzór jest w [`compose.override.example.yaml`](compose.override.example.yaml).

### Własny obraz Autoware (prowadzący)

Po zmianie [`docker/autoware/Dockerfile`](docker/autoware/Dockerfile) zbuduj obraz lokalnie
(`docker compose build autoware`). Studenci dostaną go przez `docker compose pull` dopiero
po wypchnięciu do GHCR:

```bash
# jednorazowo; hasło = token GitHub (classic) z uprawnieniem write:packages
docker login ghcr.io -u PanHassan
./scripts/publish_image.sh               # ROS_DISTRO z .env
./scripts/publish_image.sh jazzy humble  # oba warianty
```

Nowy pakiet w GHCR jest prywatny. Raz ustaw go jako publiczny: GitHub → Packages →
`carla-autoware` → Package settings → Change visibility → Public.

Obraz bazowy Autoware jest przypięty po digeście w Dockerfile, więc przebudowa daje to samo
środowisko, nawet jeśli tag w `ghcr.io/autowarefoundation` zostanie nadpisany. Przy przejściu
na nową wersję Autoware zaktualizuj digesty (polecenie jest w komentarzu w Dockerfile)
i `AUTOWARE_VERSION` w `.env`.

## Rozwiązywanie problemów

| Objaw | Rozwiązanie |
|---|---|
| w logu CARLA `lavapipe is not a conformant vulkan implementation`, symulacja bardzo wolna | CARLA renderuje na CPU, bo w kontenerze brakuje sterownika Vulkan NVIDII. Sprawdź `nvidia-ctk cdi list` (musi pokazać `nvidia.com/gpu=all`), w razie potrzeby `sudo nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml` |
| CARLA kończy się zaraz po `Disabling core dumps.` | j.w. albo brak dostępu do X: `xhost +local:docker` |
| `time-out ... waiting for the simulator` | CARLA jeszcze się ładuje albo padła: `docker compose logs carla` |
| `aw-carla` czeka na serwer CARLA w nieskończoność | nie działa `carla-master` albo ma inną mapę: `docker compose logs carla-master`. Przy osobnym serwerze sprawdź `CARLA_HOST` i firewall |
| `Brak kolejnej klatki CARLA` | `carla-master` się zatrzymał: `docker compose up -d carla-master` |
| symulacja wolniejsza niż czas rzeczywisty (`ros2 topic hz /clock` < 20 Hz) | GPU nie nadąża: `-RenderOffScreen`, `use_light_weight_sensor_mapping:=True`, zamknij inne programy używające GPU |
| RViz się nie otwiera | `xhost +local:docker`, sprawdź `echo $DISPLAY` przed `docker compose up` |
| tematy ROS niewidoczne z hosta | kontener używa CycloneDDS tylko na `lo`. Na hoście ustaw `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` i ten sam `CYCLONEDDS_URI` (`docker compose exec autoware cat /home/aw/cyclonedds.xml`) |
| sieć uczelniana blokuje pobieranie | użyj innej sieci do `docker compose pull` i skryptów `download_*` |

## Ograniczenia

- Mapy lanelet2 z [CARLA autoware-contents](https://bitbucket.org/carla-simulator/autoware-contents/src/master/maps/)
  nie mają sygnalizacji świetlnej jako elementów regulacyjnych, więc Autoware nie reaguje na
  światła. Jak dodać je do mapy: [README `autoware_carla_interface`](https://github.com/autowarefoundation/autoware_universe/tree/main/simulator/autoware_carla_interface#traffic-light-recognition).
- Kalibracja sterowania (`accel/brake/steer_map.csv`) dotyczy Toyoty Prius. Inny pojazd
  wymaga ponownej kalibracji.

## Podziękowania

- [`autoware_carla_interface`](https://github.com/autowarefoundation/autoware_universe/tree/main/simulator/autoware_carla_interface): TIER IV / Autoware Foundation.
- Poprzednia wersja tego repozytorium była oparta na
  [CARLA-Autoware-Bridge (TUM)](https://github.com/TUMFTM/Carla-Autoware-Bridge):

```bibtex
@inproceedings{carla_aw_bridge24,
  title  = {CARLA-Autoware-Bridge: Facilitating Autonomous Driving Research with a Unified Framework for Simulation and Module Development},
  author = {Kaljavesi, Gemb and Kerbl, Tobias and Betz, Tobias and Mitkovskii, Kirill and Diermeyer, Frank},
  year   = {2024}
}
```
