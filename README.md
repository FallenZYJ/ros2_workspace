# ROS 2 Robotics Workspace

Development workspace for ROS 2 robotics projects.

## Development Environment

- Windows 11
- WSL2
- Ubuntu 26.04 LTS
- ROS 2 Lyrical
- Nav2
- VS Code
- Git & GitHub
- OpenAI Codex

## Workspace Structure

- src/: ROS 2 packages
- build/: Build artifacts (ignored)
- install/: Installed workspace packages (ignored)
- log/: Build logs (ignored)

## Build

source /opt/ros/lyrical/setup.bash
colcon build --symlink-install

## Notes

Physical robot currently uses ROS 2 Jazzy.
Cross-distribution compatibility must be tested before deployment.
