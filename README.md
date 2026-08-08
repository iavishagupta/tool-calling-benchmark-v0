# Hindi Tool-Calling Benchmark (Prototype)

A mini, BFCL-style tool-calling benchmark for Hindi, built as a prototype
before scaling to other Indian regional languages.

## Files

| File | What it is |
|---|---|
| `functions.py` | The 6 real, callable tool implementations (weather, currency, reminder, restaurant, message) with live API calls |
| `tools_schema_v2.json` | Function schemas (name, params, types) matching `functions.py` exactly — this is what gets shown to the LLM |
| `hindi_bfcl_dataset_v2.json` | 14 Hindi questions only, no answers |
| `hindi_bfcl_ground_truth_v2.json` | The correct function call for each question id, keyed to match the dataset |
| `ast_utils.py` | `decode_ast()` parses the LLM's raw text output into a structured call; `ast_checker()` compares it against ground truth |
| `main.py` | Runs the whole loop: question → LLM (with schema) → raw output → decode → check → score |

## How it fits together

```
hindi_bfcl_dataset_v2.json (question)
            |
            v
   tools_schema_v2.json  --->  LLM  --->  raw text output
            |                                   |
            |                                   v
            |                          decode_ast() (ast_utils.py)
            |                                   |
            v                                   v
hindi_bfcl_ground_truth_v2.json  --->  ast_checker() (ast_utils.py)
                                                |
                                                v
                                          PASS / FAIL
```

The dataset and ground truth are kept in separate files (standard BFCL
practice) so the model is never shown the answer while being tested — the
schema is separate too, since it's reused across every question rather
than being per-question data.

## Tools covered

1. `get_weather_today(city)` — current weather
2. `get_weather_forecast(city, date)` — forecast, date rounded to the nearest 3-hour slot (00/03/06/09/12/15/18/21)
3. `convert_currency(amount, from_currency, to_currency)`
4. `set_reminder(task, date, time)`
5. `search_restaurant(city, cuisine, price_range)`
6. `send_message(recipient, message)`

## Dataset coverage (14 queries)

- 2 queries per tool (12 total)
- 1 parallel-call query (two tools in one question)
- 1 irrelevance query (no tool fits — model should return `[]`)

Relative dates ("कल", "परसों", "अगला शुक्रवार") are resolved against a fixed
`reference_date` (`2026-08-08`) stated in `hindi_bfcl_dataset_v2.json`, so
ground truth stays deterministic regardless of when you actually run it.

## Running the benchmark

```bash
pip install openai
export OPENAI_API_KEY=your_key_here   # or point base_url at a local model
python main.py
```

This prints PASS/FAIL per query, a final score, and writes full results to
`results.json`. Swap `model="gpt-4o-mini"` in `main.py`'s `call_llm()` for
whichever model you're actually benchmarking.

## Extending later

- More queries per tool (currently just 2 — thin for real eval)
- More irrelevance and parallel-call cases (these are the hardest categories)
- Multi-turn queries (BFCL also tests follow-up turns, not just single-shot)
- Scale the same structure to other regional languages once Hindi is validated