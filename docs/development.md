# Development & tests

## Install from source

```bash
git clone https://github.com/JarbasHiveMind/HiveMind-voice-relay
cd HiveMind-voice-relay
uv pip install -e ".[e2e]"
```

`pyproject.toml` is the single packaging source of truth. Runtime dependencies
live in `[project.dependencies]` and the test/e2e dependencies live in the `e2e`
extra (the `test` extra is an alias of `e2e` for the shared CI workflows).

The microphone plugin needs ALSA headers at build time:

```bash
sudo apt-get install libasound2-dev   # Debian/Ubuntu
```

## Running the tests

```bash
pytest tests/
```

All tests are end-to-end and live under `tests/e2e/`:

| File | Covers |
|---|---|
| `test_relay_e2e.py` | the **real** relay client classes over a real bus |
| `test_bridge1_conformance.py` | OVOS-BRIDGE-1 / SESSION-1 conformance |
| `test_acl.py` | ACL policy admission (allowed-types, skill blacklist) |

## How the E2E suite is wired

The suite uses the [`hivescope`](https://github.com/JarbasHiveMind/hivescope)
harness to run a **real `hivemind-core` master in-process**, with a real
WebSocket server (`TopologyBuilder.add_master(..., use_loopback=True)`). The
relay's own `HiveMindSTT`, `HMCallbacks`, and `HMPlayback` classes connect to it
over a **real `HiveMessageBusClient`**, the same client, handshake, crypto, and
ACL path as production.

What is **mocked**, so no real devices or outbound network are touched:

- **Mic / VAD / wakeword / audio capture**: `OVOSMicrophoneFactory`,
  `OVOSVADFactory`, and `OVOSWakeWordFactory` are stubbed. Captured audio is fed
  in as a pre-built silent `AudioData` buffer. No microphone is opened.
- **Remote STT / TTS endpoints**: in production the
  `hivemind-audio-binary-protocol` plugin on the server answers
  `recognizer_loop:b64_transcribe` and `speak:b64_audio`. The tests register a
  small stub handler on the master's agent bus that plays that role and replies
  with a `.response` addressed back to the originating relay peer, so no real
  STT/TTS engine or model is loaded.
- **TTS playback queue**: `HMPlayback` is built without starting the OVOS audio
  service. The test asserts on the queued playback item instead of driving a
  speaker.

No `importorskip` / `skipif` is used to dodge a missing dependency. The `e2e`
extra installs everything the suite needs, so every test actually runs.

## CI

CI is wired entirely to the shared
[`OpenVoiceOS/gh-automations`](https://github.com/OpenVoiceOS/gh-automations)
reusable workflows (referenced `@dev`):

| Workflow | Shared workflow |
|---|---|
| `build_tests.yml` | `build-tests.yml`, whole `tests/` tree, clean install, py3.10 to 3.13 |
| `e2e_tests.yml` | `build-tests.yml`, `tests/e2e/` with the `e2e` extra |
| `coverage.yml` | `coverage.yml` |
| `lint.yml` | `lint.yml` (ruff) |
| `license_tests.yml` | `license-check.yml` |
| `pip_audit.yml` | `pip-audit.yml` |
| `release_preview.yml` | `release-preview.yml` |
| `repo-health.yml` | `repo-health.yml` |
| `release_workflow.yml` | `publish-alpha.yml` (alpha + propose stable) |
| `publish_stable.yml` | `publish-stable.yml` |

Version policy is in `pyproject.toml`, never in CI. Prerelease floors are pinned
as minimum versions (`pkg>=X.Ya1`), so no `--pre` or `pre_install_pip` is needed.

---
[← Deployment](deployment.md) · [Home](index.md) · [Troubleshooting →](troubleshooting.md)
