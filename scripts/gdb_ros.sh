#!/usr/bin/env bash
# cppdbg starts this MI debugger wrapper so GDB and its inferior inherit ROS.
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$root/scripts/env.sh"
command -v gdb >/dev/null || { printf 'Error: gdb is unavailable.\n' >&2; exit 1; }
exec gdb "$@"
