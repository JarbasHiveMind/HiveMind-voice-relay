"""End-to-end tests driving the *real* HiveMind-voice-relay client.

Unlike ``test_bridge1_conformance.py`` / ``test_acl.py`` (which exercise the
generic hivescope satellite shim), this suite wires the relay's own
``HiveMindSTT`` / ``HMCallbacks`` / ``HMPlayback`` classes over a **real**
``HiveMessageBusClient`` connected to a **real** ``hivemind-core`` master that
the hivescope harness runs in-process with a real WebSocket server
(``use_loopback=True``).

What is real
------------
* ``hivemind-core`` ``HiveMindListenerProtocol`` (handshake, crypto, ACL,
  client DB) running on a loopback WebSocket server.
* The relay's ``HiveMessageBusClient`` connecting over that socket.
* The relay's ``HiveMindSTT`` (b64 STT request/response) and the b64 TTS
  request/response path used by ``HMPlayback``.

What is mocked (no real devices / no real network out)
------------------------------------------------------
* **Mic / VAD / wakeword / audio capture** — the relay never opens a real
  microphone; ``HiveMindVoiceRelay`` is built with stub plugin factories and
  audio is fed in as a pre-built ``AudioData`` buffer.
* **Remote STT / TTS endpoints** — in production the
  ``hivemind-audio-binary-protocol`` plugin on the server answers
  ``recognizer_loop:b64_transcribe`` / ``speak:b64_audio``.  Here a tiny stub
  handler on the master's agent bus plays that role, so no real STT/TTS engine
  or model is loaded.
* **TTS playback queue** — ``HMPlayback`` is built without starting the OVOS
  audio service; we assert on the queued playback item instead of touching an
  audio device.
"""

import time
from unittest.mock import MagicMock, patch

import pybase64
from ovos_bus_client.message import Message
from speech_recognition import AudioData

from hivemind_bus_client.client import HiveMessageBusClient
from hivemind_bus_client.identity import NodeIdentity

from hivescope import TopologyBuilder


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _wait_for(condition, timeout: float = 5.0, interval: float = 0.02) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return False


def _make_audio() -> AudioData:
    """A short silent PCM buffer — stands in for captured mic audio."""
    frame_data = b"\x00\x00" * 1600  # 100 ms of 16 kHz mono 16-bit silence
    return AudioData(frame_data, sample_rate=16000, sample_width=2)


def _make_relay_bus(url: str, key: str, password: str,
                    name: str = "voice-relay") -> HiveMessageBusClient:
    """Build the relay's real bus client pointed at the loopback master."""
    host, port = url.replace("ws://", "").rstrip("/").split(":")
    port = int(port)
    identity = NodeIdentity()
    identity.access_key = key
    identity.password = password
    identity.default_master = f"ws://{host}"
    identity.default_port = port
    identity.name = name
    identity.site_id = f"{name}-site"
    return HiveMessageBusClient(
        key=key, password=password,
        host=f"ws://{host}", port=port,
        useragent="VoiceRelayV1.0.0", self_signed=False,
        identity=identity,
    )


def _loopback_master():
    """Single loopback master with the relay's message types whitelisted."""
    b = TopologyBuilder()
    m = b.add_master("M0", use_loopback=True)
    m.register_satellite(
        "relay-key", password="relay-pwd",
        allowed_types=[
            "recognizer_loop:utterance",
            "recognizer_loop:b64_transcribe",
            "speak:b64_audio",
        ],
    )
    return b, m


def _install_stub_stt_endpoint(master, transcript: str = "what is the weather"):
    """Mock the server-side STT plugin: answer b64_transcribe on the agent bus.

    Mirrors what hivemind-audio-binary-protocol does, minus a real STT engine.
    The response is addressed back to the originating relay peer so the
    HiveMindListenerProtocol routes it down the socket.
    """
    seen = []

    def handler(message: Message):
        seen.append(message)
        peer = message.context.get("source")
        resp = message.reply(
            "recognizer_loop:b64_transcribe.response",
            {"transcriptions": [[transcript, 0.97]]},
        )
        # route back to the satellite that asked
        resp.context["destination"] = peer
        master.agent_protocol.bus.emit(resp)

    master.agent_protocol.bus.on("recognizer_loop:b64_transcribe", handler)
    return seen


def _install_stub_tts_endpoint(master, wav_bytes: bytes = b"RIFFfakewavdata"):
    """Mock the server-side TTS plugin: answer speak:b64_audio on the agent bus."""
    seen = []

    def handler(message: Message):
        seen.append(message)
        peer = message.context.get("source")
        utt = message.data.get("utterance", "")
        resp = message.reply(
            "speak:b64_audio.response",
            {
                "audio": pybase64.b64encode(wav_bytes).decode("utf-8"),
                "utterance": utt,
                "listen": message.data.get("listen", False),
                "tts_id": "stubTTS",
            },
        )
        resp.context["destination"] = peer
        master.agent_protocol.bus.emit(resp)

    master.agent_protocol.bus.on("speak:b64_audio", handler)
    return seen


# ---------------------------------------------------------------------------
# STT path — real HiveMindSTT over the wire
# ---------------------------------------------------------------------------

def test_hivemind_stt_round_trips_b64_transcribe():
    """HiveMindSTT.execute() sends b64 audio to the master and returns the
    transcript the (stubbed) server-side STT plugin sends back."""
    from hivemind_voice_relay.service import HiveMindSTT

    b, m = _loopback_master()
    b.start_all()
    bus = None
    try:
        requests = _install_stub_stt_endpoint(m, transcript="turn on the lights")

        bus = _make_relay_bus(m.network_protocol.url, "relay-key", "relay-pwd")
        bus.connect(site_id="relay-site")
        bus.wait_for_handshake(timeout=10)

        stt = HiveMindSTT(bus)
        result = stt.execute(_make_audio(), language="en-US")

        assert _wait_for(lambda: len(requests) >= 1), \
            "b64_transcribe never reached the master agent bus"
        # the relay actually sent base64-encoded WAV audio
        assert requests[0].data.get("audio"), "no b64 audio in transcribe request"
        assert result == "turn on the lights"
    finally:
        if bus is not None:
            bus.close()
        b.stop_all()


def test_hivemind_stt_timeout_returns_empty():
    """With no server-side STT plugin answering, HiveMindSTT.execute() times out
    and returns an empty string rather than hanging."""
    from hivemind_voice_relay.service import HiveMindSTT

    b, m = _loopback_master()
    b.start_all()
    bus = None
    try:
        bus = _make_relay_bus(m.network_protocol.url, "relay-key", "relay-pwd")
        bus.connect(site_id="relay-site")
        bus.wait_for_handshake(timeout=10)

        stt = HiveMindSTT(bus)
        # shorten the wait so the test stays fast
        with patch.object(stt._response, "wait", return_value=False):
            result = stt.execute(_make_audio(), language="en-US")
        assert result == ""
    finally:
        if bus is not None:
            bus.close()
        b.stop_all()


# ---------------------------------------------------------------------------
# Utterance injection — real HMCallbacks over the wire
# ---------------------------------------------------------------------------

def test_callbacks_text_callback_injects_utterance():
    """HMCallbacks.text_callback emits recognizer_loop:utterance and it reaches
    the master's agent bus (the wakeword→STT→inject hop)."""
    from hivemind_voice_relay.service import HMCallbacks

    b, m = _loopback_master()
    b.start_all()
    bus = None
    try:
        bus = _make_relay_bus(m.network_protocol.url, "relay-key", "relay-pwd")
        bus.connect(site_id="relay-site")
        bus.wait_for_handshake(timeout=10)

        seen = []
        m.agent_protocol.bus.on("recognizer_loop:utterance", seen.append)

        cb = HMCallbacks(bus)
        cb.text_callback("hello hive", "en-US")

        assert _wait_for(lambda: len(seen) >= 1), \
            "utterance never reached the master agent bus"
        assert seen[0].data["utterances"] == ["hello hive"]
        assert seen[0].data["lang"] == "en-US"
    finally:
        if bus is not None:
            bus.close()
        b.stop_all()


# ---------------------------------------------------------------------------
# TTS path — real b64 TTS request + playback queueing
# ---------------------------------------------------------------------------

def _build_playback(bus):
    """Construct HMPlayback without starting the OVOS audio service.

    We patch PlaybackService.__init__/start so no audio backend or thread is
    spun up; HMPlayback's own bus handler registration still runs.
    """
    from hivemind_voice_relay.service import HMPlayback
    from ovos_audio.service import PlaybackService

    def _fake_init(self, *a, **kw):
        # HMPlayback.__init__ references self.bus right after super().__init__;
        # set it the way the real PlaybackService would, without spinning up the
        # audio backend / playback thread.
        self.bus = kw.get("bus") or (a[6] if len(a) > 6 else None)

    with patch.object(PlaybackService, "__init__", _fake_init), \
         patch.object(HMPlayback, "start", lambda self: None):
        pb = HMPlayback(bus=bus)
    return pb


def test_tts_request_and_playback_queue():
    """execute_tts emits speak:b64_audio to the master; the stubbed server-side
    TTS plugin answers speak:b64_audio.response and HMPlayback queues the audio
    for local playback."""
    from queue import Queue
    from ovos_plugin_manager.templates.tts import TTS

    b, m = _loopback_master()
    b.start_all()
    bus = None
    saved_queue = TTS.queue
    try:
        # the playback queue is normally created when a real TTS is loaded; the
        # relay's HMPlayback only ever *puts* on it, so a plain Queue suffices.
        TTS.queue = Queue()

        requests = _install_stub_tts_endpoint(m, wav_bytes=b"RIFF....WAVEdata")

        bus = _make_relay_bus(m.network_protocol.url, "relay-key", "relay-pwd")
        bus.connect(site_id="relay-site")
        bus.wait_for_handshake(timeout=10)

        pb = _build_playback(bus)
        # re-register the response handler on the live bus (PlaybackService
        # __init__ was patched out, so do what it would have done)
        bus.on("speak:b64_audio.response", pb.handle_tts_b64_response)

        msg = Message("speak", {"utterance": "the light is on", "listen": False})
        pb.execute_tts("the light is on", ident="abc", listen=False, message=msg)

        assert _wait_for(lambda: len(requests) >= 1), \
            "speak:b64_audio never reached the master agent bus"
        assert requests[0].data["utterance"] == "the light is on"

        assert _wait_for(lambda: not TTS.queue.empty(), timeout=5), \
            "TTS audio was never queued for local playback"
        item = TTS.queue.get_nowait()
        # (audio_file, _, listen, tts_id, message)
        assert item[0].endswith(".wav")
        assert item[3] == "stubTTS"
    finally:
        TTS.queue = saved_queue
        if bus is not None:
            bus.close()
        b.stop_all()


# ---------------------------------------------------------------------------
# Full relay assembly — mic/VAD/wakeword mocked, bus + STT real
# ---------------------------------------------------------------------------

def test_relay_assembles_with_mocked_capture():
    """HiveMindVoiceRelay builds end-to-end with mocked mic/VAD/wakeword and a
    real bus, wiring a real HiveMindSTT — no real audio device is opened."""
    import hivemind_voice_relay.service as svc

    b, m = _loopback_master()
    b.start_all()
    bus = None
    try:
        bus = _make_relay_bus(m.network_protocol.url, "relay-key", "relay-pwd")
        bus.connect(site_id="relay-site")
        bus.wait_for_handshake(timeout=10)

        with patch.object(svc.OVOSMicrophoneFactory, "create", return_value=MagicMock()), \
             patch.object(svc.OVOSVADFactory, "create", return_value=MagicMock()), \
             patch.object(svc.OVOSWakeWordFactory, "create_hotword", return_value=MagicMock()), \
             patch.object(svc, "HMPlayback", return_value=MagicMock()):
            relay = svc.HiveMindVoiceRelay(bus=bus)

        assert isinstance(relay.stt, svc.HiveMindSTT)
        assert relay.stt.bus is bus
        assert relay.bus is bus
        # never opened a real microphone / wakeword engine
        assert relay.mic is not None
        assert relay.wakeword is not None
    finally:
        if bus is not None:
            bus.close()
        b.stop_all()
