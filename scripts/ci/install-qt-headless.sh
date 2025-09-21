#!/usr/bin/env bash
set -euo pipefail

if (( EUID != 0 )); then
    if command -v sudo >/dev/null 2>&1; then
        exec sudo -E bash "$0" "$@"
    else
        echo "This script must run as root. Re-run as root or install sudo." >&2
        exit 1
    fi
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get is required to install Qt dependencies. Please install it first." >&2
    exit 1
fi

apt-get update -y
apt-get install -y --no-install-recommends \
    xvfb libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-render-util0 libxcb-xkb1 libxkbcommon0 libxrender1 libegl1 libgl1 \
    libdbus-1-3 libxcb-randr0 libxcb-xfixes0 libxcb-cursor0 libxcb-shape0

echo "Install complete."
