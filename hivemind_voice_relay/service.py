import pybase64
import threading
from typing import List, Tuple, Optional

import speech_recognition as sr
from ovos_audio.service import PlaybackService
from ovos_bus_client.message import Message, dig_for_message
from ovos_config import Configuration
from ovos_plugin_manager.microphone import OVOSMicrophoneFactory
from ovos_plugin_manager.templates.stt import STT
from ovos_plugin_manager.transformer_services import (AudioTransformersService,
                                                      TTSTransformersService,
                                                      UtteranceTransformersService)
from ovos_plugin_manager.templates.tts import TTS
from ovos_plugin_manager.utils.tts_cache import hash_sentence
from ovos_plugin_manager.vad import OVOSVADFactory
from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
from ovos_simple_listener import ListenerCallbacks, SimpleListener
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG
from speech_recognition import AudioData

from hivemind_bus_client.client import BinaryDataCallbacks, HiveMessageBusClient
from hivemind_bus_client.identity import NodeIdentity
from hivemind_bus_client.message import HiveMessage, HiveMessageType
from hivemind_bus_client.serialization import HiveMindBinaryPayloadType


def get_stt_transport() -> str:
    """Which transport HiveMindSTT uses to hand a full utterance off for STT.

    Read from this device's ``mycroft.conf`` as top-level ``stt_transport``.
    ``"b64"`` (default) sends base64-encoded WAV over ``recognizer_loop:b64_transcribe``,
    unchanged from every prior release. ``"binary"`` opts into sending raw PCM
    as a ``STT_AUDIO_TRANSCRIBE`` binary HiveMessage instead, avoiding the
    base64 blow-up and the extra bus round-trip through JSON. Any other value
    falls back to ``"b64"``.
    """
    transport = Configuration().get("stt_transport", "b64")
    return transport if transport == "binary" else "b64"


def get_tts_transport() -> str:
    """Which transport HMPlayback uses to request synthesized TTS audio.

    Read from this device's ``mycroft.conf`` as top-level ``tts_transport``.
    ``"b64"`` (default) requests ``speak:b64_audio`` and gets base64-encoded
    WAV back, unchanged from every prior release. ``"binary"`` opts into
    ``speak:synth`` and receives the WAV as a ``TTS_AUDIO`` binary HiveMessage
    instead. Any other value falls back to ``"b64"``.
    """
    transport = Configuration().get("tts_transport", "b64")
    return transport if transport == "binary" else "b64"


def get_bus(bin_callbacks: Optional[BinaryDataCallbacks] = None) -> HiveMessageBusClient:
    # TODO - kwargs
    identity = NodeIdentity()
    siteid = identity.site_id or "unknown"
    host = identity.default_master
    port = 5678

    if not identity.access_key or not identity.password or not host:
        raise RuntimeError("NodeIdentity not set, please pass key/password/host or "
                           "call 'hivemind-client set-identity'")

    if not host.startswith("ws://") and not host.startswith("wss://"):
        host = "ws://" + host
    if not host.startswith("ws"):
        raise ValueError(f"Invalid host, please specify a protocol: 'ws://{host}' or 'wss://{host}'")

    kwargs = {}
    if bin_callbacks is not None:
        kwargs["bin_callbacks"] = bin_callbacks
    bus = HiveMessageBusClient(key=identity.access_key,
                               password=identity.password,
                               port=port,
                               host=host,
                               useragent="VoiceRelayV1.0.0",
                               internal_bus=FakeBus(),
                               **kwargs)
    bus.connect(site_id=siteid)
    return bus


def on_ready():
    LOG.info('HiveMind Voice Relay is ready.')


def on_started():
    LOG.info('HiveMind Voice Relay started.')


def on_alive():
    LOG.info('HiveMind Voice Relay alive.')


def on_stopping():
    LOG.info('HiveMind Voice Relay is shutting down...')


def on_error(e='Unknown'):
    LOG.error(f'HiveMind Voice Relay failed to launch ({e}).')


class HMCallbacks(ListenerCallbacks):
    def __init__(self, bus: Optional[HiveMessageBusClient] = None):
        self.bus = bus or get_bus()
        # client-side utterance transformers, opt-in via this device's
        # mycroft.conf. NOTE: if the hivemind server (or the OVOS agent
        # behind it) enables the same plugin, text is processed twice —
        # enable each plugin on exactly one side.
        self.utterance_transformers = UtteranceTransformersService(
            config=Configuration().get("utterance_transformers") or {})

    def listen_callback(self):
        LOG.info("New loop state: IN_COMMAND")
        self.bus.internal_bus.emit(Message("mycroft.audio.play_sound",
                                           {"uri": "snd/start_listening.wav"}))
        self.bus.internal_bus.emit(Message("recognizer_loop:wakeword"))
        self.bus.internal_bus.emit(Message("recognizer_loop:record_begin"))

    def end_listen_callback(self):
        LOG.info("New loop state: WAITING_WAKEWORD")
        self.bus.internal_bus.emit(Message("recognizer_loop:record_end"))

    def error_callback(self, audio: sr.AudioData):
        LOG.error("STT Failure")
        self.bus.internal_bus.emit(Message("recognizer_loop:speech.recognition.unknown"))

    def text_callback(self, utterance: str, lang: str):
        LOG.info(f"STT: {utterance}")
        utterances = [utterance]
        context = {}
        if self.utterance_transformers.plugins:
            utterances, context = self.utterance_transformers.transform(
                utterances, {"lang": lang})
            if context.get("canceled"):
                LOG.info(f"utterance canceled by {context.get('cancel_by')}: "
                         f"{context.get('cancel_reason')}")
                self.bus.internal_bus.emit(Message("ovos.utterance.cancelled"))
                return
        self.bus.emit(Message("recognizer_loop:utterance",
                              {"utterances": utterances, "lang": lang},
                              context))


class HiveMindSTT(STT):
    def __init__(self, bus: HiveMessageBusClient, config=None):
        super().__init__(config)
        self.bus = bus
        self.transport = get_stt_transport()
        self._response = threading.Event()
        self._transcripts: List[Tuple[str, float]] = []
        # client-side audio transformers applied before audio is sent to the
        # server for STT; opt-in via this device's mycroft.conf
        self.audio_transformers = AudioTransformersService(
            config=Configuration().get("audio_transformers") or {})
        self.bus.on_mycroft("recognizer_loop:b64_transcribe.response",
                            self.handle_transcripts)
        self.bus.on_mycroft("recognizer_loop:transcribe.response",
                            self.handle_transcripts)

    def handle_transcripts(self, message: Message):
        self._transcripts = message.data["transcriptions"]
        self._response.set()

    def execute(self, audio: AudioData, language: Optional[str] = None) -> str:
        if self.audio_transformers.plugins:
            chunk, _ = self.audio_transformers.transform(audio.frame_data)
            audio = AudioData(chunk, audio.sample_rate, audio.sample_width)
        self._response.clear()
        self._transcripts = []
        if self.transport == "binary":
            hm = HiveMessage(HiveMessageType.BINARY,
                             payload=audio.frame_data,
                             bin_type=HiveMindBinaryPayloadType.STT_AUDIO_TRANSCRIBE,
                             metadata={"lang": self.lang,
                                       "sample_rate": audio.sample_rate,
                                       "sample_width": audio.sample_width})
            self.bus.emit(hm, binary_type=HiveMindBinaryPayloadType.STT_AUDIO_TRANSCRIBE)
        else:
            wav = audio.get_wav_data()
            b64audio = pybase64.b64encode(wav).decode("utf-8")
            m = dig_for_message() or Message("")
            m = m.forward("recognizer_loop:b64_transcribe",
                          {"audio": b64audio, "lang": self.lang})
            self.bus.emit(m)
        self._response.wait(20)
        if self._response.is_set():
            if not self._transcripts:
                LOG.error("Empty STT")
                return ""
            return self._transcripts[0][0]
        else:
            LOG.error("Timeout waiting for STT transcriptions")
            return ""


class HMPlaybackBinaryCallbacks(BinaryDataCallbacks):
    """Routes binary TTS_AUDIO HiveMessages back into HMPlayback.

    ``HiveMessageBusClient`` only dispatches binary payloads to callbacks
    handed to it at construction time (see ``get_bus``), so this is a thin
    adapter forwarding into the owning ``HMPlayback`` instance.
    """

    def __init__(self, playback: "HMPlayback"):
        self.playback = playback

    def handle_receive_tts(self, bin_data: bytes, utterance: str, lang: str, file_name: str):
        self.playback.handle_tts_binary_response(bin_data, utterance, lang, file_name)


class HMPlayback(PlaybackService):
    def __init__(self, bus: HiveMessageBusClient, ready_hook=on_ready, error_hook=on_error,
                 stopping_hook=on_stopping, alive_hook=on_alive,
                 started_hook=on_started, watchdog=lambda: None):
        super().__init__(ready_hook, error_hook, stopping_hook, alive_hook, started_hook, watchdog=watchdog,
                         bus=bus, validate_source=False,
                         disable_fallback=True)
        self.transport = get_tts_transport()
        # client-side tts transformers applied to received TTS audio before
        # playback; opt-in via this device's mycroft.conf
        self.tts_transformers = TTSTransformersService(
            config=Configuration().get("tts_transformers") or {})
        self.bus.on("speak:b64_audio.response", self.handle_tts_b64_response)
        if self.transport == "binary":
            self.bus.bin_callbacks = HMPlaybackBinaryCallbacks(self)
        self.start()

    def execute_tts(self, utterance, ident, listen=False,
                    message: Message = None):
        """Mute mic and start speaking the utterance using selected tts backend.

        Args:
            utterance:  The sentence to be spoken
            ident:      Ident tying the utterance to the source query
            listen:     True if a user response is expected
        """
        LOG.info("Speak: " + utterance)
        # request synth in HM master side
        target = "speak:synth" if self.transport == "binary" else "speak:b64_audio"
        self.bus.emit(message.forward(target,
                                      {"utterance": utterance, "listen": listen}))

    def handle_tts_b64_response(self, message: Message):
        LOG.debug("Received TTS audio")
        b64data = message.data["audio"]
        listen = message.data.get("listen", False)
        utt = message.data["utterance"]
        tts_id = message.data.get("tts_id", "b64TTS")
        audio_file = f"/tmp/{hash_sentence(utt)}.wav"
        with open(audio_file, "wb") as f:
            f.write(pybase64.b64decode(b64data))
        self._queue_for_playback(audio_file, utt, listen, tts_id, message)

    def handle_tts_binary_response(self, bin_data: bytes, utterance: str, lang: str, file_name: str):
        LOG.debug("Received binary TTS audio")
        audio_file = f"/tmp/{file_name}" if file_name else f"/tmp/{hash_sentence(utterance)}.wav"
        with open(audio_file, "wb") as f:
            f.write(bin_data)
        message = dig_for_message() or Message("speak:synth", {"utterance": utterance, "lang": lang})
        self._queue_for_playback(audio_file, utterance, message.data.get("listen", False),
                                 "binaryTTS", message)

    def _queue_for_playback(self, audio_file, utterance, listen, tts_id, message):
        if self.tts_transformers.plugins:
            audio_file, _ = self.tts_transformers.transform(
                audio_file, {"lang": message.data.get("lang")})

        # queue audio for playback
        TTS.queue.put(
            (audio_file, None, listen, tts_id, message)
        )

    def handle_b64_audio(self, message):
        # HACK: dont get in a infinite loop, this message is meant for master
        # because of how HiveMindTTS is implemented we need to do this
        pass


class HiveMindVoiceRelay(SimpleListener):
    def __init__(self, bus: Optional[HiveMessageBusClient] = None):
        self.bus = bus or get_bus()
        self.audio = HMPlayback(bus=self.bus)
        ww = Configuration().get("listener", {}).get("wake_word", "hey_mycroft")
        super().__init__(
            mic=OVOSMicrophoneFactory.create(),
            vad=OVOSVADFactory.create(),
            wakeword=OVOSWakeWordFactory.create_hotword(ww),
            stt=HiveMindSTT(self.bus),
            callbacks=HMCallbacks(self.bus)
        )


def main():
    t = HiveMindVoiceRelay()
    t.run()


if __name__ == "__main__":
    main()
