"""Unit tests for the stt_transport / tts_transport config switch.

Unlike tests/e2e/test_relay_e2e.py (a real HiveMessageBusClient over a real
loopback hivemind-core), these tests stub the bus client directly to assert,
in isolation, which wire contract HiveMindSTT / HMPlayback pick for each
transport setting. The default (no config) must reproduce the exact b64
behaviour that shipped before this option existed.
"""
from unittest.mock import MagicMock, patch

from ovos_bus_client.message import Message
from speech_recognition import AudioData

from hivemind_bus_client.message import HiveMessage, HiveMessageType
from hivemind_bus_client.serialization import HiveMindBinaryPayloadType


def _make_audio() -> AudioData:
    frame_data = b"\x00\x00" * 1600  # 100 ms of 16 kHz mono 16-bit silence
    return AudioData(frame_data, sample_rate=16000, sample_width=2)


def _config(**kwargs):
    """Patch target for Configuration().get(...) used by service.py."""
    return patch("hivemind_voice_relay.service.Configuration",
                return_value=MagicMock(get=lambda k, default=None: kwargs.get(k, default)))


# ---------------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------------

def test_stt_default_config_uses_b64_transport():
    from hivemind_voice_relay.service import HiveMindSTT

    with _config():
        bus = MagicMock()
        stt = HiveMindSTT(bus)
        assert stt.transport == "b64"

        def fake_emit(*args, **kwargs):
            stt._transcripts = [["hello world", 0.9]]
            stt._response.set()

        bus.emit.side_effect = fake_emit
        result = stt.execute(_make_audio(), language="en-US")

    assert result == "hello world"
    assert bus.emit.call_count == 1
    sent = bus.emit.call_args.args[0]
    assert isinstance(sent, Message)
    assert sent.msg_type == "recognizer_loop:b64_transcribe"
    assert "audio" in sent.data
    # b64-encoded WAV, not raw PCM
    assert sent.data["audio"] != _make_audio().frame_data


def test_stt_binary_transport_sends_stt_audio_transcribe_frame():
    from hivemind_voice_relay.service import HiveMindSTT

    with _config(stt_transport="binary"):
        bus = MagicMock()
        stt = HiveMindSTT(bus)
        assert stt.transport == "binary"

        audio = _make_audio()

        def fake_emit(*args, **kwargs):
            stt._transcripts = [["turn on the lights", 0.95]]
            stt._response.set()

        bus.emit.side_effect = fake_emit
        result = stt.execute(audio, language="en-US")

    assert result == "turn on the lights"
    assert bus.emit.call_count == 1
    call = bus.emit.call_args
    sent: HiveMessage = call.args[0]
    assert isinstance(sent, HiveMessage)
    assert sent.msg_type == HiveMessageType.BINARY
    assert sent.bin_type == HiveMindBinaryPayloadType.STT_AUDIO_TRANSCRIBE
    assert sent.payload == audio.frame_data  # raw PCM, not a WAV container
    assert sent.metadata["lang"] == "en-US"
    assert sent.metadata["sample_rate"] == audio.sample_rate
    assert sent.metadata["sample_width"] == audio.sample_width
    assert call.kwargs["binary_type"] == HiveMindBinaryPayloadType.STT_AUDIO_TRANSCRIBE

    # the binary-transport response arrives on recognizer_loop:transcribe.response,
    # NOT the b64 event name
    bus.on_mycroft.assert_any_call("recognizer_loop:transcribe.response",
                                   stt.handle_transcripts)


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

def _make_playback(bus, **config):
    from hivemind_voice_relay.service import HMPlayback
    with _config(**config):
        with patch.object(HMPlayback, "start", lambda self: None), \
             patch("hivemind_voice_relay.service.PlaybackService.__init__", return_value=None):
            playback = HMPlayback.__new__(HMPlayback)
            playback.bus = bus
            from hivemind_voice_relay.service import get_tts_transport, TTSTransformersService
            playback.transport = get_tts_transport()
            playback.tts_transformers = TTSTransformersService(config={})
            bus.on("speak:b64_audio.response", playback.handle_tts_b64_response)
            if playback.transport == "binary":
                from hivemind_voice_relay.service import HMPlaybackBinaryCallbacks
                bus.bin_callbacks = HMPlaybackBinaryCallbacks(playback)
            return playback


def test_tts_default_config_requests_b64_audio():
    bus = MagicMock()
    playback = _make_playback(bus)
    assert playback.transport == "b64"

    m = Message("speak", {"utterance": "hi"}).forward("speak", {"utterance": "hi"})
    playback.execute_tts("hi", ident="1", listen=False, message=m)

    assert bus.emit.call_count == 1
    sent = bus.emit.call_args.args[0]
    assert sent.msg_type == "speak:b64_audio"


def test_tts_binary_transport_requests_synth_and_handles_binary_response(tmp_path):
    bus = MagicMock()
    playback = _make_playback(bus, tts_transport="binary")
    assert playback.transport == "binary"

    m = Message("speak", {"utterance": "hi"}).forward("speak", {"utterance": "hi"})
    playback.execute_tts("hi", ident="1", listen=False, message=m)

    assert bus.emit.call_count == 1
    sent = bus.emit.call_args.args[0]
    assert sent.msg_type == "speak:synth"

    # a TTS_AUDIO binary payload was wired up as the receive callback
    assert bus.bin_callbacks is not None

    with patch("builtins.open", create=True) as mock_open:
        from unittest.mock import mock_open as _mo
        mock_open.side_effect = _mo()
        with patch.object(playback, "_queue_for_playback") as queue_mock:
            bus.bin_callbacks.handle_receive_tts(b"RIFFfakewavdata", "hi", "en-US", "abc.wav")
            assert queue_mock.call_count == 1
            args = queue_mock.call_args.args
            assert args[0] == "/tmp/abc.wav"
            assert args[1] == "hi"
