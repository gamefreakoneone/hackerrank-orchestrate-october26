# Spec 0009 — vision-extraction: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
Live extraction (one structured Gemini call per PNG via the shared layer; ledger runs/usage_vision_0009.jsonl):
11 calls, gemini-3.8-flash, 18,099 input + 66,512 output tokens (output includes model reasoning tokens).
$ python -m pytest code/tests/test_vision.py -q          # recorded responses in code/tests/fixtures/vision_*.json
4 passed
$ python code/tools/evidence_coverage.py --png
total observations 3035 (png 23); files without records 4 (evidence_42, evidence_46: no resource id on screen;
evidence_18, evidence_27: PDFs without resource ids)
$ python code/evaluation/run_eval.py --split dev        # runs/score_20261025T082316Z_dev.md
status 0/20, F1 0.000 — unchanged (pipeline still the stub)
```

Per-PNG records kept / dropped:

| file | screen | records | dropped |
|---|---|---|---|
| evidence_04 | account admin console | 2 | 0 |
| evidence_09 | search index inspector | 2 | 1 identifier |
| evidence_14 | connector console | 2 | 0 |
| evidence_19 | analytics profile | 1 | 0 |
| evidence_23 | export console | 4 | 3 identifiers |
| evidence_28 | support ticket console | 1 | 0 |
| evidence_32 | backup restore console | 4 | 3 identifiers (company emails not in the identity universe) |
| evidence_37 | security audit explorer | 6 | 0 |
| evidence_42 | deleted account reference | 0 | 1 non-resource id (ORD-/CS-/FIN- references only) |
| evidence_46 | object storage browser | 0 | 5 non-resource ids |
| evidence_60 | marketing profile | 1 | 1 identifier (email not in identity universe; phone kept) |

**Spot checks by eye (3 PNGs):** evidence_37 — table shows user_03 with audit_record_001…006, all "Valid": matches the
6 extracted rows. evidence_14 — data_flow_1121 (jain.aditi@gmail.com, detail pane "Healthy") and data_flow_9846
(lucia-torres@gmail.com) plus two non-resource connectors: matches. evidence_32 — backup_9286…9291 with account
emails; only areed1433@gmail.com is a known identity, "Verified" is a checksum status (no restore field mapped): matches.
Also viewed evidence_42 (user_17 references, no resource id) and evidence_60 (marketing_001, Email opt-in Yes).

**Must-check (phase 0b):** audit_record_4902/6645/5569/4128/7095/3954/1707 → not in evidence_37 (only 001–006);
account_004 → not in evidence_42 (no resource ids). **Not found**; TECHNICAL_DESIGN §5 Q3 updated (reach stays 103/111).
PNG contribution on samples: one eligible identifier hit (case_15 data_flow_9846 via evidence_14); sample identifier
recall unchanged at 76/111 (that resource was already reached through text).

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0008) | 0.000 | not measured | 0.000 | 0.000 |
| after | 0.000 | not measured | 0.000 | 0.000 |

## Notes

- `evidence/vision.py` + `prompts/vision_extract.md` (generic screen-transcription prompt, no case hints).
  Revalidation: resource ids must full-match the resource pattern; identifiers must be email (and in the identity
  universe), phone, user id or 64-hex hash. Category from the screen origin only when the resource prefix belongs to
  that screen's system (`png_origin_category`), else none (0011 fallback). Status text → `enabled` /
  `restore_allowed` via `png_status_fields`.
- Offline / missing cache: a PNG without an answer yields no observations and is reported as missing evidence, never
  as absence.
