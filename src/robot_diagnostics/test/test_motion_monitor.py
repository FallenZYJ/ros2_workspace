"""Offline tests: no DDS participants, publishers, or robot connections."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node

from robot_diagnostics.motion_monitor import MotionMonitor, format_sample, positive_number


@pytest.fixture
def make_monitor():
    patches = []

    def create(**overrides):
        def declare(name, default, descriptor):
            assert descriptor.read_only
            return SimpleNamespace(value=overrides.get(name, default))

        replacements = {
            '__init__': Mock(return_value=None),
            'declare_parameter': Mock(side_effect=declare),
            'create_subscription': Mock(),
            'create_timer': Mock(),
            'destroy_node': Mock(),
            'get_logger': Mock(return_value=Mock()),
        }
        for name, replacement in replacements.items():
            item = patch.object(Node, name, replacement)
            item.start()
            patches.append(item)
        return MotionMonitor()

    yield create
    for item in reversed(patches):
        item.stop()


@pytest.mark.parametrize('kind,expected', [('Twist', Twist), ('TwistStamped', TwistStamped)])
def test_exactly_one_command_subscription(make_monitor, kind, expected):
    node = make_monitor(cmd_vel_type=kind, odom_topic='/test/odom',
                        cmd_vel_topic='/test/cmd', output_rate_hz=2.0)
    calls = node.create_subscription.call_args_list
    assert len(calls) == 2
    assert calls[0].args[:2] == (Odometry, '/test/odom')
    assert calls[1].args[:2] == (expected, '/test/cmd')
    assert node.create_timer.call_args.args[0] == 0.5


def test_defaults_and_startup_report(make_monitor):
    node = make_monitor()
    assert node.create_subscription.call_args.args[:2] == (TwistStamped, '/cmd_vel')
    assert node.create_timer.call_args.args[0] == 1.0
    node._report()
    assert node.get_logger().info.call_args.args[0].count('NO DATA') == 2


@pytest.mark.parametrize('kind', [Twist, TwistStamped])
def test_callbacks_and_stale_report(make_monitor, kind):
    node = make_monitor(cmd_vel_type=kind.__name__, message_timeout_sec=2.0)
    odom = Odometry()
    odom.twist.twist.linear.x = 1.25
    odom.twist.twist.angular.z = -0.5
    command = kind()
    twist = command.twist if kind is TwistStamped else command
    twist.linear.x = 0.75
    with patch('robot_diagnostics.motion_monitor.time.monotonic', return_value=10.0):
        node._on_odom(odom)
        node._on_command(command)
        node._report()
    report = node.get_logger().info.call_args.args[0]
    assert report.count('FRESH') == 2
    assert '1.250' in report and '-0.500' in report and '0.750' in report
    with patch('robot_diagnostics.motion_monitor.time.monotonic', return_value=12.01):
        node._report()
    assert node.get_logger().info.call_args.args[0].count('STALE') == 2


def test_timeout_boundary_and_missing_stream():
    assert 'FRESH' in format_sample('odom', Twist(), 10.0, 12.0, 2.0)
    assert 'STALE' in format_sample('odom', Twist(), 10.0, 12.001, 2.0)
    assert 'NO DATA' in format_sample('cmd_vel', None, None, 12.0, 2.0)


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), True, '1'])
def test_invalid_timing(value):
    with pytest.raises(ValueError):
        positive_number(value, 'timing')


@pytest.mark.parametrize('overrides', [
    {'cmd_vel_type': 'invalid'}, {'output_rate_hz': 0.0},
    {'message_timeout_sec': -1.0}, {'odom_topic': ''}, {'cmd_vel_topic': ' '},
])
def test_invalid_config_creates_no_subscriptions(make_monitor, overrides):
    with pytest.raises(ValueError):
        make_monitor(**overrides)
    Node.create_subscription.assert_not_called()
    Node.destroy_node.assert_called_once()


@pytest.mark.parametrize('value', [
    float('nan'), float('inf'), -float('inf'), 0.0, -1.0,
    1e10, 1e-300, 0.099, 20.001,
])
def test_output_frequency_rejected_before_subscriptions(make_monitor, value):
    with pytest.raises(ValueError, match='output_rate_hz'):
        make_monitor(output_rate_hz=value)
    Node.create_subscription.assert_not_called()
    Node.create_timer.assert_not_called()
    Node.destroy_node.assert_called_once()


@pytest.mark.parametrize('rate,period_ns', [(0.1, 10_000_000_000), (20.0, 50_000_000)])
def test_output_frequency_boundaries(rate, period_ns):
    from robot_diagnostics.motion_monitor import output_period
    assert int(output_period(rate) * 1_000_000_000) == period_ns


@pytest.mark.parametrize('rate', [1e10, 1e-12])
def test_nanosecond_period_guard(rate):
    from robot_diagnostics import motion_monitor as module
    # Exercise both defensive guards if the public range is widened later.
    with patch.object(module, 'MIN_OUTPUT_RATE_HZ', 1e-12), \
            patch.object(module, 'MAX_OUTPUT_RATE_HZ', 1e10), \
            pytest.raises(ValueError, match='nanoseconds'):
        module.output_period(rate)


@pytest.mark.parametrize('failure', [KeyboardInterrupt, 'external', RuntimeError])
def test_main_spin_exception_cleanup(failure):
    from rclpy.executors import ExternalShutdownException
    from robot_diagnostics import motion_monitor as module
    exception = ExternalShutdownException if failure == 'external' else failure
    node = Mock()
    with patch.object(module.rclpy, 'init'), \
            patch.object(module, 'MotionMonitor', return_value=node), \
            patch.object(module.rclpy, 'spin', side_effect=exception), \
            patch.object(module.rclpy, 'try_shutdown') as shutdown:
        if exception is RuntimeError:
            with pytest.raises(RuntimeError):
                module.main([])
        else:
            module.main([])
        node.destroy_node.assert_called_once()
        shutdown.assert_called_once()


def test_main_constructor_failure_cleanup(capsys):
    from robot_diagnostics import motion_monitor as module
    with patch.object(module.rclpy, 'init'), \
            patch.object(module, 'MotionMonitor', side_effect=ValueError('invalid frequency')), \
            patch.object(module.rclpy, 'try_shutdown') as shutdown:
        assert module.main([]) == 1
        assert 'invalid frequency' in capsys.readouterr().err
        shutdown.assert_called_once()


def test_main_destroy_failure_still_shuts_down():
    from robot_diagnostics import motion_monitor as module
    node = Mock()
    node.destroy_node.side_effect = RuntimeError('destroy failed')
    with patch.object(module.rclpy, 'init'), \
            patch.object(module, 'MotionMonitor', return_value=node), \
            patch.object(module.rclpy, 'spin'), \
            patch.object(module.rclpy, 'try_shutdown') as shutdown:
        with pytest.raises(RuntimeError, match='destroy failed'):
            module.main([])
        shutdown.assert_called_once()


def test_partial_subscription_failure_is_cleaned(make_monitor):
    node = make_monitor()
    node.create_subscription.reset_mock()
    node.create_subscription.side_effect = [Mock(), RuntimeError('subscription failed')]
    with pytest.raises(RuntimeError, match='subscription failed'):
        MotionMonitor()
    node.destroy_node.assert_called_once()
