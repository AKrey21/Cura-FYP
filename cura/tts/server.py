# PROVENANCE: LIBRARY - wraps Coqui TTS (Tacotron2); original glue is the
# character map and length capping. Third-party: coqui-tts, torch. See PROVENANCE.md.
"""Stretch TTS: server-side synthesis (Coqui TTS) to a WAV file.

Optional extra - install with `pip install -e ".[tts]"` (heavy: pulls torch).
Adopt over the Web Speech baseline only if it wins the MOS-style listening
test / intelligibility check described in cura/eval/datasets/README.md.

Consumes the same sentence-level CURA_BRIEFING segments as the baseline, so
the transcript-sync model in the UI is unchanged whichever engine narrates.
"""

from __future__ import annotations

from cura.contracts import Briefing

# Coqui's character vocabulary is ASCII-ish: typographic punctuation and
# accented letters get silently discarded (fusing or mangling the words
# around them - "Zócalo" → "Zcalo") unless mapped first.
_CHAR_MAP = str.maketrans({"—": ", ", "–": ", ", "…": "...", "|": ", ",
                           "/": ", ", "“": '"', "”": '"', "‘": "'", "’": "'",
                           "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a",
                           "é": "e", "è": "e", "ê": "e", "ë": "e",
                           "í": "i", "ì": "i", "î": "i", "ï": "i",
                           "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o",
                           "ú": "u", "ù": "u", "û": "u", "ü": "u",
                           "ñ": "n", "ç": "c", "ø": "o", "å": "a", "æ": "ae",
                           "Á": "A", "À": "A", "Â": "A", "Ä": "A", "Ã": "A",
                           "É": "E", "È": "E", "Ê": "E", "Ë": "E",
                           "Í": "I", "Ì": "I", "Î": "I", "Ï": "I",
                           "Ó": "O", "Ò": "O", "Ô": "O", "Ö": "O", "Õ": "O",
                           "Ú": "U", "Ù": "U", "Û": "U", "Ü": "U",
                           "Ñ": "N", "Ç": "C", "Ø": "O", "Å": "A"})
# Tacotron2 synthesis time scales with input length, and a runaway "sentence"
# (un-punctuated boilerplate) can stall an edition build for minutes.
_MAX_CHARS = 600


class CoquiTTS:
    name = "coqui"

    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        try:
            from TTS.api import TTS  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                'CoquiTTS needs the optional extra: pip install -e ".[tts]"') from exc
        self.model_name = model_name
        self._tts = TTS(model_name)

    def synthesize(self, briefing: Briefing, out_path: str) -> str:
        """Narrate the briefing transcript into a single WAV at `out_path`."""
        text = " ".join(seg.text for seg in briefing.segments)
        self._tts.tts_to_file(text=text.translate(_CHAR_MAP), file_path=out_path)
        return out_path

    def synthesize_text(self, text: str, out_path: str) -> str:
        """One sentence to one WAV (listening test + Listen narration)."""
        text = text.translate(_CHAR_MAP)
        if len(text) > _MAX_CHARS:
            cut = text[:_MAX_CHARS]
            text = cut[: max(cut.rfind(" "), 1)] + "."
        self._tts.tts_to_file(text=text, file_path=out_path)
        return out_path
