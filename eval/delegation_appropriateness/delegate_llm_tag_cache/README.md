# LLM Label Cache

English | [简体中文](README.zh-CN.md)

Cached function labels for golden (`gt`) and executed (`actual`) sub-agents. Each `<input_hash>.json` stores one labeling request (up to 12 sub-agents) and its result. The cache covers every run reported in the paper, so re-evaluating those runs needs no API calls.

## Usage

The [DA evaluator](../README.md) reads this directory by default; use `--cache DIR` to choose another. With `--match`, missing labels are requested from the [LLM reviewer](../README.md#llm-reviewer) and added here. Keep existing entries when sharing the cache.

## Format

| Field | Contents |
| --- | --- |
| `input_hash` | Cache key, equal to the filename |
| `reviewer`, `prompt_version`, `system_sha256` | Labeling protocol |
| `payload` | Task text, sub-agent inputs, and vocabulary version |
| `result.tags` | Function labels |

The key hashes the reviewer, prompt, and payload. Entries from other prompt versions are ignored; the current protocol is vocabulary `expanded-20260912-v2`, prompt `expanded-20260912-llm-v2`, reviewer `deepseek-v4-flash`.
