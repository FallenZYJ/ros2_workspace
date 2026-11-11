# ROS 2 CI

`workflows/ros2-ci.yml` runs for pull requests targeting `main` and pushes to
`main`, on a GitHub-hosted `ubuntu-26.04` runner. Only `contents: read` is granted;
checkout does not persist credentials. No personal tokens or deployment secrets
are needed. No robot drivers, launch files, navigation, or deployment are started.

## Workflow steps

1. Check out the code and verify Ubuntu 26.04 / Resolute.
2. Use the ROS Tooling Working Group's `setup-ros` action to configure ROS apt
   repositories and development tools, without installing the desktop variant.
3. Explicitly install `ros-dev-tools`, `ros-lyrical-ros-base`, and
   `ros-lyrical-rmw-fastrtps-cpp`. Initialize rosdep only when its default source
   file is absent; update Lyrical rules and install dependencies declared under
   `src`, including test dependencies. Installation occurs on the runner only.
4. Source Lyrical and run `colcon build --symlink-install` for the workspace.
5. Source the workspace and run `colcon test --return-code-on-test-failure`.
   GitHub's explicit `bash` shell enables `-e` and `-o pipefail`. There is no
   `continue-on-error` or error-suppressing fallback.
6. After an attempted test run, even a failing one, execute
   `colcon test-result --all --verbose` and save its output. A failing result
   command still fails the job through the `tee` pipeline. Require the current
   package's pytest XML file to exist.
7. Always write a job summary and attempt to upload colcon logs, JUnit XML,
   available ROS logs and the text report, retained for 14 days. An early setup
   failure can leave no report; the job remains failed and its step logs explain
   why. Summary and artifact steps cannot turn a failed job into success.

## DDS isolation reviewed

The workflow sets Fast DDS, discovery `OFF`, an empty static-peer list, domain
175, and `SKIP_DEFAULT_XML=1`; it clears discovery-server and external XML/QoS
environment overrides before tests. The existing integration fixture independently
sets discovery `OFF`, clears static peers and overrides, selects a per-process
domain (`100 + PID % 100`), and puts logs in pytest temporary directories.

Real publishers and subscribers share a process/context and use UUID-named test
topics. Command messages are all zero. These tests require no external ROS peer.
Domain IDs alone are not a security boundary; disabling discovery and removing
explicit peers is essential. The workflow is for GitHub-hosted runners, not a
self-hosted machine attached to a robot. It does not provide a network sandbox
for arbitrary future test code. Fixture ROS logs may be embedded in pytest's
captured output rather than the workflow-level ROS log directory.

## Verified references

Action tags were resolved through the public GitHub API and pinned to commit SHAs:

| Action | Verified tag | Commit |
| --- | --- | --- |
| `actions/checkout` | `v4.2.2` | `11bd71901bbe5b1630ceea73d27597364c9af683` |
| `ros-tooling/setup-ros` | `v0.7` | `649ef6bcd696da05bc27ceb3fab69d810c0daeab` |
| `actions/upload-artifact` | `v4.6.2` | `ea165f8d65b6e75b540449e92b4886f43607fa02` |

- [setup-ros usage and supported platforms](https://github.com/ros-tooling/setup-ros)
- [Pinned setup-ros action inputs, including Lyrical](https://github.com/ros-tooling/setup-ros/blob/649ef6bcd696da05bc27ceb3fab69d810c0daeab/action.yml)
- [Lyrical supported platforms](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/lyrical/supported-platforms.rst)
- [GitHub-hosted runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

APT packages and rosdep rules are not version-locked. A first GitHub run must
still validate the runner image, repository/package availability, dependency
installation, Action execution, timing of DDS integration tests, summary display
and artifact upload. Local checks cannot substitute for that run.

## Local validation (2026-11-12)

On Ubuntu 26.04 / Lyrical, against repository base `0613111` plus these uncommitted
CI files:

- `colcon build --symlink-install --event-handlers console_direct+`: passed.
- `colcon test --return-code-on-test-failure --event-handlers console_direct+`:
  51 passed, including the 15 real-interface integration cases.
- `colcon test-result --all --verbose`: 51 tests, zero errors, failures or skips.
- YAML structure and every embedded Bash script's syntax: passed.
- A simulated failing command piped through `tee` with GitHub's Bash flags
  preserved exit code 7 and stopped the following command.
- actionlint v1.7.12: passed with only the precise unknown-`ubuntu-26.04` label
  diagnostic excluded. Its built-in label catalog is older than GitHub's current
  official runner list. The runner label was separately verified against GitHub
  documentation. actionlint found an invalid job-level `runner.temp` reference
  during initial validation; the reference was moved to step-level `env`.

No APT/rosdep installation or GitHub job was run locally. No source or test files
were changed, and no commit, merge, push, robot connection or deployment occurred.
