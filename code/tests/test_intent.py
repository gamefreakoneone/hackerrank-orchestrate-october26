import csv
import os
from pathlib import Path

import pytest

from ghostaudit.intent import IntentLabel, classify, keyword_says_deletion
from ghostaudit.llm.cache import DiskCache
from ghostaudit.llm.providers import LLMLayer, TransportResult

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
NON_DELETION = {
    "Can you tell me what personal data you store about me?": "ACCESS",
    "My phone number changed, please update it on my profile.": "CORRECTION",
    "I want to download all my data as a file I can move to another shop.": "EXPORT",
    "Stop sending me newsletters, but keep my account.": "OPT_OUT",
    "¿Pueden enviarme una copia de los datos personales que tienen sobre mí?": "ACCESS",
    "Merci de corriger l'orthographe de mon nom de famille sur mon compte.": "CORRECTION",
}


def layer(tmp_path, monkeypatch, jev_label=None, jev_probability=1.0, azure_label=None):
    monkeypatch.setenv("JEV_MODEL", "fake-jev")
    monkeypatch.setenv("AZURE_DEPLOYMENT_FALLBACK", "fake-azure")
    calls = []

    def fake_jev(*, inputs, schema, images):
        calls.append("jev")
        if jev_label is None:
            raise RuntimeError("jev down")
        return TransportResult(output={"intent": {"choice": jev_label, "confidence": jev_probability,
                                                  "probabilities": {jev_label: jev_probability}}},
                               input_tokens=1, output_tokens=1, served_model="fake-jev")

    def fake_azure(*, inputs, schema, images):
        calls.append("azure")
        if azure_label is None:
            raise RuntimeError("azure down")
        return TransportResult(output={"label": azure_label}, input_tokens=1, output_tokens=1,
                               served_model="fake-azure")

    llm = LLMLayer(ledger_path=None, cache=DiskCache(tmp_path), transports={"jev": fake_jev, "azure": fake_azure})
    return llm, calls


def test_confident_jev_agreeing_with_keywords_is_accepted(tmp_path, monkeypatch):
    llm, calls = layer(tmp_path, monkeypatch, "DELETION")
    result = classify("Please delete my account.", llm)
    assert (result.label, result.source, calls) == (IntentLabel.DELETION, "jev", ["jev"])


def test_keyword_disagreement_goes_to_azure(tmp_path, monkeypatch):
    llm, calls = layer(tmp_path, monkeypatch, "OPT_OUT", azure_label="OPT_OUT")
    result = classify("Stop the promotional emails, I am not asking for deletion.", llm)   # keyword: deletion
    assert (result.label, result.source, result.jev_label, calls) == (IntentLabel.OPT_OUT, "azure", "OPT_OUT",
                                                                      ["jev", "azure"])


def test_low_confidence_goes_to_azure_and_falls_back(tmp_path, monkeypatch):
    llm, calls = layer(tmp_path, monkeypatch, "DELETION", jev_probability=0.5, azure_label="DELETION")
    assert classify("Please delete my account.", llm).source == "azure" and calls == ["jev", "azure"]
    llm, _ = layer(tmp_path / "c", monkeypatch, "DELETION", jev_probability=0.5, azure_label=None)
    assert classify("Please delete my account.", llm).source == "jev_unconfirmed"


def test_offline_keyword_path_is_provisional():
    result = classify("Por favor eliminen mi cuenta.")
    assert (result.label, result.source) == (IntentLabel.DELETION, "keyword_provisional")
    assert classify("Please update my phone number.").label == IntentLabel.OTHER


def test_negations_still_contain_deletion_words():
    assert keyword_says_deletion("I still use it, so please don't delete or change anything.")


@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 for live model calls")
def test_live_samples_are_deletion_and_synthetic_requests_are_not(tmp_path):
    llm = LLMLayer(ledger_path=tmp_path / "usage.jsonl")
    with (DATASET_DIR / "sample_deletion_requests.csv").open(encoding="utf-8", newline="") as handle:
        samples = list(csv.DictReader(handle))
    assert all(classify(r["request_text"], llm).label == IntentLabel.DELETION for r in samples)
    for text, expected in NON_DELETION.items():
        assert classify(text, llm).label.value == expected, text
