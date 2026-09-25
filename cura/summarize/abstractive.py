# PROVENANCE: LIBRARY - thin wrapper over the Hugging Face transformers
# summarization pipeline (BART/Pegasus). Original glue: the token-budget
# truncation. Third-party: transformers, torch. See PROVENANCE.md.
"""Stretch summariser: abstractive seq2seq (BART / Pegasus) via transformers.

Optional extra - install with `pip install -e ".[abstractive]"`. Adopt only if
it beats TextRank on ROUGE *and* the faithfulness check (cura/eval/summary.py);
abstractive models can hallucinate, which the faithfulness metric penalises.
"""

from __future__ import annotations

from cura.contracts import Summary
from cura.summarize.base import split_sentences


class AbstractiveSummarizer:
    name = "abstractive"

    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        try:
            from transformers import pipeline
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "AbstractiveSummarizer needs the optional extra: "
                'pip install -e ".[abstractive]"') from exc
        self.model_name = model_name
        self._pipe = pipeline("summarization", model=model_name)
        # Inputs past the encoder's position limit (1024 for BART) crash it,
        # and the tokenizer often reports no usable max length, so derive the
        # cap from the model config; margin for special tokens.
        config_max = getattr(self._pipe.model.config,
                             "max_position_embeddings", 1024)
        self._max_input_tokens = max(64, config_max - 24)

    def _truncate(self, text: str) -> str:
        tokenizer = self._pipe.tokenizer
        ids = tokenizer(text, truncation=True,
                        max_length=self._max_input_tokens)["input_ids"]
        return tokenizer.decode(ids, skip_special_tokens=True)

    def summarize(self, text: str, max_sentences: int = 3) -> Summary:
        # ~40 tokens per sentence is a workable budget for news copy
        out = self._pipe(self._truncate(text), max_length=max_sentences * 40,
                         min_length=15, do_sample=False)
        summary_text = out[0]["summary_text"].strip()
        sentences = split_sentences(summary_text)[:max_sentences]
        return Summary(text=" ".join(sentences), sentences=sentences,
                       method=f"{self.name}:{self.model_name}")
