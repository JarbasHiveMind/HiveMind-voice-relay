# HiveMind Voice Relay

OpenVoiceOS Relay, connect to [HiveMind](https://github.com/JarbasHiveMind/HiveMind-core)

Similar to [voice-satellite](https://github.com/JarbasHiveMind/HiveMind-voice-sat), but STT and TTS are sent to HiveMind instead of handled on device

> NOTE: is using ovos-installer for the server this requires the `listener` profile

## Install

Install dependencies (if needed)

```bash
sudo apt-get install -y libpulse-dev libasound2-dev
```

Install with pip

```bash
$ pip install git+https://github.com/JarbasHiveMind/HiveMind-voice-relay
```

## Usage

```bash
Usage: hivemind-voice-relay [OPTIONS]

  connect to HiveMind

Options:
  --host TEXT      hivemind host
  --key TEXT       Access Key
  --password TEXT  Password for key derivation
  --port INTEGER   HiveMind port number
  --selfsigned     accept self signed certificates
  --help           Show this message and exit.

```


## Configuration

Voice relay uses the default OpenVoiceOS configuration `~/.config/mycroft/mycroft.conf`

Supported plugin types:
- Microphone  (required)
- VAD  (required)
- Audio Transformers  (optional, None by default)
- Dialog Transformers  (optional, None by default)
- TTS Transformers  (optional, None by default)
- PHAL  (optional, None by default)