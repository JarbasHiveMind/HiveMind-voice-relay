import base64
import threading
from typing import List, Tuple, Optional

import speech_recognition as sr
from ovos_audio.service import PlaybackService
from ovos_bus_client.message import Message, dig_for_message
from ovos_config import Configuration
from ovos_plugin_manager.microphone import OVOSMicrophoneFactory
from ovos_plugin_manager.templates.stt import STT
from ovos_plugin_manager.templates.tts import TTS
from ovos_plugin_manager.utils.tts_cache import hash_sentence
from ovos_plugin_manager.vad import OVOSVADFactory
from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
from ovos_simple_listener import ListenerCallbacks, SimpleListener
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG
from speech_recognition import AudioData

from hivemind_bus_client.client import HiveMessageBusClient
from hivemind_bus_client.identity import NodeIdentity


def get_bus() -> HiveMessageBusClient:
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

    bus = HiveMessageBusClient(key=identity.access_key,
                               password=identity.password,
                               port=port,
                               host=host,
                               useragent="VoiceRelayV1.0.0",
                               internal_bus=FakeBus())
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
        self.bus.emit(Message("recognizer_loop:utterance",
                              {"utterances": [utterance], "lang": lang}))


class HiveMindSTT(STT):
    def __init__(self, bus: HiveMessageBusClient, config=None):
        super().__init__(config)
        self.bus = bus
        self._response = threading.Event()
        self._transcripts: List[Tuple[str, float]] = []
        self.bus.on_mycroft("recognizer_loop:b64_transcribe.response",
                            self.handle_transcripts)

    def handle_transcripts(self, message: Message):
        self._transcripts = message.data["transcriptions"]
        self._response.set()

    def execute(self, audio: AudioData, language: Optional[str] = None) -> str:
        wav = audio.get_wav_data()
        b64audio = base64.b64encode(wav).decode("utf-8")
        m = dig_for_message() or Message("")
        m = m.forward("recognizer_loop:b64_transcribe",
                      {"audio": b64audio, "lang": self.lang})
        self._response.clear()
        self._transcripts = []
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


class HMPlayback(PlaybackService):
    def __init__(self, bus: HiveMessageBusClient, ready_hook=on_ready, error_hook=on_error,
                 stopping_hook=on_stopping, alive_hook=on_alive,
                 started_hook=on_started, watchdog=lambda: None):
        super().__init__(ready_hook, error_hook, stopping_hook, alive_hook, started_hook, watchdog=watchdog,
                         bus=bus, validate_source=False,
                         disable_fallback=True)
        self.bus.on("speak:b64_audio.response", self.handle_tts_b64_response)
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
        self.bus.emit(message.forward('speak:b64_audio',
                                      {"utterance": utterance, "listen": listen}))

    def handle_tts_b64_response(self, message: Message):
        LOG.debug("Received TTS audio")
        b64data = message.data["audio"]
        listen = message.data.get("listen", False)
        utt = message.data["utterance"]
        tts_id = message.data.get("tts_id", "b64TTS")
        audio_file = f"/tmp/{hash_sentence(utt)}.wav"
        with open(audio_file, "wb") as f:
            f.write(base64.b64decode(b64data))

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
