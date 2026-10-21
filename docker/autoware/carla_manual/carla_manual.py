#!/usr/bin/env python3
"""Ręczna jazda (manual_control.py z CARLA 0.9.16) we wspólnym świecie z carla-master.

manual_control.py jest bez zmian. Tu tylko blokujemy to, co zmieniłoby świat wszystkim
podłączonym: pogodę (C), warstwy mapy (V/B) oraz nagrywanie i odtwarzanie symulacji
(CTRL+R/CTRL+P - odtwarzanie podmieniłoby symulację każdemu). Tryb --sync też jest wyłączony,
bo świat taktuje carla-master.
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

if __name__ == "__main__":
    if "--sync" in sys.argv:
        sys.exit("--sync nie działa ze wspólnym serwerem: świat taktuje carla-master")
    mc.main()
