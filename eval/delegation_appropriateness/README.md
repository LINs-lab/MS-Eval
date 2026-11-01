# Delegation Appropriateness (DA)

English | [简体中文](README.zh-CN.md)

Measure *whether* and *how* the main agent delegates, against the golden Delegation Priors.

| Metric | Meaning |
| --- | --- |
| **UDR** ↓ | Share of the 89 delegation-needed tasks where the agent did not delegate |
| **ODR** ↓ | Share of the 77 no-need tasks where the agent delegated anyway |
| **P / R / F1<sub>hit</sub>** ↑ | One-to-one match between executed and golden sub-agent units |

Planning-only sub-agents do not count as delegation.

## Usage

```bash
python3 -m eval.delegation_appropriateness.evaluate \
  --dump results/MODEL/spec --out results/MODEL/spec
```

`--dump` must contain a [`summary.csv`](../common/README.md), which selects the run of each task.

| Option | Description |
| --- | --- |
| `--dump DIR` | Experiment directory (required) |
| `--out DIR` | Output directory (required; may equal `--dump`) |
| `--summary CSV` | Run-selection CSV (default: `<dump>/summary.csv`) |
| `--match` | Label uncached sub-agents with the LLM reviewer |
| `--llm-key FILE` | Read the reviewer API key from a file |
| `--workers N` | Labeling concurrency (default: `6`) |
| `--gt-path DIR`, `--cache DIR` | Use other golden tags or another label cache |

For several experiments: `bash eval/delegation_appropriateness/scripts/run_batch.sh DIR1 DIR2 -- --match`.

| Output | Contents |
| --- | --- |
| `summary.json` | Coverage, UDR / ODR, and `hit_scores` (`gt_total`, `actual_total`, `matched`, `precision`, `recall`, `f1`) |
| `task_metrics.json` | Per task: delegation decision, units, and matches |
| `task_metrics.csv` | Per task: coverage and `hit_*` scores |

<a id="llm-reviewer"></a>

## LLM reviewer

An LLM reviewer assigns function labels to each sub-agent; labels are cached in [`delegate_llm_tag_cache/`](delegate_llm_tag_cache/README.md). Without `--match`, the evaluator makes no API calls and stops if a label is missing. With `--match`, it labels only the missing sub-agents and adds them to the cache.

| Environment variable | Default |
| --- | --- |
| `DELEGATE_LLM_API_KEY` | API key (or a key file via `DELEGATE_LLM_KEY` / `--llm-key`) |
| `DELEGATE_LLM_MODEL` | `deepseek-v4-flash` |
| `DELEGATE_LLM_ENDPOINT` | `https://api.deepseek.com/chat/completions` (any chat-completions API) |
| `DELEGATE_LLM_REASONING_EFFORT` | `none` (set empty to omit the field) |

Keep the default reviewer: the golden tags were labeled with it, so a different reviewer makes hit scores incomparable.

<a id="matching"></a>

## Matching

Each sub-agent receives function labels from a fixed vocabulary:

```text
Read  (14): rail_12306, woocommerce, yahoo-finance, snowflake, scholarly-arxiv,
            external-fetch, notion, youtube, playwright-web, filesystem-workspace,
            canvas, howtocook, emails, github
Write (11): excel, word, ppt, notion, email, calendar, gsheet, gform, pdf,
            processor, other-write
```

- **Units.** Each writing sub-agent is one unit. Reading sub-agents that share a domain within a wave form one unit; a sub-agent with several domains contributes to several.
- **Matching.** Golden and executed units with equal labels are matched one-to-one by maximum bipartite matching. `other-write` counts toward totals but never matches.
- **Aggregation.** Hit scores are micro-averaged over tasks with traces; tasks without traces are excluded.

## Bundled data

| Directory | Contents |
| --- | --- |
| [`delegate_gt_tag/`](delegate_gt_tag/README.md) | Golden tags for all 166 tasks (265 units) |
| [`delegate_llm_tag_cache/`](delegate_llm_tag_cache/README.md) | Cached labels for golden and executed sub-agents |
