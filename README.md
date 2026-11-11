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

## Development commands

Run from the repository root (build/test/clean also work from other directories):

```bash
source scripts/env.sh           # Lyrical + existing workspace overlay
./scripts/build.sh              # colcon build --symlink-install
./scripts/test.sh               # colcon test + test-result, nonzero on failures
./scripts/build.sh --packages-select robot_diagnostics
./scripts/test.sh --packages-select robot_diagnostics --pytest-args -q
./scripts/clean.sh              # preview only
./scripts/clean.sh --yes        # explicitly approve deleting build/, install/, log/
python3 -m unittest discover -s scripts/tests -v
```

Arguments are forwarded unchanged to colcon build/test. Test results are checked
for the whole workspace, so earlier failures in other packages also cause failure.
The environment script prints a hint if no overlay exists; it never edits `.bashrc`.
The clean script rejects symbolic links and mounted artifact directories.

In VS Code, use **Terminal → Run Task** and select **Build Workspace**,
**Test Workspace**, or **Clean Build Artifacts**. Build is also the default
Ctrl+Shift+B task. Cleaning defaults to preview; select `--yes` to approve deletion.
Personal VS Code settings remain ignored.

### Tooling validation (2026-11-12)

Objective: verify reproducible workspace commands, argument forwarding, failure
propagation, and guarded cleanup without changing ROS package source.
Validated on `feature/development-tooling`, base commit
`b538a306fd3803ce33f1ca4203f944ded27efd15`, with the uncommitted tooling changes:

```bash
bash -n scripts/*.sh
python3 -m unittest discover -s scripts/tests -v
./scripts/build.sh --event-handlers console_direct+
ROS_AUTOMATIC_DISCOVERY_RANGE=OFF ROS_STATIC_PEERS='' ROS_DOMAIN_ID=175 \
  RMW_IMPLEMENTATION=rmw_fastrtps_cpp ./scripts/test.sh --event-handlers console_direct+
./scripts/clean.sh
```

Results: Bash syntax passed; 9 tooling tests passed; 1 ROS package built;
51 ROS tests passed, with 0 errors, failures, or skips. Cleanup only previewed
the real workspace; deletion and unsafe-path rejection were tested in temporary
fixtures. JSON syntax and VS Code ignore exceptions were checked. VS Code task
interaction was not tested in the GUI; no physical robot validation was performed.

## Notes

Physical robot currently uses ROS 2 Jazzy.
Cross-distribution compatibility must be tested before deployment.
