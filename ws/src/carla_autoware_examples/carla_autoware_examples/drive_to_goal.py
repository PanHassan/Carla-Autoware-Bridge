"""Przejazd do celu bez klikania w RViz - przez Autoware AD API.

Kolejno: inicjalizacja lokalizacji z GNSS -> ustawienie trasy do celu -> tryb autonomiczny
-> czekanie na dojazd. To te same usługi, których używają przyciski w RViz.

Uruchomienie (pozycja celu w układzie mapy, yaw w stopniach):
  ros2 run carla_autoware_examples drive_to_goal --ros-args \
      -p goal_x:=<x> -p goal_y:=<y> -p goal_yaw_deg:=<yaw>
Współrzędne celu najłatwiej odczytać tak: `ros2 topic echo /planning/mission_planning/goal`
i kliknięcie celu narzędziem "2D Goal Pose" w RViz.
"""

import math
import time

from autoware_adapi_v1_msgs.msg import LocalizationInitializationState
from autoware_adapi_v1_msgs.msg import OperationModeState
from autoware_adapi_v1_msgs.msg import RouteState
from autoware_adapi_v1_msgs.srv import ChangeOperationMode
from autoware_adapi_v1_msgs.srv import ClearRoute
from autoware_adapi_v1_msgs.srv import InitializeLocalization
from autoware_adapi_v1_msgs.srv import SetRoutePoints
from geometry_msgs.msg import Pose
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy

# Tematy stanu w AD API są "latched" (transient local) - trzeba użyć tego samego QoS.
API_STATE_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)


class DriveToGoal(Node):

    def __init__(self):
        super().__init__('drive_to_goal')
        self.declare_parameter('goal_x', 0.0)
        self.declare_parameter('goal_y', 0.0)
        self.declare_parameter('goal_z', 0.0)
        self.declare_parameter('goal_yaw_deg', 0.0)
        self.declare_parameter('timeout_s', 60.0)

        self.localization_state = None
        self.route_state = None
        self.operation_mode = None
        self.create_subscription(
            LocalizationInitializationState, '/api/localization/initialization_state',
            lambda m: setattr(self, 'localization_state', m), API_STATE_QOS)
        self.create_subscription(
            RouteState, '/api/routing/state',
            lambda m: setattr(self, 'route_state', m), API_STATE_QOS)
        self.create_subscription(
            OperationModeState, '/api/operation_mode/state',
            lambda m: setattr(self, 'operation_mode', m), API_STATE_QOS)

        self.cli_init = self.create_client(
            InitializeLocalization, '/api/localization/initialize')
        self.cli_clear_route = self.create_client(ClearRoute, '/api/routing/clear_route')
        self.cli_set_route = self.create_client(SetRoutePoints, '/api/routing/set_route_points')
        self.cli_autonomous = self.create_client(
            ChangeOperationMode, '/api/operation_mode/change_to_autonomous')

    # --- pomocnicze -------------------------------------------------------------------

    def wait_until(self, condition, what, timeout=None):
        timeout = timeout or self.get_parameter('timeout_s').value
        deadline = time.monotonic() + timeout
        while rclpy.ok() and not condition():
            if time.monotonic() > deadline:
                raise TimeoutError(f'Przekroczono czas oczekiwania: {what}')
            rclpy.spin_once(self, timeout_sec=0.2)

    def call(self, client, request):
        if not client.wait_for_service(timeout_sec=30.0):
            raise RuntimeError(f'Usługa {client.srv_name} niedostępna - czy Autoware działa?')
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        status = future.result().status
        if not status.success:
            raise RuntimeError(f'{client.srv_name}: {status.message} (kod {status.code})')
        return future.result()

    def goal_pose(self):
        p = Pose()
        p.position.x = self.get_parameter('goal_x').value
        p.position.y = self.get_parameter('goal_y').value
        p.position.z = self.get_parameter('goal_z').value
        yaw = math.radians(self.get_parameter('goal_yaw_deg').value)
        p.orientation.z = math.sin(yaw / 2.0)
        p.orientation.w = math.cos(yaw / 2.0)
        return p

    # --- scenariusz -------------------------------------------------------------------

    def run(self):
        log = self.get_logger()

        self.wait_until(lambda: self.localization_state is not None, 'stan lokalizacji')
        if self.localization_state.state != LocalizationInitializationState.INITIALIZED:
            log.info('1/4 Inicjalizacja lokalizacji z GNSS...')
            # Pusta lista pose = inicjalizacja na podstawie GNSS (jak "Init by GNSS" w RViz).
            self.call(self.cli_init, InitializeLocalization.Request())
            self.wait_until(
                lambda: self.localization_state.state
                == LocalizationInitializationState.INITIALIZED,
                'zainicjalizowana lokalizacja')
        log.info('1/4 Lokalizacja OK')

        log.info('2/4 Ustawianie trasy do celu...')
        self.wait_until(lambda: self.route_state is not None, 'stan trasy')
        if self.route_state.state != RouteState.UNSET:
            self.call(self.cli_clear_route, ClearRoute.Request())
        req = SetRoutePoints.Request()
        req.header.frame_id = 'map'
        req.header.stamp = self.get_clock().now().to_msg()
        req.goal = self.goal_pose()
        self.call(self.cli_set_route, req)

        log.info('3/4 Czekam aż planowanie pozwoli na tryb autonomiczny...')
        self.wait_until(
            lambda: self.operation_mode is not None
            and self.operation_mode.is_autonomous_mode_available,
            'dostępny tryb autonomiczny')
        self.call(self.cli_autonomous, ChangeOperationMode.Request())

        log.info('4/4 Jedziemy! Czekam na dojazd do celu...')
        self.wait_until(
            lambda: self.route_state.state == RouteState.ARRIVED,
            'dojazd do celu', timeout=float('inf'))
        log.info('Cel osiągnięty.')


def main(args=None):
    rclpy.init(args=args)
    node = DriveToGoal()
    try:
        node.run()
    except (RuntimeError, TimeoutError) as e:
        node.get_logger().error(str(e))
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
