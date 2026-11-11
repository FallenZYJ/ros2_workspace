#!/usr/bin/env bash
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$root/scripts/env.sh"
command -v colcon >/dev/null || { printf 'Error: colcon is unavailable.\n' >&2; exit 1; }
cd -- "$root"
exec colcon build --symlink-install "$@"
