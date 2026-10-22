#!/usr/bin/env python3
"""Ręczna jazda (manual_control.py z CARLA 0.9.16) we wspólnym świecie z carla-master.

manual_control.py jest bez zmian. Tu tylko blokujemy to, co zmieniłoby świat wszystkim
podłączonym: pogodę (C), warstwy mapy (V/B) oraz nagrywanie i odtwarzanie symulacji
(CTRL+R/CTRL+P - odtwarzanie podmieniłoby symulację każdemu). Tryb --sync też jest wyłączony,
bo świat taktuje carla-master.

Dodatkowa opcja --fps N: ile klatek na sekundę wysyła kamera (domyślnie 20, czyli w każdym
kroku symulacji). Mniej klatek = mniej danych w sieci.
"""

import sys

import carla

import manual_control as mc


def _blocked(message):
    def method(self, *args, **kwargs):
        self.hud.notification(message)
    return method


mc.World.next_weather = _blocked("Pogoda jest wspólna dla wszystkich - nie można jej zmienić")
mc.World.next_map_layer = _blocked("Warstwy mapy są wspólne dla wszystkich - nie można ich zmienić")
mc.World.load_map_layer = _blocked("Warstwy mapy są wspólne dla wszystkich - nie można ich zmienić")


def _no_recorder(self, *args, **kwargs):
    print("Nagrywanie i odtwarzanie symulacji jest wyłączone na wspólnym serwerze")
    return ""


carla.Client.start_recorder = _no_recorder
carla.Client.stop_recorder = _no_recorder
carla.Client.replay_file = _no_recorder

_camera_fps = 20.0
_camera_manager_init = mc.CameraManager.__init__


def _camera_manager_with_fps(self, *args, **kwargs):
    _camera_manager_init(self, *args, **kwargs)
    for item in self.sensors:
        blueprint = item[-1]
        if blueprint.id.startswith("sensor.camera") and blueprint.has_attribute("sensor_tick"):
            blueprint.set_attribute("sensor_tick", str(1.0 / _camera_fps))


mc.CameraManager.__init__ = _camera_manager_with_fps

if __name__ == "__main__":
    if "--sync" in sys.argv:
        sys.exit("--sync nie działa ze wspólnym serwerem: świat taktuje carla-master")
    if "--fps" in sys.argv:
        i = sys.argv.index("--fps")
        _camera_fps = float(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    mc.main()
