# Run Summaries

English | [简体中文](README.zh-CN.md)

Build the per-task `summary.csv` read by the DA and OU evaluators. Outcomes and critical steps come from each run's `audit.html`; token usage comes from the Kimi session logs (`wire.jsonl`) of the main agent and all sub-agents.

## Usage

```bash
python3 -m eval.common.build_audit_summary results/MODEL/spec results/MODEL/sa
```

Writes `summary.csv` into each variant directory. You may also pass a model directory or `results/` itself; variant directories are discovered automatically. All `RUN_ID/` runs of a variant are merged, and if a task has several runs, the latest one is used. Use `-o PATH` to write elsewhere (one variant only).

## Columns

| Column | Meaning |
| --- | --- |
| `Task`, `Result` | Task ID; `1` = passed, `0` = failed |
| `Comment` | Stop reason, e.g. `claim_done`, `timeout`, `100_step_limit`, `API Error` |
| `Critical Steps` | Main-agent steps plus, for each delegation, the steps of its slowest sub-agent; API-error steps excluded |
| `Subagent-Delegate` | `1` if any sub-agent ran, including planning-only ones |
| `Duration`, `Checkpoints`, `API Error Steps(main-agent/subagent)` | Copied from the audit page |
| `inputOther`, `inputCacheRead`, `inputCacheCreation`, `output` | Token usage |
| `Input-Cost`, `inputCacheRead-Cost`, `output-Cost`, `total-Cost` | Estimated cost in USD |
| `audit.html` | Selected audit page, relative to the CSV |

<a id="cost-estimation"></a>

## Cost estimation

`build_audit_summary` prices token usage with [`eval/orchestration_utilities/pricing.json`](../orchestration_utilities/pricing.json), in USD per 1M tokens. Prices are looked up by the model directory name, `MODEL` in `results/MODEL/`. Cache-creation tokens are not billed.

A model missing from this file gets zero cost. To add one:

1. Add an entry under `"models"` in `eval/orchestration_utilities/pricing.json`. The key must match the directory name exactly. The three rates are uncached input, cached input and output:

   ```json
   "my-model": [1.00, 0.10, 4.00]
   ```

2. Run `build_audit_summary`, or re-run it if `summary.csv` already exists. The output should show `model=my-model`. If it shows `model=None` and `[warn] no pricing key`, the key does not match the directory name.

For tiered prices, add the entry under `"tiered_models"` in the same format as `minimax-m3`. Requests with more than `input_token_threshold` input tokens use the `above` rates; the threshold is 512K for `minimax-m3` and 272K for `gpt-5.6-sol`.
