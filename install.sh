#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$ROOT_DIR/package"
PLUGIN_ID="dev.codexbar.kde"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
ICON_SRC="$PACKAGE_DIR/contents/images/codexbar.png"
ICON_DEST_DIR="$DATA_HOME/icons/hicolor/256x256/apps"

chmod +x "$PACKAGE_DIR/contents/code/codexbar_kde.py"
mkdir -p "$ICON_DEST_DIR"
install -m 0644 "$ICON_SRC" "$ICON_DEST_DIR/codexbar.png"

if command -v kpackagetool6 >/dev/null 2>&1; then
    TOOL=kpackagetool6
elif command -v kpackagetool5 >/dev/null 2>&1; then
    TOOL=kpackagetool5
else
    echo "kpackagetool6 was not found. Install KDE Plasma SDK/tools first." >&2
    exit 1
fi

if "$TOOL" -t Plasma/Applet -l 2>/dev/null | grep -q "$PLUGIN_ID"; then
    if ! "$TOOL" -t Plasma/Applet -u "$PACKAGE_DIR"; then
        echo "Package update failed; replacing the user-installed copy directly." >&2
        rm -rf "$DATA_HOME/plasma/plasmoids/$PLUGIN_ID"
        if ! "$TOOL" -t Plasma/Applet -i "$PACKAGE_DIR"; then
            echo "Recovery install failed. The widget may not be available." >&2
            exit 1
        fi
    fi
else
    "$TOOL" -t Plasma/Applet -i "$PACKAGE_DIR"
fi

echo "Installed $PLUGIN_ID. Add 'CodexBar KDE' to your Plasma panel from Add Widgets."

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi
