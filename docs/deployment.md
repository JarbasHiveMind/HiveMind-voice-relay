# Deployment

## systemd service

Create a unit file to run voice-relay as a system service.

**`/etc/systemd/system/hivemind-voice-relay.service`**

```ini
[Unit]
Description=HiveMind Voice Relay
After=network.target sound.target

[Service]
Type=simple
User=YOUR_USER
ExecStart=/home/YOUR_USER/.local/bin/hivemind-voice-relay
Restart=on-failure
RestartSec=5
Environment=HOME=/home/YOUR_USER

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USER` with the user account under which the relay should run (the one whose `~/.config/hivemind/identity2.json` and `~/.config/mycroft/mycroft.conf` files are set up).

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hivemind-voice-relay
sudo systemctl start hivemind-voice-relay
```

Check status and logs:

```bash
systemctl status hivemind-voice-relay
journalctl -u hivemind-voice-relay -f
```

---

## Raspberry Pi

### Recommended OS

Raspberry Pi OS Lite (64-bit) works well. Install Python 3.10+ if it is not the system default:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### ALSA microphone

The default microphone plugin (`ovos-microphone-plugin-alsa`) uses ALSA. Verify your microphone is visible:

```bash
arecord -l
```

If the microphone is on a non-default card, set it in `mycroft.conf`:

```json
{
  "microphone": {
    "module": "ovos-microphone-plugin-alsa",
    "device_name": "plughw:1,0"
  }
}
```

### Audio output (speaker)

ALSA output is used for TTS playback. Check available output devices:

```bash
aplay -l
```

Set the default ALSA output in `/etc/asound.conf` or `~/.asoundrc`:

```
defaults.pcm.card 0
defaults.ctl.card 0
```

### Install in a virtual environment

On Raspberry Pi it is recommended to install in a venv to avoid conflicts with system packages:

```bash
python3 -m venv ~/.venvs/hivemind-relay
source ~/.venvs/hivemind-relay/bin/activate
pip install HiveMind-voice-relay
```

Update `ExecStart` in the systemd unit accordingly:

```ini
ExecStart=/home/YOUR_USER/.venvs/hivemind-relay/bin/hivemind-voice-relay
```

### Performance tips

- Use `ovos-vad-plugin-webrtcvad` instead of Silero VAD to reduce CPU load on low-end Pi boards:
  ```bash
  pip install ovos-vad-plugin-webrtcvad
  ```
  ```json
  { "listener": { "VAD": { "module": "ovos-vad-plugin-webrtcvad" } } }
  ```
- Choose a lightweight wakeword plugin such as `ovos-ww-plugin-precise-lite`.

---

## Autostart without systemd

For desktop or headless environments without systemd, add to crontab:

```bash
crontab -e
```

```
@reboot /home/YOUR_USER/.local/bin/hivemind-voice-relay >> /home/YOUR_USER/hivemind-relay.log 2>&1
```

---

## TLS / SSL

When connecting to a server over TLS (`wss://`):

- If the server uses a certificate from a recognised CA, no special config is needed.
- If the server uses a self-signed certificate, pass `--selfsigned`:

  ```bash
  hivemind-voice-relay --host wss://your-host --selfsigned
  ```

  In the systemd unit:

  ```ini
  ExecStart=/home/YOUR_USER/.local/bin/hivemind-voice-relay --selfsigned
  ```
