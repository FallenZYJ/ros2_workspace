# robot_diagnostics

只读 ROS 2 Lyrical / ament_python 功能包。`motion_monitor` 监视里程计和控制器速度命令，不创建发布器，不发送运动命令。

## 构建与运行

在工作空间根目录执行：

```bash
source /opt/ros/lyrical/setup.bash
colcon build --packages-select robot_diagnostics
source install/setup.bash
ros2 run robot_diagnostics motion_monitor
```

默认订阅 `/odom` (`nav_msgs/msg/Odometry`) 和 `/cmd_vel` (`geometry_msgs/msg/TwistStamped`)。若实际控制器使用 `Twist`：

```bash
ros2 run robot_diagnostics motion_monitor --ros-args -p cmd_vel_type:=Twist
```

修改话题和时序的示例：

```bash
ros2 run robot_diagnostics motion_monitor --ros-args \
  -p odom_topic:=/filtered/odom -p cmd_vel_topic:=/controller/cmd_vel \
  -p cmd_vel_type:=TwistStamped -p output_rate_hz:=2.0 \
  -p message_timeout_sec:=1.5
```

## 参数

参数均为启动时设置、运行中只读；修改需重启节点。

| 参数 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `odom_topic` | string | `/odom` | 里程计话题 |
| `cmd_vel_topic` | string | `/cmd_vel` | 控制器命令话题 |
| `cmd_vel_type` | string | `TwistStamped` | 仅接受 `Twist` 或 `TwistStamped`，只创建所选类型的一个订阅 |
| `output_rate_hz` | double | `1.0` | 日志频率，范围 `[0.1, 20.0]` Hz（包含边界） |
| `message_timeout_sec` | double | `2.0` | 接收超时阈值，有限正数 |

每行输出两个流最近的 linear xyz（m/s）、angular xyz（rad/s）以及各自状态：`NO DATA` 为启动后未收到消息，`FRESH` 为接收年龄不大于阈值，`STALE` 为超过阈值。过期数据保留最后数值，收到新消息后恢复为 FRESH。两个流分别判断。输出定时器和接收年龄使用单调时钟，仿真时间暂停不会阻止过期提示。

频率下限对应最长 10 秒的输出间隔，上限用于限制诊断日志开销（最短 50 毫秒）。除有限性和范围校验外，节点还检查换算后的周期是否为有效的正数、有符号 64 位纳秒值。NaN、Infinity、零、负数和超范围值在创建订阅和定时器之前被拒绝，命令行输出明确错误并返回非零退出码。正常 KeyboardInterrupt 或 ExternalShutdownException 退出时会清理节点，并通过幂等的 `rclpy.try_shutdown()` 避免重复关闭上下文。

## 测试

```bash
source /opt/ros/lyrical/setup.bash
colcon test --packages-select robot_diagnostics
colcon test-result --test-result-base build/robot_diagnostics --verbose
```

保留模拟 Node 接口的单元测试，覆盖类型选择、订阅数量、参数、频率边界、未接收消息、回调、超时及异常清理。

集成测试使用真实 Node、Publisher、Subscription、Timer 和 ROS 参数系统，覆盖 Twist / TwistStamped 与 best-effort / reliable 发布者的四种组合、未收到数据、两个流分别过期和恢复、参数只读与类型约束、真实等待集关闭异常和 main 清理。测试依赖 `rmw_fastrtps_cpp`，使用独立域（`ROS_DOMAIN_ID=100 + PID % 100`）、`ROS_AUTOMATIC_DISCOVERY_RANGE=OFF`、空静态对端，并禁用外部 Fast DDS XML / discovery server 配置。测试对象在同一进程、同一上下文中通信；关闭发现可阻止同域其他进程自动匹配。使用 UUID 话题，只发布零速度命令，不访问默认 `/cmd_vel` 或实体机器人。Fast DDS 仍可能需要本机套接字和共享内存权限。

## 局限性

- 采用 sensor_data QoS（best effort、volatile、keep last 5），可接收常见 reliable 或 best-effort 发布器，但可能丢帧；不接收历史消息。
- 不自动探测或转换命令类型，配置须与发布者匹配；类型不匹配通常显示 NO DATA。默认类型是本包选择，并非所有 Lyrical 控制器的保证。
- 超时仅表示本机距离最近一次接收的时长，不检查消息 header 时间戳，不检测传输前已陈旧的数据。
- 不转换坐标系或检查 TF；里程计速度遵循其 child_frame_id，命令速度坐标系取决于发布者。日志数值不能直接作为跟踪误差。
- 不订阅电机反馈，不验证运动安全性，不发布 diagnostic_msgs 状态；仅输出日志。
- 集成测试验证本机 Fast DDS 通信与 QoS 匹配，不涵盖跨主机通信、其他 RMW、信号投递的全部时序或硬件行为。实体机器人当前为 Jazzy，跨发行版部署需另行验证。
- 包维护者邮箱为占位值，发布前需替换为实际维护信息。
