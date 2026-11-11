#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if (( $# > 1 )) || { (( $# == 1 )) && [[ -n "$1" && "$1" != --yes ]]; }; then
    printf 'Usage: %s [--yes]\n' "$0" >&2
    exit 2
fi
[[ "$root" != / && -d "$root/src" && -f "$root/AGENTS.md" ]] || {
    printf 'Error: invalid workspace root: %s\n' "$root" >&2; exit 1;
}
# Validate every target before deleting any. Reject symlinks, including dangling ones.
targets=()
for name in build install log; do
    target="$root/$name"
    if [[ -L "$target" ]] || [[ -e "$target" && ! -d "$target" ]]; then
        printf 'Error: unsafe artifact directory: %s\n' "$target" >&2; exit 1
    fi
    resolved="$(realpath -m -- "$target")"
    [[ "$resolved" == "$root/$name" && "$resolved" != "$root" ]] || {
        printf 'Error: target escapes workspace: %s\n' "$target" >&2; exit 1;
    }
    if mountpoint -q -- "$target"; then
        printf 'Error: refusing mounted directory: %s\n' "$target" >&2; exit 1
    fi
    targets+=("$target")
done
printf 'Artifact directories:\n'
printf '  %s\n' "${targets[@]}"
if [[ "${1:-}" == --yes ]]; then
    rm -rf --one-file-system -- "${targets[@]}"
else
    printf 'Preview only. Pass --yes to delete these directories.\n'
fi
