#!/usr/bin/env bash
# Link the tools into ~/.local/bin and install the units and WirePlumber override.
set -euo pipefail
cd "$(dirname "$0")"
here=$PWD

mkdir -p ~/.local/bin ~/.config/systemd/user ~/.local/share/wireplumber/scripts/device
for f in bin/*; do ln -sfn "$here/$f" ~/.local/bin/"$(basename "$f")"; done
cp systemd/* ~/.config/systemd/user/
# Takes effect the next time WirePlumber starts; restarting it now would drop A2DP.
cp wireplumber/autoswitch-bluetooth-profile.lua ~/.local/share/wireplumber/scripts/device/

venv=~/.local/share/ditoo/venv
if [ ! -x "$venv/bin/python" ]; then
  python3 -m venv "$venv"
  "$venv/bin/pip" install -q -r requirements.txt
fi

systemctl --user daemon-reload
systemctl --user enable --now ditoo-audio.service ditoo-github.timer
echo "Installed."
