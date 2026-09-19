# Getting Started

## Prerequisites

### Hardware

- A microphone attached to the device (USB, 3.5 mm, or built-in).
- A speaker or audio output for TTS playback.

### Server

> **Your `hivemind-core` server must have the [hivemind-audio-binary-protocol](https://github.com/JarbasHiveMind/hivemind-audio-binary-protocol) binary plugin installed.** Plain `hivemind-core` does not provide STT or TTS. If you connect to it, wakeword triggers, but nothing is transcribed and no spoken response returns.

Install the `hivemind-audio-binary-protocol` plugin on a `hivemind-core` server that has the resources to run STT and TTS models. Then:

1. Install `hivemind-audio-binary-protocol` and (re)start `hivemind-core`.
2. Create a client credential (access key + password) using `hivemind-core add-client` on the server.
3. Note the host address and port (default `5678`).

### Python

Python 3.10 or later is required.

---

## Install

```bash
pip install HiveMind-voice-relay
```

This installs the `hivemind-voice-relay` CLI entry point and pulls in default plugins:
- `ovos-microphone-plugin-alsa`: ALSA microphone capture
- `ovos-vad-plugin-silero`: Silero VAD
- `ovos-stt-plugin-server` / `ovos-tts-plugin-server`: used internally for the relay transport

---

## Pairing (set identity)

Before connecting, store your credentials locally with `hivemind-client`:

```bash
hivemind-client set-identity \
  --key YOUR_ACCESS_KEY \
  --password YOUR_PASSWORD \
  --host wss://your-hivemind-host \
  --port 5678
```

Credentials are written to `~/.config/hivemind/_identity.json`. After this step you can run the satellite without passing flags every time.

To inspect the stored identity:

```bash
hivemind-client test-identity
```

---

## First run

```bash
hivemind-voice-relay
```

Or, passing flags explicitly (useful for testing before storing identity):

```bash
hivemind-voice-relay \
  --host wss://your-hivemind-host \
  --key YOUR_ACCESS_KEY \
  --password YOUR_PASSWORD \
  --port 5678
```

If the server uses a self-signed TLS certificate:

```bash
hivemind-voice-relay --selfsigned
```

---

## Verify it works

1. Watch the log output. You should see:
   ```
   HiveMind Voice Relay started.
   HiveMind Voice Relay is ready.
   ```
2. Say your wake word (default: **"hey mycroft"**).
3. The log prints `New loop state: IN_COMMAND` and a start-listening sound plays.
4. Speak a command (e.g. "what time is it").
5. The log prints the transcription (`STT: what time is it`) and the server sends back TTS audio that plays on the device.

If you see the wakeword trigger but no transcription arrives, check that `hivemind-core` has the `hivemind-audio-binary-protocol` plugin installed. See [Troubleshooting](troubleshooting.md).

---

## Next steps

- Swap the wake word or microphone plugin: [Configuration](configuration.md)
- Run as a system service: [Deployment](deployment.md)
- Understand the internal pipeline: [Architecture](architecture.md)

---
[Home](index.md) · [Configuration →](configuration.md)
