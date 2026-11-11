#!/usr/bin/env bash
set -eo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$root/scripts/env.sh"
command -v colcon >/dev/null || { printf 'Error: colcon is unavailable.\n' >&2; exit 1; }
cd -- "$root"
# Always inspect results, even when colcon test itself fails.
test_status=0
colcon test --return-code-on-test-failure "$@" || test_status=$?
result_status=0
colcon test-result --all --verbose || result_status=$?
if (( test_status != 0 )); then
    exit "$test_status"
fi
exit "$result_status"
