# Sourced by Galinia’s GTK 3 utility launchers.
# Native appearance hooks are optional; use standard GTK behavior by default.
[ "${GALINIA_EXPERIMENTAL_LAYOUT:-0}" = 1 ] || return 0
source_file="$HOME/.local/share/galinia/settings-layout.c"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/galinia"
module="$cache/settings-layout.so"
if [ -f "$source_file" ] && [ ! "$module" -nt "$source_file" ] && command -v cc >/dev/null; then
    mkdir -p "$cache"
    temporary=$(mktemp "$cache/settings-layout.XXXXXX")
    if cc -Wall -Wextra -shared -fPIC -Wl,-z,noexecstack "$source_file" -o "$temporary"; then
        mv -f "$temporary" "$module"
    else
        unlink "$temporary"
    fi
fi
if [ -r "$module" ]; then
    export GTK_MODULES="$module${GTK_MODULES:+:$GTK_MODULES}"
fi
