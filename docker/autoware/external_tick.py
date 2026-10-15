"""Tryb wielu klientów dla autoware_carla_interface.

Świat CARLA taktuje carla-master (docker/carla-master), więc most nie może:
- wywoływać world.tick() - zamiast tego zgłasza masterowi gotowość (UDP) i czeka na kolejną
  klatkę; master robi krok, gdy wszyscy podłączeni klienci są gotowi,
- zmieniać ustawień świata (tryb synchroniczny, krok czasu),
- przeładowywać mapy - to wyrzuciłoby z symulacji wszystkich pozostałych.

Dodatkowo (wydajność przy zdalnym serwerze) stan świateł auta jest zapamiętywany lokalnie,
a kamery dostają sensor_tick (CARLA_CAMERA_HZ, domyślnie 10 Hz). Bez tego CARLA renderuje
i wysyła obraz z każdej kamery w każdym kroku, choć most publikuje go w ROS najwyżej ~10 Hz -
przy zdalnym serwerze to kilkaset MB/s przez sieć.

Importowany na początku carla_autoware.py (patrz Dockerfile).
"""

import os
import socket
import time

import carla

from .modules import carla_wrapper

_MASTER = (os.environ.get("CARLA_HOST", "localhost"), int(os.environ.get("CARLA_MASTER_PORT", "2005")))
_CLIENT_ID = f"{socket.gethostname()}-{os.getpid()}"
# Nazwa auta tego klienta (ustawia aw-carla). Master usuwa je, gdy klient zniknie bez sprzątania.
_EGO_ROLE = os.environ.get("CARLA_EGO_ROLE", "-")
_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_CAMERA_HZ = float(os.environ.get("CARLA_CAMERA_HZ", "10"))


def _tick(self, seconds=10.0):
    frame = self.get_snapshot().frame
    _sock.sendto(f"{_CLIENT_ID} {frame} {_EGO_ROLE}".encode(), _MASTER)
    # get_snapshot() czyta stan odebrany lokalnie (bez zapytania do serwera). wait_for_tick()
    # mogłoby przegapić klatkę, którą master zrobi zaraz po naszym zgłoszeniu.
    deadline = time.monotonic() + seconds
    while True:
        snapshot = self.get_snapshot()
        if snapshot.frame > frame:
            return snapshot.frame
        if time.monotonic() > deadline:
            raise RuntimeError("Brak kolejnej klatki CARLA - czy działa carla-master?")
        time.sleep(0.001)


def _apply_settings(self, settings):
    return self.get_snapshot().frame


def _load_world_if_different(self, map_name, *args, **kwargs):
    world = self.get_world()
    current = world.get_map().name.split("/")[-1]
    if current not in (map_name, f"{map_name}_Opt"):
        raise RuntimeError(
            f"Serwer CARLA ma załadowaną mapę {current}, a Autoware chce {map_name}. "
            "Mapę zmienia się na serwerze (CARLA_MAP w .env)."
        )
    return world


_configure_camera_attributes = carla_wrapper.SensorWrapper._configure_camera_attributes


def _configure_camera_with_tick(self, bp, spec):
    _configure_camera_attributes(self, bp, spec)
    bp.set_attribute("sensor_tick", str(1.0 / _CAMERA_HZ))


carla_wrapper.SensorWrapper._configure_camera_attributes = _configure_camera_with_tick


# Most w każdym kroku dwa razy pyta serwer o stan świateł auta (kierunkowskazy), a każde zapytanie
# to przejście przez sieć - przez Wi-Fi ~10 ms. Światła ego zmienia tylko sam most, więc wystarczy
# zapamiętać stan po każdym set_light_state.
_light_state = {}
_get_light_state = carla.Vehicle.get_light_state
_set_light_state = carla.Vehicle.set_light_state


def _cached_get_light_state(self):
    if self.id not in _light_state:
        _light_state[self.id] = _get_light_state(self)
    return _light_state[self.id]


def _cached_set_light_state(self, state):
    _light_state[self.id] = state
    return _set_light_state(self, state)


carla.Vehicle.get_light_state = _cached_get_light_state
carla.Vehicle.set_light_state = _cached_set_light_state
carla.World.tick = _tick
carla.World.apply_settings = _apply_settings
carla.Client.load_world_if_different = _load_world_if_different
