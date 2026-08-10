"""Abstraction de la synthese vocale (TTS) : cloud ou local, meme interface.

Chaque provider expose `synthetiser(texte)` qui renvoie (audio_int16, frequence)
ou None. jarvis14 se charge de JOUER l'audio (avec sa gestion d'interruption) et
retombe sur la voix Windows (SAPI) si le provider renvoie None.

  - ElevenLabsProvider : cloud (qualite max), voix configurable.
  - PiperProvider      : local, 100% offline, voix francaise Piper (.onnx).

Choix par config.yaml :
  - cloud -> ElevenLabs
  - local -> Piper/Kokoro selon voix_locale
  - nvidia -> Piper/Kokoro selon voix_locale

Le mode NVIDIA concerne uniquement le LLM : il ne doit pas forcer un TTS cloud.
Cela permet d'utiliser NVIDIA gratuitement pour le cerveau et Piper localement
pour la voix, sans cle ElevenLabs.
"""
import json
import logging
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from core.config import reglage

LOG = logging.getLogger("jarvis")
_RACINE = Path(__file__).resolve().parent.parent


class ProviderTTS:
    nom = "?"

    def disponible(self):
        return True

    def synthetiser(self, texte):
        return None


class ElevenLabsProvider(ProviderTTS):
    nom = "ElevenLabs"

    def __init__(self):
        self.cle = reglage("elevenlabs.cle", "")
        self.voix = reglage("elevenlabs.voix", "")
        self.modele = reglage("elevenlabs.modele", "eleven_flash_v2_5")
        self._voix_resolue = None

    def disponible(self):
        return bool(self.cle)

    def _resoudre_voix(self):
        if self.voix:
            return self.voix
        if self._voix_resolue:
            return self._voix_resolue
        try:
            requete = urllib.request.Request(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": self.cle})
            with urllib.request.urlopen(requete, timeout=6) as reponse:
                d = json.loads(reponse.read().decode("utf-8"))
            self._voix_resolue = d["voices"][0]["voice_id"]
        except Exception:
            self._voix_resolue = "21m00Tcm4TlvDq8ikWAM"
        return self._voix_resolue

    def synthetiser(self, texte):
        try:
            import miniaudio
            import numpy as np
        except ImportError:
            return None
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._resoudre_voix()}"
        charge = {"text": texte, "model_id": self.modele}
        if any(x in self.modele for x in ("flash", "turbo")):
            charge["language_code"] = reglage("elevenlabs.langue", "fr")
        corps = json.dumps(charge).encode("utf-8")
        requete = urllib.request.Request(url, data=corps, method="POST", headers={
            "xi-api-key": self.cle, "Content-Type": "application/json",
            "Accept": "audio/mpeg"})
        try:
            with urllib.request.urlopen(requete, timeout=15) as reponse:
                mp3 = reponse.read()
            decode = miniaudio.decode(
                mp3, nchannels=1, sample_rate=24000,
                output_format=miniaudio.SampleFormat.SIGNED16)
            return np.frombuffer(decode.samples, dtype=np.int16), 24000
        except Exception as e:
            print(f"  [ElevenLabs] indisponible ({e}), repli voix Windows.")
            return None


class PiperProvider(ProviderTTS):
    nom = "Piper"

    def __init__(self):
        self.modele = reglage("piper.modele", "")
        self._voix = None

    def _chemin(self):
        if not self.modele:
            trouves = list((_RACINE / "voix").glob("*.onnx"))
            return trouves[0] if trouves else None
        p = Path(self.modele)
        return p if p.is_absolute() else (_RACINE / p)

    def disponible(self):
        c = self._chemin()
        return bool(c and c.exists())

    def synthetiser(self, texte):
        try:
            import numpy as np
            from piper import PiperVoice
        except ImportError:
            print("  [Piper] librairie piper-tts absente.")
            return None
        chemin = self._chemin()
        if chemin is None or not chemin.exists():
            print("  [Piper] aucun modele de voix (.onnx) dans voix/. Voir docs.")
            return None
        try:
            if self._voix is None:
                self._voix = PiperVoice.load(str(chemin))
            brut = b"".join(self._voix.synthesize_stream_raw(texte))
            return np.frombuffer(brut, dtype=np.int16), self._voix.config.sample_rate
        except Exception as e:
            print(f"  [Piper] echec ({e}), repli voix Windows.")
            return None


class KokoroProvider(ProviderTTS):
    nom = "Kokoro"

    def __init__(self):
        self.modele = reglage("kokoro.modele", "")
        self.voix = reglage("kokoro.voix", "")
        self.voix_nom = reglage("kokoro.voix_nom", "ff_siwis")
        self._k = None

    def disponible(self):
        return bool(self.modele and Path(self.modele).exists())

    def synthetiser(self, texte):
        try:
            import numpy as np
            from kokoro_onnx import Kokoro
        except ImportError:
            print("  [Kokoro] librairie absente. Installe : uv add kokoro-onnx")
            return None
        if not (self.modele and Path(self.modele).exists()):
            print("  [Kokoro] modele introuvable (kokoro.modele). Voir docs/local.md.")
            return None
        try:
            if self._k is None:
                self._k = Kokoro(self.modele, self.voix)
            samples, freq = self._k.create(texte, voice=self.voix_nom, speed=1.0, lang="fr-fr")
            audio = (np.asarray(samples) * 32767).astype(np.int16)
            return audio, freq
        except Exception as e:
            print(f"  [Kokoro] echec ({e}), repli voix Windows.")
            return None


_TTS = None


def tts():
    """Provider TTS courant.

    Le mode NVIDIA choisit volontairement le meme TTS local que le mode local.
    Ainsi NVIDIA peut etre utilise avec Piper sans ElevenLabs et sans cout cloud.
    """
    global _TTS
    if _TTS is None:
        mode = (reglage("mode", "cloud") or "cloud").lower()
        if mode in ("local", "nvidia"):
            moteur = (reglage("voix_locale", "piper") or "piper").lower()
            _TTS = KokoroProvider() if moteur == "kokoro" else PiperProvider()
        else:
            _TTS = ElevenLabsProvider()
        LOG.info("provider TTS : %s (mode %s)", _TTS.nom, mode)
    return _TTS
