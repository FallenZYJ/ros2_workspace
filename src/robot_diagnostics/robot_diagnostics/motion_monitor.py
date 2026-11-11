"""Monitor motion messages without publishing commands or requiring TF."""

import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data


COMMAND_TYPES = {'Twist': Twist, 'TwistStamped': TwistStamped}
MIN_OUTPUT_RATE_HZ = 0.1
MAX_OUTPUT_RATE_HZ = 20.0


def output_period(value):
    """Bound log volume and validate the signed 64-bit nanosecond period."""
    rate = positive_number(value, 'output_rate_hz')
    if not MIN_OUTPUT_RATE_HZ <= rate <= MAX_OUTPUT_RATE_HZ:
        raise ValueError('output_rate_hz must be between 0.1 and 20.0 Hz (inclusive)')
    period = 1.0 / rate
    nanoseconds = period * 1_000_000_000
    if not math.isfinite(nanoseconds) or not 1 <= int(nanoseconds) <= 2**63 - 1:
        raise ValueError('output_rate_hz produces an invalid timer period in nanoseconds')
    return period


def positive_number(value, name):
    """Reject invalid timing parameters before constructing subscriptions."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite positive number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number')
    return float(value)


def format_sample(label, twist, received_at, now, timeout):
    """Describe the latest sample using local monotonic reception age."""
    if received_at is None:
        return f'{label}: NO DATA (尚未收到消息)'
    age = max(0.0, now - received_at)
    state = 'STALE' if age > timeout else 'FRESH'
    linear, angular = twist.linear, twist.angular
    return (
        f'{label}: linear[m/s]=({linear.x:.3f}, {linear.y:.3f}, {linear.z:.3f}), '
        f'angular[rad/s]=({angular.x:.3f}, {angular.y:.3f}, {angular.z:.3f}) '
        f'[{state}, age={age:.2f}s]'
    )


class MotionMonitor(Node):
    """Subscribe to odometry and exactly one configured command message type."""

    def __init__(self, **kwargs):
        super().__init__('motion_monitor', **kwargs)
        try:
            self._configure()
        except Exception:
            self.destroy_node()
            raise

    def _configure(self):
        defaults = {
            'odom_topic': '/odom',
            'cmd_vel_topic': '/cmd_vel',
            'cmd_vel_type': 'TwistStamped',
            'output_rate_hz': 1.0,
            'message_timeout_sec': 2.0,
        }
        config = {}
        for name, default in defaults.items():
            config[name] = self.declare_parameter(
                name, default,
                ParameterDescriptor(read_only=True, description='Set at node startup.'),
            ).value
        self._timeout = positive_number(config['message_timeout_sec'], 'message_timeout_sec')
        period = output_period(config['output_rate_hz'])
        if config['cmd_vel_type'] not in COMMAND_TYPES:
            raise ValueError('cmd_vel_type must be Twist or TwistStamped')
        for name in ('odom_topic', 'cmd_vel_topic'):
            if not isinstance(config[name], str) or not config[name].strip():
                raise ValueError(f'{name} must be a non-empty topic name')
        self._odom_twist = self._command_twist = None
        self._odom_received = self._command_received = None
        self._odom_subscription = self.create_subscription(
            Odometry, config['odom_topic'], self._on_odom, qos_profile_sensor_data,
        )
        self._command_subscription = self.create_subscription(
            COMMAND_TYPES[config['cmd_vel_type']], config['cmd_vel_topic'],
            self._on_command, qos_profile_sensor_data,
        )
        self._steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self._timer = self.create_timer(period, self._report, clock=self._steady_clock)

    def _on_odom(self, message):
        self._odom_twist = message.twist.twist
        self._odom_received = time.monotonic()

    def _on_command(self, message):
        self._command_twist = message.twist if isinstance(message, TwistStamped) else message
        self._command_received = time.monotonic()

    def _report(self):
        now = time.monotonic()
        self.get_logger().info(' | '.join([
            format_sample('odom', self._odom_twist, self._odom_received, now, self._timeout),
            format_sample('cmd_vel', self._command_twist, self._command_received,
                          now, self._timeout),
        ]))


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MotionMonitor()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except ValueError as exc:
        print(f'motion_monitor: {exc}', file=sys.stderr)
        return 1
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            # Idempotent context shutdown also handles signal-triggered shutdown.
            rclpy.try_shutdown()
