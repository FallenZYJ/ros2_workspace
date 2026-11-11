# ROS 2 Robotics Development Instructions

## 1. Development Environment
- OS: Ubuntu 26.04 LTS running under WSL2 on Windows 11.
- ROS distribution: ROS 2 Lyrical.
- Workspace: /home/legion/ros2_workspace.
- Build system: colcon.
- Main tools: Python, C++, CMake, Git, VS Code, Codex.
- Navigation framework: Nav2.
- Physical robot currently uses ROS 2 Jazzy.

## 2. General Development Rules
- Inspect relevant project files before changing code.
- Prefer minimal, reversible changes.
- Explain the purpose of important modifications.
- Follow ROS 2 conventions and package structures.
- Do not modify unrelated packages.
- Never invent test results or claim unperformed validation.
- Do not install or upgrade system dependencies without approval.

## 3. ROS 2 Development
- Source /opt/ros/lyrical/setup.bash before ROS commands.
- Use colcon to build affected packages.
- Prefer `scripts/build.sh` and `scripts/test.sh` for workspace builds and tests; pass package selection arguments as needed.
- Request explicit user approval before deleting build artifacts. Preview with `scripts/clean.sh`; use `--yes` only after approval.
- Run available tests when appropriate.
- Maintain valid package.xml and build configuration.
- Do not assume ROS 2 Jazzy and Lyrical are fully compatible.
- Keep ROS interfaces and dependencies explicit.

## 4. Navigation and Localization
- Prefer Nav2 standard components and plugins.
- Pay attention to A*, RPP, AMCL, EKF, velocity smoother, and goal checker configurations.
- Check TF relationships between map, odom, base_link, and laser frames.
- Consider differential-drive kinematic constraints.
- Avoid changing unrelated navigation parameters simultaneously.
- Record original and modified parameter values.

## 5. Hardware Safety
- Do not connect to, deploy to, or control the physical robot without explicit approval.
- Do not send velocity commands to a physical robot autonomously.
- Do not start navigation or motor movement without approval.
- Do not modify hardware calibration or safety limits without approval.
- Simulation results are not equivalent to physical robot validation.

## 6. Git Workflow
- Use dedicated branches for experiments.
- Keep commits focused and descriptive.
- Never force-push or delete branches without approval.
- Do not overwrite unrelated user changes.
- Explain significant code differences before committing.
- Do not commit secrets, credentials, build outputs, or large recordings.

## 7. Experiment Documentation
- Document experiment objectives and hypotheses.
- Record the tested configuration and relevant Git commit.
- Distinguish verified results from assumptions.
- Record failures and unresolved issues.
- Prefer reproducible experiments over unstructured parameter changes.

## 8. Reporting
After completing a development task, summarize:
1. Files inspected and modified.
2. Changes made and their rationale.
3. Build and test commands executed.
4. Actual test results.
5. Remaining risks or unresolved issues.
6. Suggested next validation steps.
