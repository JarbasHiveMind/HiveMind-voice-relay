# HiveMind Voice Relay

OpenVoiceOS Relay, connect to [HiveMind](https://github.com/JarbasHiveMind/HiveMind-core)

Similar to [voice-satellite](https://github.com/JarbasHiveMind/HiveMind-voice-sat), but STT and TTS are sent to HiveMind instead of handled on device

running TTS/STT via hivemind has the advantage of access control, ie, requires an access key to use the plugins vs the non-authenticated public servers

## Install

> NOTE: if using ovos-installer for the server side, the `listener` profile is required

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


Voice relay is built on top of [ovos-listener](https://openvoiceos.github.io/ovos-technical-manual/speech_service/) and [ovos-audio](https://openvoiceos.github.io/ovos-technical-manual/audio_service/), it uses the same OpenVoiceOS configuration `~/.config/mycroft/mycroft.conf`

Supported plugin types:
- [Microphone](https://openvoiceos.github.io/ovos-technical-manual/mic_plugins/) (required)
- [VAD](https://openvoiceos.github.io/ovos-technical-manual/vad_plugins/) (required)
- [WakeWord](https://openvoiceos.github.io/ovos-technical-manual/ww_plugins/) (required)
- [Media Playback Plugins](https://openvoiceos.github.io/ovos-technical-manual/media_plugins/) (optional)
- [OCP Plugins](https://openvoiceos.github.io/ovos-technical-manual/ocp_plugins/) (optional)
- [Audio Transformers](https://openvoiceos.github.io/ovos-technical-manual/transformer_plugins/) (optional)
- [Dialog Transformers](https://openvoiceos.github.io/ovos-technical-manual/transformer_plugins/) (optional)
- [TTS Transformers](https://openvoiceos.github.io/ovos-technical-manual/transformer_plugins/) (optional)
- [PHAL](https://openvoiceos.github.io/ovos-technical-manual/PHAL/) (optional)

