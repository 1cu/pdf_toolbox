#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  xvfb libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-render-util0 libxcb-xkb1 libxkbcommon0 libxrender1 libegl1 libgl1 \
  libdbus-1-3 libxcb-randr0 libxcb-xfixes0 libxcb-cursor0

echo "Qt headless deps installed."
