import base64
import threading
from typing import List, Tuple, Optional

from ovos_audio.service import PlaybackService
from ovos_bus_client.message import Message, dig_for_message
from ovos_config.locale import setup_locale
from ovos_dinkum_listener.plugins import FakeStreamingSTT
from ovos_dinkum_listener.service import OVOSDinkumVoiceService
from ovos_plugin_manager.templates.stt import STT
from ovos_plugin_manager.templates.tts import TTS
from ovos_plugin_manager.templates.vad import VADEngine
from ovos_plugin_manager.utils.tts_cache import hash_sentence
from ovos_utils.log import LOG
from speech_recognition import AudioData

from hivemind_bus_client.client import HiveMessageBusClient


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


class AudioPlaybackRelay(PlaybackService):

    def __init__(self, bus: HiveMessageBusClient, ready_hook=on_ready, error_hook=on_error,
                 stopping_hook=on_stopping, alive_hook=on_alive,
                 started_hook=on_started, watchdog=lambda: None):
        super().__init__(ready_hook, error_hook, stopping_hook, alive_hook, started_hook, watchdog=watchdog,
                         bus=bus, validate_source=False,
                         disable_fallback=True)
        self.bus.on("speak:b64_audio.response", self.handle_tts_b64_response)

    def execute_tts(self, utterance, ident, listen=False, message: Message = None):
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
        pass  # handled in master, not client

    def _maybe_reload_tts(self):
        # skip loading TTS in this subclass
        pass


class VoiceRelay(OVOSDinkumVoiceService):
    """HiveMind Voice Relay, but bus is replaced with hivemind connection"""

    def __init__(self, bus: HiveMessageBusClient, on_ready=on_ready, on_error=on_error,
                 on_stopping=on_stopping, on_alive=on_alive,
                 on_started=on_started, watchdog=lambda: None, mic=None,
                 vad: Optional[VADEngine] = None):
        setup_locale()  # read mycroft.conf for default lang/timezone in all modules (eg, lingua_franca)
        stt = FakeStreamingSTT(HiveMindSTT(bus=bus))
        super().__init__(on_ready, on_error, on_stopping, on_alive, on_started, watchdog, mic,
                         stt=stt, vad=vad,
                         bus=bus, validate_source=False, disable_fallback=True)

    def _handle_b64_transcribe(self, message: Message):
        pass  # handled in master, not client

    def _connect_to_bus(self):
        pass

    def reload_configuration(self):
        pass
