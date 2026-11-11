#!/usr/bin/env bash
# Source this file from Bash; do not change the caller's shell options or cwd.
_ros2_workspace_env() {
    local root
    root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)" || return 1
    if [[ ! -r "/opt/ros/lyrical/setup.bash" ]]; then
        printf 'Error: ROS 2 Lyrical setup is missing: /opt/ros/lyrical/setup.bash\n' >&2
        return 1
    fi
    source "/opt/ros/lyrical/setup.bash" || return "$?"
    if [[ -f "$root/install/setup.bash" ]]; then
        source "$root/install/setup.bash" || return "$?"
    else
        printf 'Workspace overlay is not built yet. Run scripts/build.sh first.\n' >&2
    fi
}
if _ros2_workspace_env; then
    unset -f _ros2_workspace_env
else
    unset -f _ros2_workspace_env
    return 1 2>/dev/null || exit 1
fi
