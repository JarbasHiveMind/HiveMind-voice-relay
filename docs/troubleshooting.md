# Troubleshooting

## Wakeword triggers but nothing happens (no transcription, no spoken response)

**Most likely cause:** the satellite is connected to `hivemind-core` instead of `HiveMind-listener`.

`hivemind-core` does not handle the `recognizer_loop:b64_transcribe` or `speak:b64_audio` messages. The relay sends audio to the server and waits up to 20 seconds for a transcription response; when none arrives it logs:

```
Timeout waiting for STT transcriptions
```

and returns an empty string. No intent fires and no TTS audio is sent back.

**Fix:** ensure the server is running `HiveMind-listener`, not `hivemind-core`.
Alternatively, run `hivemind-core` together with `ovos-audio` and `ovos-dinkum-listener` on the same machine to provide the same capabilities.

---

## No audio captured / microphone not found

```
Error opening ALSA device
```
or the relay starts but never triggers on speech.

Check that the microphone is visible to ALSA:

```bash
arecord -l
```

If no devices are listed, the microphone is not recognised by the OS. Check USB/driver support.

If the wrong device is selected, specify it in `~/.config/mycroft/mycroft.conf`:

```json
{
  "microphone": {
    "module": "ovos-microphone-plugin-alsa",
    "device_name": "plughw:1,0"
  }
}
```

Try recording a short clip to confirm the device works:

```bash
arecord -D plughw:1,0 -d 3 test.wav && aplay test.wav
```

---

## TLS / self-signed certificate error

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

The server is using a self-signed certificate. Pass `--selfsigned`:

```bash
hivemind-voice-relay --selfsigned
```

---

## Wakeword never triggers

1. Confirm you are using the correct wake word. The default is **"hey mycroft"**. Check `listener.wake_word` in `~/.config/mycroft/mycroft.conf`.

2. Confirm the wake word plugin is installed:

   ```bash
   pip show ovos-ww-plugin-precise-lite
   ```

3. Test VAD separately — VAD silence incorrectly rejecting speech will prevent frames from reaching the wakeword detector. Try switching VAD to `ovos-vad-plugin-webrtcvad` to rule out a Silero model issue:

   ```bash
   pip install ovos-vad-plugin-webrtcvad
   ```

   ```json
   { "listener": { "VAD": { "module": "ovos-vad-plugin-webrtcvad" } } }
   ```

4. Increase microphone gain at the OS level:

   ```bash
   alsamixer
   ```

---

## NodeIdentity not set error

```
RuntimeError: NodeIdentity not set, please pass key/password/host or call 'hivemind-client set-identity'
```

No credentials are stored and none were passed on the command line. Run:

```bash
hivemind-client set-identity --key YOUR_KEY --password YOUR_PASSWORD --host wss://your-host
```

Or pass all three flags directly:

```bash
hivemind-voice-relay --key YOUR_KEY --password YOUR_PASSWORD --host wss://your-host
```

---

## TTS audio received but no sound plays

1. Check that the default ALSA output device is correct:

   ```bash
   aplay -l
   aplay /usr/share/sounds/alsa/Front_Center.wav
   ```

2. If the wrong card is selected, set defaults in `~/.asoundrc`:

   ```
   defaults.pcm.card 1
   defaults.ctl.card 1
   ```

3. Check volume is not muted:

   ```bash
   alsamixer
   ```

---

## Connection drops and does not reconnect

The `hivemind-bus-client` library handles reconnection internally. If the service exits on disconnect rather than reconnecting, the systemd `Restart=on-failure` directive will relaunch it. Check the service unit includes:

```ini
Restart=on-failure
RestartSec=5
```

---

## PHAL not available

```
PHAL is not available
```

This is an informational message, not an error. PHAL (platform hardware abstraction layer) is optional. If you need platform-specific hardware support (e.g. LEDs on a Mark 1), install:

```bash
pip install ovos-PHAL
```

Otherwise the message can be ignored.
