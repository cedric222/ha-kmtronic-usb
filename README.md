# KMTronic USB Relay for Home Assistant

Native Home Assistant integration for [KMTronic](https://kmtronic.com) USB relay boards
(1, 2, 4 and 8 channels). No MQTT broker, add-on or middleware needed: Home Assistant
talks to the board directly over its USB serial port.

> The official `kmtronic` integration only supports the network (LAN/IP) boards.
> This one covers the USB ones.

## Features

- Config flow from the UI, with automatic USB discovery of the board
- **Real relay states** read back from the board (`FF 09 00`), polled every 10 s and after
  every command: no more "reset everything at startup"
- Each relay can be exposed as a **switch**, a **light**, a **button** (impulse with a
  configurable duration, for gates and garage doors) or disabled
- **Inverted** option for loads wired on the normally closed (NC) contact
- Survives unplug/replug: the serial port is reopened automatically
- English and French translations

## Installation

### HACS (recommended)

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/cedric222/ha-kmtronic-usb`,
   category *Integration*.
2. Install **KMTronic USB Relay** and restart Home Assistant.

### Manual

Copy `custom_components/kmtronic_usb` into your `config/custom_components/` folder and
restart Home Assistant.

## Configuration

1. Plug the board in. Home Assistant should show it under *Settings → Devices & services*
   as discovered; otherwise click *Add integration* and search for **KMTronic USB Relay**.
2. Pick the serial port. Prefer the `/dev/serial/by-id/usb-KMtronic_Ltd._USB_8_Relays-if00`
   style path, it is stable across reboots.
3. Open **Configure** on the integration to choose, for each relay, its type, whether it is
   inverted, and the pulse duration for buttons. The integration reloads automatically.

Entity names and icons are set the usual way, from each entity's settings.

On Home Assistant OS the USB device is available to Home Assistant Core without any extra
setting.

## Supported hardware

| Board | Status command | Tested |
|---|---|---|
| USB 8 relays (`04d8:f55e`) | `FF 09 00` | ✅ |
| USB 4 relays | `FF 09 00` | not yet |
| USB 1 / 2 relays | `FF 0N 03` | not yet |

Reports for other boards are welcome in the issues.

## Migrating from an MQTT bridge / add-on

1. Stop the add-on or daemon that was driving the board: only one program can use the
   serial port at a time.
2. Delete the old MQTT device in Home Assistant (this also clears its retained discovery
   messages).
3. Set up this integration, then rename the new entities (or give them the old entity IDs)
   so your automations keep working.

## Protocol

9600 baud, 8N1. `FF 0N 01` switches relay N on, `FF 0N 00` off. The driver is in
[`kmtronic.py`](custom_components/kmtronic_usb/kmtronic.py) and does not depend on Home
Assistant.

## License

MIT
