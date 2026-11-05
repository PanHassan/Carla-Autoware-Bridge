from autoware_vehicle_msgs.msg import VelocityReport
import rclpy
from rclpy.node import Node


class Predkosc(Node):
    def __init__(self):
        super().__init__('predkosc')
        self.create_subscription(
            VelocityReport, '/vehicle/status/velocity_status', self.on_velocity, 10)

    def on_velocity(self, msg):
        self.get_logger().info(
            f'prędkość: {msg.longitudinal_velocity * 3.6:.1f} km/h')


def main(args=None):
    rclpy.init(args=args)
    node = Predkosc()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
