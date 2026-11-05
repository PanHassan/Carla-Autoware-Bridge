from dataclasses import dataclass, replace
from threading import Lock

from autoware_adapi_v1_msgs.msg import OperationModeState
from autoware_vehicle_msgs.msg import VelocityReport
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

API_QOS = QoSProfile(
    depth=1, reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL)

NAZWY_TRYBOW = {
    OperationModeState.UNKNOWN: 'UNKNOWN',
    OperationModeState.STOP: 'STOP',
    OperationModeState.AUTONOMOUS: 'AUTONOMOUS',
    OperationModeState.LOCAL: 'LOCAL',
    OperationModeState.REMOTE: 'REMOTE',
}


@dataclass
class StanLicznika:
    predkosc_kmh: float | None = None
    tryb: int | None = None
    dystans_m: float = 0.0
    max_predkosc_kmh: float = 0.0
    czas_autonomiczny_s: float = 0.0


def tekst(wartosc, wzor='{:.1f}'):
    return '—' if wartosc is None else wzor.format(wartosc)


class Licznik(Node):
    def __init__(self, nazwa='licznik_jazdy'):
        super().__init__(nazwa)
        self.stan = StanLicznika()
        self.ostatni_czas = None
        self._lock = Lock()
        self.create_subscription(
            VelocityReport, '/vehicle/status/velocity_status', self.on_velocity, 10)
        self.create_subscription(
            OperationModeState, '/api/operation_mode/state', self.on_mode, API_QOS)

    def snapshot(self):
        with self._lock:
            return replace(self.stan)

    def on_velocity(self, msg):
        with self._lock:
            s = self.stan
            s.predkosc_kmh = abs(msg.longitudinal_velocity) * 3.6
            s.max_predkosc_kmh = max(s.max_predkosc_kmh, s.predkosc_kmh)
            teraz = self.get_clock().now()
            if self.ostatni_czas is not None:
                dt = (teraz - self.ostatni_czas).nanoseconds / 1e9
                # Reset zegara symulacji nie może odejmować drogi ani czasu.
                if dt > 0:
                    s.dystans_m += abs(msg.longitudinal_velocity) * dt
                    if s.tryb == OperationModeState.AUTONOMOUS:
                        s.czas_autonomiczny_s += dt
            self.ostatni_czas = teraz

    def on_mode(self, msg):
        with self._lock:
            self.stan.tryb = msg.mode

    def podsumowanie(self):
        s = self.snapshot()
        return (
            f'v={tekst(s.predkosc_kmh)} km/h, max={s.max_predkosc_kmh:.1f} km/h, '
            f'dystans={s.dystans_m:.0f} m, tryb={NAZWY_TRYBOW.get(s.tryb, "—")}, '
            f'autonomicznie={s.czas_autonomiczny_s:.0f} s')


def main(args=None):
    rclpy.init(args=args)
    node = Licznik()
    node.create_timer(1.0, lambda: node.get_logger().info(node.podsumowanie()))
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
