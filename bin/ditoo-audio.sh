#!/usr/bin/env bash
# Keep the Ditoo Pro speaker connected and make it the default output whenever it
# (re)appears. When the speaker powers on it reconnects the link by itself but
# without the A2DP profile, so PipeWire never sees a sink; ConnectProfile on the
# Audio Sink UUID fixes that.
MAC=B1:21:81:C1:B3:E2
DEV=/org/bluez/hci0/dev_${MAC//:/_}
A2DP=0000110b-0000-1000-8000-00805f9b34fb
CARD=bluez_card.${MAC//:/_}
SINK=bluez_output.${MAC//:/_}.1

has_sink() { pactl list sinks short 2>/dev/null | grep -q "$SINK"; }
# The card survives A2DP<->HFP switches (the sink is briefly recreated), so it is
# what marks a genuine reconnect.
has_card() { pactl list cards short 2>/dev/null | grep -q "$CARD"; }
link_up() { bluetoothctl info "$MAC" 2>/dev/null | grep -q 'Connected: yes'; }

had_card=false
want_a2dp=false
last_page=0
while true; do
  if has_card && ! $had_card && ! has_sink; then
    sleep 1; continue
  fi
  if has_card; then
    # Only take over on reconnect, so a manual switch to another output sticks.
    # The profile is left to WirePlumber, which flips to HFP while the mic is in use.
    if ! $had_card; then
      want_a2dp=true
      pactl set-default-sink "$SINK"
      for i in $(pactl list sink-inputs short | awk '{print $1}'); do
        pactl move-sink-input "$i" "$SINK" 2>/dev/null
      done
      echo "Ditoo audio up, set as default output"
      had_card=true
    fi
    # Sometimes only HFP comes up; keep asking for A2DP, but not more often than
    # bluetoothd can finish an attempt, or it wedges with EBUSY until restarted.
    # A stored HFP choice would otherwise stick after reconnecting. Only done right
    # after a reconnect, when no capture stream can be relying on HFP yet.
    if $want_a2dp && pactl list cards 2>/dev/null | sed -n "/$CARD/,/Active Profile/p" | grep -q 'a2dp-sink:'; then
      pactl set-card-profile "$CARD" a2dp-sink && echo "Ditoo set to A2DP"
      want_a2dp=false
    fi
    now=$(date +%s)
    if ! pactl list cards 2>/dev/null | sed -n "/$CARD/,/Active Profile/p" | grep -q 'a2dp-sink:' \
        && (( now - last_page >= 30 )); then
      last_page=$now
      echo "Ditoo connected without A2DP, requesting it"
      dbus-send --system --print-reply --dest=org.bluez "$DEV" \
        org.bluez.Device1.ConnectProfile string:$A2DP >/dev/null 2>&1
    fi
  else
    $had_card && echo "Ditoo audio gone"
    had_card=false
    if link_up; then
      dbus-send --system --print-reply --dest=org.bluez "$DEV" \
        org.bluez.Device1.ConnectProfile string:$A2DP >/dev/null 2>&1
      sleep 3
      continue
    fi
    # Paging a switched-off speaker costs radio time other Bluetooth devices share.
    now=$(date +%s)
    if (( now - last_page >= 30 )); then
      last_page=$now
      bluetoothctl power on >/dev/null 2>&1
      timeout 15 bluetoothctl connect "$MAC" >/dev/null 2>&1 && continue
    fi
  fi
  sleep 5
done
