"""Real Lyrical interfaces with discovery OFF and a separate test domain.

Only zero command messages are published on UUID-named test topics. All
participants live in the same context; no robot or other ROS network is needed.
"""
import os
import time
import uuid
from unittest.mock import patch

import pytest
import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.context import Context
from rclpy.exceptions import InvalidParameterTypeException
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import (
    QoSCompatibility, QoSProfile, ReliabilityPolicy, qos_check_compatible,
)

from robot_diagnostics.motion_monitor import MotionMonitor, main


@pytest.fixture(autouse=True)
def isolated_dds(monkeypatch, tmp_path):
    # OFF prevents discovery of other participants, including on localhost.
    # Fast DDS shares one participant for nodes in this context.
    monkeypatch.setenv('ROS_DOMAIN_ID', str(100 + os.getpid() % 100))
    monkeypatch.setenv('RMW_IMPLEMENTATION', 'rmw_fastrtps_cpp')
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE', 'OFF')
    monkeypatch.setenv('ROS_STATIC_PEERS', '')
    monkeypatch.setenv('ROS_SECURITY_ENABLE', 'false')
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path / 'ros_logs'))
    monkeypatch.setenv('SKIP_DEFAULT_XML', '1')
    for key in ('ROS_DISCOVERY_SERVER', 'ROS_SUPER_CLIENT', 'ROS_LOCALHOST_ONLY',
                'FASTDDS_DEFAULT_PROFILES_FILE', 'FASTRTPS_DEFAULT_PROFILES_FILE',
                'RMW_FASTRTPS_USE_QOS_FROM_XML'):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def ros_context():
    context = Context()
    context.init(args=[], domain_id=int(os.environ['ROS_DOMAIN_ID']))
    try:
        yield context
    finally:
        context.try_shutdown()
        assert not context.ok()


def spin_until(executor, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.02)
        if predicate():
            return
    raise AssertionError('ROS condition not reached before timeout')


@pytest.mark.parametrize('kind', [Twist, TwistStamped])
@pytest.mark.parametrize('reliability', [ReliabilityPolicy.BEST_EFFORT,
                                         ReliabilityPolicy.RELIABLE])
def test_real_topics_timer_parameters_and_freshness(ros_context, capfd, kind, reliability):
    prefix = '/diagnostics_test_' + uuid.uuid4().hex
    monitor = MotionMonitor(
        context=ros_context, enable_rosout=False,
        cli_args=['--ros-args', '-p', 'cmd_vel_type:=' + kind.__name__,
                  '-p', 'odom_topic:=' + prefix + '/odom',
                  '-p', 'cmd_vel_topic:=' + prefix + '/cmd',
                  '-p', 'output_rate_hz:=20.0', '-p', 'message_timeout_sec:=0.4'],
    )
    peer = Node('diagnostics_test_peer', context=ros_context, enable_rosout=False)
    executor = SingleThreadedExecutor(context=ros_context)
    executor.add_node(monitor)
    executor.add_node(peer)
    try:
        assert monitor.get_parameter('cmd_vel_type').value == kind.__name__
        assert monitor.get_parameter('message_timeout_sec').value == 0.4
        assert monitor.describe_parameter('output_rate_hz').read_only
        result = monitor.set_parameters([Parameter('output_rate_hz', value=1.0)])[0]
        assert not result.successful
        assert monitor.get_parameter('output_rate_hz').value == 20.0
        assert monitor._timer.timer_period_ns == 50_000_000
        assert len(list(monitor.subscriptions)) == 2
        qos = QoSProfile(depth=5, reliability=reliability)
        for subscription in monitor.subscriptions:
            compatibility, reason = qos_check_compatible(qos, subscription.qos_profile)
            # SYSTEM_DEFAULT liveliness yields WARNING in Lyrical. Actual
            # endpoint matching and delivery below resolve that uncertainty.
            assert compatibility != QoSCompatibility.ERROR, reason
        odom_pub = peer.create_publisher(Odometry, prefix + '/odom', qos)
        command_pub = peer.create_publisher(kind, prefix + '/cmd', qos)
        spin_until(executor, lambda: odom_pub.get_subscription_count() == 1
                   and command_pub.get_subscription_count() == 1)

        latest = ['']

        def report_has(odom_state, command_state):
            output = capfd.readouterr()
            for line in (output.out + output.err).splitlines():
                if 'odom:' in line and 'cmd_vel:' in line:
                    latest[0] = line
            if not latest[0]:
                return False
            odom, command = latest[0].split(' | ')
            return odom_state in odom and command_state in command

        def wait_report(odom_state, command_state):
            # Require a new timer-driven report after each state transition.
            capfd.readouterr()
            latest[0] = ''
            spin_until(executor, lambda: report_has(odom_state, command_state))

        wait_report('NO DATA', 'NO DATA')
        odom = Odometry()
        odom.twist.twist.linear.x = 1.25
        odom_timer = peer.create_timer(0.03, lambda: odom_pub.publish(odom))
        wait_report('FRESH', 'NO DATA')
        # Commands deliberately remain all-zero, even inside the isolated domain.
        command_timer = peer.create_timer(0.03, lambda: command_pub.publish(kind()))
        wait_report('FRESH', 'FRESH')
        assert monitor._odom_twist.linear.x == 1.25
        assert monitor._command_twist.linear.x == 0.0
        odom_timer.cancel()
        wait_report('STALE', 'FRESH')
        odom_timer.reset()
        wait_report('FRESH', 'FRESH')
        command_timer.cancel()
        wait_report('FRESH', 'STALE')
        command_timer.reset()
        wait_report('FRESH', 'FRESH')
        odom_timer.cancel()
        command_timer.cancel()
        wait_report('STALE', 'STALE')
    finally:
        executor.remove_node(peer)
        executor.remove_node(monitor)
        peer.destroy_node()
        monitor.destroy_node()
        executor.shutdown()
    assert not list(monitor.subscriptions)
    assert not list(monitor.timers)
    # Repeated shutdown is safe; fixture calls try_shutdown again as well.
    ros_context.try_shutdown()
    ros_context.try_shutdown()
    assert not ros_context.ok()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'),
                                   0.0, -1.0, 1e10, 1e-300])
def test_real_invalid_frequency(ros_context, value):
    with pytest.raises(ValueError, match='output_rate_hz'):
        MotionMonitor(context=ros_context, enable_rosout=False,
                      parameter_overrides=[Parameter('output_rate_hz', value=value)])
    # Failed configuration must untrack the partially constructed node.
    assert not ros_context._Context__node_weak_ref_list


def test_real_parameter_type_enforcement(ros_context):
    with pytest.raises(InvalidParameterTypeException):
        MotionMonitor(context=ros_context, enable_rosout=False,
                      parameter_overrides=[Parameter('output_rate_hz', value='fast')])
    assert not ros_context._Context__node_weak_ref_list


def test_real_external_shutdown_during_executor_wait(ros_context):
    """Trigger context shutdown while the real wait set is blocked."""
    import threading

    monitor = MotionMonitor(context=ros_context, enable_rosout=False)
    executor = SingleThreadedExecutor(context=ros_context)
    executor.add_node(monitor)
    errors = []
    started = threading.Event()

    def wait():
        started.set()
        try:
            executor.spin_once(timeout_sec=3.0)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=wait)
    try:
        # The timer must not wake the wait set before shutdown.
        monitor._timer.cancel()
        thread.start()
        assert started.wait(timeout=1.0)
        time.sleep(0.1)
        ros_context.try_shutdown()
        thread.join(timeout=5.0)
        assert not thread.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], ExternalShutdownException)
    finally:
        ros_context.try_shutdown()
        thread.join(timeout=5.0)
        executor.shutdown()


@pytest.mark.parametrize('already_shutdown', [False, True])
def test_real_main_cleanup(already_shutdown):
    """Run the real main, node and timer; emulate only the spin lifecycle."""
    nodes = []

    def spin(node):
        nodes.append(node)
        if already_shutdown:
            rclpy.try_shutdown()
            raise ExternalShutdownException()
        executor = SingleThreadedExecutor(context=node.context)
        executor.add_node(node)
        try:
            # A real timer wakes the executor before an ordinary interrupt.
            executor.spin_once(timeout_sec=1.5)
            raise KeyboardInterrupt()
        finally:
            executor.remove_node(node)
            executor.shutdown()

    with patch.object(rclpy, 'spin', side_effect=spin):
        main(['--ros-args', '-p', 'output_rate_hz:=20.0'])
    assert not rclpy.ok()
    assert len(nodes) == 1
    assert not list(nodes[0].subscriptions)
    assert not list(nodes[0].timers)
