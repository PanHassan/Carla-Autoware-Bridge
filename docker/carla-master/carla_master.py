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

Master może też dodać ruch uliczny (CARLA_NPC_VEHICLES aut na autopilocie). Traffic Manager
musi działać w procesie, który taktuje świat - w innym procesie auta stoją w miejscu.

Przy CARLA z oknem (./scripts/carla_server.sh --window) master ustawia też kamerę okna
(CARLA_SPECTATOR): "top" - na starcie z góry na całą mapę, potem swobodna (domyślnie), "follow" - za
kolejnymi autami, "off" - kamera sterowana w oknie myszą i klawiszami WASD.
"""

import math
import os
import random
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
# Liczba aut ruchu ulicznego (autopilot przez Traffic Manager), 0 = bez ruchu.
NPC_VEHICLES = int(os.environ.get("CARLA_NPC_VEHICLES", "0"))
NPC_ROLE = "npc"
TM_PORT = 8000
# Kamera okna CARLA: "follow" = śledzi auta, "off" = sterowana ręcznie w oknie.
SPECTATOR = os.environ.get("CARLA_SPECTATOR", "top")
SPECTATOR_SWITCH = float(os.environ.get("CARLA_SPECTATOR_SWITCH", "20"))
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


class Traffic:
    """Ruch uliczny: auta na autopilocie sterowane przez Traffic Manager w tym procesie."""

    def __init__(self, client, world):
        self.client = client
        self.world = world
        self.vehicles = []
        # Auta po poprzednim uruchomieniu mastera (np. po awarii) stoją bez Traffic Managera.
        self.destroy([v.id for v in world.get_actors().filter("vehicle.*")
                      if v.attributes.get("role_name") == NPC_ROLE])
        if NPC_VEHICLES <= 0:
            return
        tm = client.get_trafficmanager(TM_PORT)
        tm.set_synchronous_mode(True)
        tm.set_global_distance_to_leading_vehicle(2.5)
        tm.global_percentage_speed_difference(30.0)
        blueprints = [bp for bp in world.get_blueprint_library().filter("vehicle.*")
                      if int(bp.get_attribute("number_of_wheels")) == 4]
        spawn_points = world.get_map().get_spawn_points()
        random.shuffle(spawn_points)
        batch = []
        for transform in spawn_points[:NPC_VEHICLES]:
            bp = random.choice(blueprints)
            bp.set_attribute("role_name", NPC_ROLE)
            batch.append(carla.command.SpawnActor(bp, transform).then(
                carla.command.SetAutopilot(carla.command.FutureActor, True, TM_PORT)))
        self.vehicles = [r.actor_id for r in client.apply_batch_sync(batch, True) if not r.error]
        print(f"Ruch uliczny: {len(self.vehicles)} aut", flush=True)

    def destroy(self, ids):
        if ids:
            # Najpierw wyłączyć autopilota - usuwanie aut sterowanych przez TM potrafi wywrócić CARLA.
            self.client.apply_batch_sync([carla.command.SetAutopilot(i, False, TM_PORT) for i in ids])
            self.client.apply_batch_sync([carla.command.DestroyActor(i) for i in ids])

    def cleanup(self):
        self.destroy(self.vehicles)
        self.vehicles = []


class Spectator:
    """Kamera okna CARLA (tryb CARLA_SPECTATOR).

    - "top": na starcie widok z góry na całą mapę (widać wszystkie auta), potem kamera jest
      swobodna - mysz i WASD w oknie CARLA.
    - "follow": za jednym autem studenta, co CARLA_SPECTATOR_SWITCH s przełącza na kolejne.
    """

    # follow: kamera za autem
    DISTANCE, HEIGHT, PITCH = 8.0, 4.0, -15.0
    # top: zapas wokół dróg mapy [m]
    MARGIN = 10.0

    def __init__(self, world, mode):
        self.world = world
        self.mode = mode
        self.spectator = world.get_spectator()
        self.target = None
        self.since = 0.0
        self.last_refresh = 0.0
        self.candidates = []
        if mode == "top":
            self.spectator.set_transform(self.map_overview(world))

    def map_overview(self, world):
        # Zasięg dróg mapy (punkty co 10 m), kamera nad środkiem tak wysoko, żeby objąć całość.
        points = [w.transform.location for w in world.get_map().generate_waypoints(10.0)]
        x0, x1 = min(p.x for p in points), max(p.x for p in points)
        y0, y1 = min(p.y for p in points), max(p.y for p in points)
        # Kąt widzenia kamery 90° w poziomie; w pionie przy oknie ~16:10 mniej (tan ~0.625),
        # więc liczymy wysokość dla węższego kierunku.
        height = (max(x1 - x0, y1 - y0) / 2 + self.MARGIN) / 0.625
        # Skośnie z góry, nie pionowo: przy pitch -90° sterowanie kamerą w oknie (WASD, mysz)
        # wariuje. Kamera cofnięta od środka mapy tak, żeby środek był w środku kadru.
        pitch, yaw = -65.0, -90.0
        back = height / math.tan(math.radians(-pitch))
        x = (x0 + x1) / 2 - back * math.cos(math.radians(yaw))
        y = (y0 + y1) / 2 - back * math.sin(math.radians(yaw))
        return carla.Transform(carla.Location(x=x, y=y, z=height),
                               carla.Rotation(pitch=pitch, yaw=yaw))

    def refresh(self, now):
        # Lista aut co sekundę, nie w każdym kroku - to zapytanie do serwera.
        vehicles = list(self.world.get_actors().filter("vehicle.*"))
        egos = [v for v in vehicles if v.attributes.get("role_name", "").startswith("ego_")]
        self.candidates = sorted(egos or vehicles, key=lambda v: v.id)
        self.last_refresh = now

    def update(self):
        now = time.monotonic()
        if self.mode == "top":
            return  # widok ustawiony raz w __init__, dalej kamerą steruje użytkownik
        if now - self.last_refresh > 1.0:
            self.refresh(now)
        self.update_follow(now)

    def update_follow(self, now):
        if not self.candidates:
            self.target = None
            return
        ids = {v.id for v in self.candidates}
        if self.target is None or self.target.id not in ids or now - self.since > SPECTATOR_SWITCH:
            current = self.target.id if self.target else -1
            self.target = next((v for v in self.candidates if v.id > current), self.candidates[0])
            self.since = now
            name = self.target.attributes.get("role_name") or self.target.type_id
            print(f"Kamera okna śledzi: {name}", flush=True)
        t = self.target.get_transform()
        yaw = math.radians(t.rotation.yaw)
        location = t.location + carla.Location(
            x=-self.DISTANCE * math.cos(yaw), y=-self.DISTANCE * math.sin(yaw), z=self.HEIGHT
        )
        self.spectator.set_transform(
            carla.Transform(location, carla.Rotation(pitch=self.PITCH, yaw=t.rotation.yaw))
        )


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
    traffic = Traffic(client, world)
    print(f"Czekam na zgłoszenia klientów na UDP {MASTER_PORT}", flush=True)

    next_tick = time.monotonic()
    last_check = next_tick
    stats = Stats()
    spectator = Spectator(world, SPECTATOR) if SPECTATOR in ("top", "follow") else None
    try:
        while running:
            if spectator:
                spectator.update()
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
        try:
            traffic.cleanup()
        finally:
            release(world)
        print("Master zatrzymany, CARLA w trybie asynchronicznym", flush=True)


if __name__ == "__main__":
    main()
