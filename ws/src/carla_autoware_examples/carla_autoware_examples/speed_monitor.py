"""Najprostszy węzeł: czyta stan pojazdu z Autoware i publikuje prędkość w km/h.

Pokazuje podstawy: subskrypcja, publikacja, timer, parametry.
Uruchomienie: ros2 run carla_autoware_examples speed_monitor
"""

from autoware_vehicle_msgs.msg import VelocityReport
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32


class SpeedMonitor(Node):

    def __init__(self):
        super().__init__('speed_monitor')
        self.declare_parameter('speed_limit_kmh', 30.0)

        self._speed_kmh = 0.0
        self._position = None

        # Prędkość raportowana przez interfejs pojazdu (tu: autoware_carla_interface).
        self.create_subscription(
            VelocityReport, '/vehicle/status/velocity_status', self._on_velocity, 10)
        # Pozycja wyestymowana przez moduł lokalizacji Autoware (EKF).
        self.create_subscription(
            Odometry, '/localization/kinematic_state', self._on_odometry, 10)

        self._speed_pub = self.create_publisher(Float32, '~/speed_kmh', 10)
        self.create_timer(1.0, self._report)

    def _on_velocity(self, msg: VelocityReport):
        self._speed_kmh = msg.longitudinal_velocity * 3.6
        self._speed_pub.publish(Float32(data=self._speed_kmh))

    def _on_odometry(self, msg: Odometry):
        self._position = msg.pose.pose.position

    def _report(self):
        limit = self.get_parameter('speed_limit_kmh').value
        where = 'brak lokalizacji'
        if self._position is not None:
            where = f'x={self._position.x:.1f} y={self._position.y:.1f}'
        text = f'v={self._speed_kmh:5.1f} km/h, {where}'
        if self._speed_kmh > limit:
            self.get_logger().warn(f'{text} - przekroczono {limit:.0f} km/h!')
        else:
            self.get_logger().info(text)


def main(args=None):
    rclpy.init(args=args)
    node = SpeedMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
