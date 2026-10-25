"""Request intent gate (spec 0013): does request_text authorize deletion? Models return typed labels; this module's
decision table decides. Offline without cached answers, the keyword check is used and marked provisional."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from ghostaudit.config import env
from ghostaudit.llm.providers import LLMError

LEXICON_PATH = Path(__file__).resolve().parents[1] / "config" / "intent_lexicon.yaml"


class IntentLabel(StrEnum):
    DELETION = "DELETION"
    ACCESS = "ACCESS"
    CORRECTION = "CORRECTION"
    EXPORT = "EXPORT"
    OPT_OUT = "OPT_OUT"
    OTHER = "OTHER"


INTENT_CRITERIA = {
    "DELETION": "delete, erase or close the account or its personal data, including asking to confirm or audit that "
                "an earlier deletion really happened",
    "ACCESS": "see what personal information is held, or receive a copy of it",
    "CORRECTION": "fix or update a detail such as a name, phone number or email address",
    "EXPORT": "download their account data in a portable format",
    "OPT_OUT": "stop marketing or promotional messages while keeping the account",
    "OTHER": "something else, such as login help or a copy of invoices",
}
ADJUDICATION_PROMPT = """Classify what the customer wants, using exactly one label.
DELETION: the customer asks to delete, erase or close their account or personal data, or asks to confirm/audit that a
deletion they requested was really completed. A request that asks for deletion together with something else is DELETION.
ACCESS: see or receive a copy of the personal information held. CORRECTION: change or fix a detail.
EXPORT: download data in a portable format. OPT_OUT: stop marketing while keeping the account. OTHER: anything else.
A message that explicitly says it is not asking for deletion, or asks not to delete or close the account, is not DELETION.

Customer message:
{request_text}"""


class JevIntentAnswer(BaseModel):
    intent: dict                 # {"choice", "confidence", "probabilities"}


class AdjudicatedIntent(BaseModel):
    label: IntentLabel


@dataclass(frozen=True)
class IntentResult:
    label: IntentLabel
    confidence: float | None
    source: str                  # jev | azure | keyword_provisional | jev_unconfirmed
    keyword_deletion: bool
    jev_label: str | None = None

    @property
    def authorizes_deletion(self) -> bool:
        return self.label == IntentLabel.DELETION

    def as_dict(self) -> dict:
        return {"label": self.label.value, "confidence": self.confidence, "source": self.source,
                "keyword_deletion": self.keyword_deletion, "jev_label": self.jev_label}


@cache
def deletion_terms() -> tuple[str, ...]:
    lexicon = yaml.safe_load(LEXICON_PATH.read_text(encoding="utf-8"))["deletion_terms"]
    return tuple(sorted({term.lower() for terms in lexicon.values() for term in terms}))


def keyword_says_deletion(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in deletion_terms())


def jev_intent(llm, text: str) -> tuple[str, float]:
    answer = llm.call(task="intent", schema=JevIntentAnswer, provider="jev", inputs={
        "state": {"request_text": text},
        "questions": {"intent": {"type": "choice", "criteria": INTENT_CRITERIA,
                                 "instructions": "What does the person who wrote `request_text` want done?"}}})
    label = answer.intent["choice"]
    return label, float((answer.intent.get("probabilities") or {}).get(label, 0.0))


def classify(text: str, llm=None) -> IntentResult:
    keyword = keyword_says_deletion(text)
    provisional = IntentResult(IntentLabel.DELETION if keyword else IntentLabel.OTHER, None, "keyword_provisional",
                               keyword)
    if llm is None:
        return provisional
    threshold = float(env("JEV_CONFIDENCE_THRESHOLD", "0.8"))
    try:
        jev_label, probability = jev_intent(llm, text)
    except LLMError:
        jev_label, probability = None, 0.0
    if jev_label is not None and probability >= threshold and (jev_label == IntentLabel.DELETION) == keyword:
        return IntentResult(IntentLabel(jev_label), probability, "jev", keyword, jev_label)
    try:
        adjudicated = llm.call(task="intent_adjudication", schema=AdjudicatedIntent, provider="azure",
                               inputs={"prompt": ADJUDICATION_PROMPT.format(request_text=text)})
        return IntentResult(adjudicated.label, None, "azure", keyword, jev_label)
    except LLMError:
        if jev_label is not None:
            return IntentResult(IntentLabel(jev_label), probability, "jev_unconfirmed", keyword, jev_label)
        return provisional
