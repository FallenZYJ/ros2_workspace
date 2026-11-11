#!/usr/bin/env bash
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$root/scripts/env.sh"
cd -- "$root"
python3 -c 'import debugpy' || {
    printf 'Error: python3 cannot import debugpy. Check the selected ROS Python environment.\n' >&2
    exit 1
}
# Run the installed console_scripts wrapper, which calls the registered main().
# Running the source module directly would not invoke its entry point.
entry="$(python3 - "$root" <<'PY'
from pathlib import Path
import sys
from ament_index_python.packages import get_package_prefix, PackageNotFoundError

try:
    prefix = Path(get_package_prefix('robot_diagnostics')).resolve()
    prefix.relative_to((Path(sys.argv[1]) / 'install').resolve())
    entry = prefix / 'lib' / 'robot_diagnostics' / 'motion_monitor'
    if not entry.is_file():
        raise FileNotFoundError(entry)
except (PackageNotFoundError, ValueError, FileNotFoundError) as exc:
    print(f'Error: local motion_monitor installation unavailable: {exc}. '
          'Run scripts/build.sh --packages-select robot_diagnostics first.', file=sys.stderr)
    sys.exit(1)
print(entry)
PY
)"
printf 'Starting debugpy at 127.0.0.1:5678; waiting for a debugger before running motion_monitor.\n'
exec python3 -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 --wait-for-client "$entry" "$@"
