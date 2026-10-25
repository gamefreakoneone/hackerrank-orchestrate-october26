# Usage report — final full-dataset run

Run `output_candidate_20261025T085130Z` (code revision `375604e2c3387748ee0c942e0c28e46433bcec9a`), the cold-cache run that produced the submitted
`output.csv` (sha256 `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`): `python code/main.py --cases all --no-cache`
over 518 requests. Source: usage ledger `code/evaluation/final_run/usage_ledger.jsonl` (one row per
structured call). `--no-cache` skips cache reads, so every call below was a real model call.

| Provider | Model | Calls by task | Calls | Attempts (incl. repair) | Cached | Input tokens | Output tokens | Total tokens | Avg tokens / request | Est. cost | Est. cost / request |
|---|---|---|---|---|---|---|---|---|---|---|---|
| azure | gpt-6-luna | intent_adjudication 3 | 3 | 3 | 0 | 1093 | 58 | 1151 | 2.2 | $0.000138 | $0.00000027 |
| gemini | gemini-3.8-flash | vision_extract 11 | 11 | 11 | 0 | 18099 | 53937 | 72036 | 139.1 | $0.215838 | $0.00041668 |
| jev | jev-1.14.0 | category_fallback 3, intent 518 | 521 | 521 | 0 | 254084 | 34709 | 288793 | 557.5 | $0.010672 | $0.00002060 |
| **overall** |  |  | 535 | 535 | 0 | 273276 | 88704 | 361980 | 698.8 | $0.226648 | $0.00043754 |

- Averages divide by all 518 requests (most requests make exactly one Jev intent call; PNG extraction is 11 calls
  shared by the whole run; Azure is called only when the intent decision table needs adjudication).
- **Costs are estimates.** No official price page for these model ids was found; the prices below come from third-party
  trackers (recorded with their sources in `code/config/pricing.yaml`). Gemini output tokens include reasoning tokens.

```yaml
# USD per 1M tokens, keyed by served model id. ESTIMATES from third-party price trackers (no official price page was
# found for these model ids on 2026-10-25); the usage report labels every cost as an estimate. null = unknown.
models:
  jev-1.14.0:
    input_per_million: 0.042
    output_per_million: 0.0
    source: "third-party: https://www.eesel.ai/blog/typesafe-jev-pricing , https://docs.litellm.ai/blog/typesafe_jev (output free)"
  gpt-6-luna:
    input_per_million: 0.10
    output_per_million: 0.50
    source: "third-party: https://www.azurespeed.com/AzureAiModelPricing/Models/openai-gpt-6-luna (Azure Global Standard)"
  gemini-3.8-flash:
    input_per_million: 0.75
    output_per_million: 3.75
    source: "third-party: https://anotherwrapper.com/llm-pricing/gemini-3.8-flash , https://eesel.ai/blog/gemini-3-8-flash-pricing (introductory rate)"
```
