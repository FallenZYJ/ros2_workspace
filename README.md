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

## VS Code debugging (WSL)

Open this folder in a VS Code **WSL** window with Python Debugger and C/C++
extensions enabled there. Existing build/test/clean tasks are unchanged.

### Python motion_monitor

1. Build the installed entry point with
   `./scripts/build.sh --packages-select robot_diagnostics`.
2. In a WSL terminal, start an isolated local debugging session:

   ```bash
   ROS_AUTOMATIC_DISCOVERY_RANGE=OFF ROS_STATIC_PEERS='' ROS_DOMAIN_ID=175 \
     ./scripts/debug_motion_monitor.sh --ros-args -p output_rate_hz:=1.0
   ```

   The script sources `scripts/env.sh`, locates this workspace's installed
   `console_scripts` wrapper through the ament index, and starts Python debugpy
   on **127.0.0.1:5678** with `--wait-for-client`. ROS arguments are forwarded
   unchanged. `setup.py` registers
   `motion_monitor = robot_diagnostics.motion_monitor:main`; no source-file
   `__main__` guard is needed. The node does not run until the debugger connects.
   The script inherits your ROS networking environment; keep discovery OFF for
   local work and remove inherited discovery-server/vendor profile overrides.
3. Set a breakpoint in
   `src/robot_diagnostics/robot_diagnostics/motion_monitor.py`, for example on
   `rclpy.init(args=args)` in `main`, or in `_report`.
4. Select **Python: Attach motion_monitor (localhost)** in Run and Debug and
   press F5. Continue/step after the breakpoint. No `preLaunchTask` waits for
   the server: start it manually before F5. Only one session can use port 5678.
5. Stop/disconnect in VS Code, then press Ctrl+C in the server terminal if it
   remains alive (also use Ctrl+C to cancel before attaching). Confirm the
   terminal process exited before starting another session. Disconnecting an
   attached debugger can leave the node running.

### C++ templates

There is currently no C++ node. Both GDB configurations prompt for the absolute
executable path; attach additionally prompts for a process. Use the executable
matching that process, built with symbols (for a future CMake package, pass
`--cmake-args -DCMAKE_BUILD_TYPE=Debug` to `scripts/build.sh`). Edit launch `args`
for ROS arguments as needed. `scripts/gdb_ros.sh` loads the ROS/workspace
environment before starting GDB in MI mode. An attached process must already
have been started with its own ROS environment; attaching cannot change it.
Linux ptrace permissions may prevent attach; no sudo or system policy changes
are performed. These templates do not start any existing ROS node automatically.

### Debugging validation (2026-11-12)

Objective: verify the installed Python entry can wait for localhost attachment
without executing the node, while preserving existing tooling. Tested on
`feature/ros2-debugging`, base commit
`fd226c87f9cbcd9f82d3e74bcbcc3a0f92c5b64f`, with uncommitted debugging changes.

- `bash -n scripts/*.sh`: passed.
- `python3 -m unittest discover -s scripts/tests -v`: 13 tests passed, including
  JSON configuration, argument forwarding, dependency failure, and GDB wrapper.
- `./scripts/build.sh --packages-select robot_diagnostics`: 1 package built.
- `ROS_AUTOMATIC_DISCOVERY_RANGE=OFF ROS_STATIC_PEERS='' ROS_DOMAIN_ID=175
  RMW_IMPLEMENTATION=rmw_fastrtps_cpp ./scripts/test.sh --packages-select
  robot_diagnostics --event-handlers console_direct+`: 51 passed; 0 errors,
  failures, or skips.
- `./scripts/gdb_ros.sh --batch -ex 'show environment ROS_DISTRO'`:
  reported `ROS_DISTRO = lyrical` using GDB 17.1.
- Real debugpy 1.8.19 smoke check from `/tmp`: the helper resolved the installed
  entry, listened only on `127.0.0.1:5678`, and remained waiting without a client.
  The check used isolated ROS settings, stopped its process group, and confirmed
  the listener was gone. The sandbox initially denied socket creation; the
  check succeeded outside it. No debugger was attached and no node code ran.
- Existing Tasks and ROS package source have no diff; personal VS Code settings
  remain ignored. GUI breakpoint/stop behavior and C++ launch/attach are untested.
  Next validation: follow the Python steps above in VS Code; test C++ templates
  when an actual local executable is available.

References: [debugpy command line](https://github.com/microsoft/debugpy/wiki/Command-Line-Reference)
and [VS Code C++ configuration](https://code.visualstudio.com/docs/cpp/launch-json-reference).

## Notes

Physical robot currently uses ROS 2 Jazzy.
Cross-distribution compatibility must be tested before deployment.
