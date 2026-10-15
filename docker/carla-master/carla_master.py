#!/usr/bin/env python3
"""Jedyny proces, który taktuje świat CARLA.

Dzięki temu do jednej CARLA może podłączyć się kilka Autoware naraz. Każdy most
(autoware_carla_interface, patrz docker/autoware/external_tick.py) zamiast wywoływać
world.tick() wysyła do mastera po UDP "gotowe z klatką N" i czeka na kolejną klatkę.

Master po każdym kroku czeka, aż wszyscy podłączeni klienci zgłoszą gotowość (bariera),
ale nie dłużej niż CARLA_STEP_TIMEOUT - dzięki temu wolny lub zawieszony klient nie
zatrzymuje pozostałych. Czekanie jest też potrzebne dla wydajności: serwer CARLA obsługuje
zapytania klientów (sterowanie, stan auta) tylko między klatkami, więc taktowanie bez
przerwy spowalnia każde zapytanie o całą klatkę.

Świat nigdy nie biegnie szybciej niż czas rzeczywisty.
"""

import os
import select
import signal
import socket
import sys
import time

import carla

HOST = os.environ.get("CARLA_HOST", "localhost")
PORT = int(os.environ.get("CARLA_PORT", "2000"))
MASTER_PORT = int(os.environ.get("CARLA_MASTER_PORT", "2005"))
MAP = os.environ.get("CARLA_MAP", "Town01")
DELTA = float(os.environ.get("CARLA_DELTA", "0.05"))
# Najdłuższe czekanie na klientów w jednym kroku. Wolniejszy klient gubi klatki.
STEP_TIMEOUT = float(os.environ.get("CARLA_STEP_TIMEOUT", "0.25"))
# Klient, który tyle nie zgłosił gotowości, przestaje być uwzględniany w barierze...
CLIENT_TTL = 3.0
# ...a po tym czasie jest uznawany za odłączonego i jego auto jest usuwane. Dłuższy czas,
# żeby chwilowy zator w sieci nie wyrzucił klienta z symulacji.
LEFTOVER_TTL = 30.0
# Ile spóźnienia względem czasu rzeczywistego wolno nadrabiać szybszymi krokami.
CATCH_UP = 0.5
# Co ile sekund wypisywać statystyki (0 = nigdy).
STATS_PERIOD = float(os.environ.get("CARLA_STATS_PERIOD", "30"))

running = True


def stop(*_):
    global running
    running = False


def connect():
    # CARLA otwiera port zanim świat jest gotowy - czekamy aż faktycznie odpowiada.
    while running:
        try:
            client = carla.Client(HOST, PORT)
            client.set_timeout(10.0)
            client.get_world()
            return client
        except RuntimeError:
            print(f"Czekam na CARLA ({HOST}:{PORT})...", flush=True)
            time.sleep(2)
    sys.exit(0)


def ensure_settings(world):
    settings = world.get_settings()
    if settings.synchronous_mode and settings.fixed_delta_seconds == DELTA:
        return
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = DELTA
    world.apply_settings(settings)
    print(f"Tryb synchroniczny, krok {DELTA} s", flush=True)


def release(world):
    # Bez tego CARLA zostaje w trybie synchronicznym i zamarza, czekając na tick.
    settings = world.get_settings()
    settings.synchronous_mode = False
    world.apply_settings(settings)


class Clients:
    """Klienci zgłaszający gotowość po UDP: wiadomość "<id> <numer klatki> <nazwa auta>"."""

    def __init__(self, world):
        self.world = world
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", MASTER_PORT))
        self.done = {}  # id -> (ostatnia gotowa klatka, czas ostatniej wiadomości)
        self.roles = {}  # id -> role_name auta klienta
        self.waiting_for = set()  # klienci uwzględniani w barierze

    def receive(self, timeout):
        ready, _, _ = select.select([self.sock], [], [], timeout)
        while ready:
            try:
                client_id, frame, role = self.sock.recv(256).decode().split()
                if client_id not in self.done:
                    print(f"Klient dołączył: {client_id} (auto {role})", flush=True)
                elif client_id not in self.waiting_for:
                    print(f"Klient znów odpowiada: {client_id}", flush=True)
                self.waiting_for.add(client_id)
                self.done[client_id] = (int(frame), time.monotonic())
                self.roles[client_id] = role
            except ValueError:
                pass
            ready, _, _ = select.select([self.sock], [], [], 0)

    def forget_inactive(self):
        now = time.monotonic()
        for client_id, (_, seen) in list(self.done.items()):
            if now - seen > CLIENT_TTL and client_id in self.waiting_for:
                self.waiting_for.discard(client_id)
                print(f"Klient nie odpowiada, nie czekam na niego: {client_id}", flush=True)
            if now - seen > LEFTOVER_TTL:
                del self.done[client_id]
                print(f"Klient odłączony: {client_id}", flush=True)
                self.remove_leftovers(self.roles.pop(client_id))

    def remove_leftovers(self, role):
        """Usuwa auto (i jego czujniki) klienta, który zniknął bez sprzątania, np. po kill -9."""
        if role in self.roles.values():
            return  # tego samego auta używa nowy klient (np. ponowne uruchomienie)
        actors = self.world.get_actors()
        egos = [a for a in actors.filter("vehicle.*") if a.attributes.get("role_name") == role]
        ego_ids = {a.id for a in egos}
        sensors = [a for a in actors.filter("sensor.*") if a.parent and a.parent.id in ego_ids]
        for actor in sensors + egos:
            actor.destroy()
        if egos:
            print(f"Usunięto pozostawione auto {role} i {len(sensors)} czujników", flush=True)

    def wait_for(self, frame):
        deadline = time.monotonic() + STEP_TIMEOUT
        while True:
            self.forget_inactive()
            if all(self.done[c][0] >= frame for c in self.waiting_for):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            self.receive(min(remaining, 0.01))


class Stats:
    """Co STATS_PERIOD sekund wypisuje, na co idzie czas jednego kroku."""

    def __init__(self):
        self.reset(time.monotonic())

    def reset(self, now):
        self.start, self.steps, self.tick, self.wait, self.idle = now, 0, 0.0, 0.0, 0.0

    def add(self, tick, wait, idle, n_clients):
        self.steps += 1
        self.tick += tick
        self.wait += wait
        self.idle += idle
        now = time.monotonic()
        if STATS_PERIOD <= 0 or now - self.start < STATS_PERIOD:
            return
        ms = 1000.0 / self.steps
        print(
            f"{self.steps / (now - self.start):.1f} kroków/s, klientów: {n_clients} | na krok: "
            f"CARLA {self.tick * ms:.0f} ms, czekanie na klientów {self.wait * ms:.0f} ms, "
            f"wyrównanie do czasu rzeczywistego {self.idle * ms:.0f} ms",
            flush=True,
        )
        self.reset(now)


def main():
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    client = connect()
    world = client.load_world_if_different(MAP) or client.get_world()
    clients = Clients(world)
    print(f"Mapa: {world.get_map().name}", flush=True)
    ensure_settings(world)
    print(f"Czekam na zgłoszenia klientów na UDP {MASTER_PORT}", flush=True)

    next_tick = time.monotonic()
    last_check = next_tick
    stats = Stats()
    try:
        while running:
            t0 = time.monotonic()
            frame = world.tick()
            t1 = time.monotonic()
            clients.wait_for(frame)
            now = time.monotonic()
            # Co kilka sekund przywracamy ustawienia, gdyby zmienił je któryś klient.
            if now - last_check > 5.0:
                ensure_settings(world)
                last_check = now
            # Średnio nie szybciej niż czas rzeczywisty, ale szybkie kroki mogą nadrobić wolne
            # (np. te z obrazem z kamery). Przy dużym opóźnieniu nie nadrabiamy wstecz.
            next_tick += DELTA
            if now - next_tick > CATCH_UP:
                next_tick = now
            clients.receive(max(0.0, next_tick - time.monotonic()))
            stats.add(t1 - t0, now - t1, time.monotonic() - now, len(clients.waiting_for))
    finally:
        release(world)
        print("Master zatrzymany, CARLA w trybie asynchronicznym", flush=True)


if __name__ == "__main__":
    main()
