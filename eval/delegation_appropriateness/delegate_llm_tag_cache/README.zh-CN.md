# LLM 标签缓存

[English](README.md) | 简体中文

金标准（`gt`）与实际（`actual`）子 Agent 的功能标签缓存。每个 `<input_hash>.json` 保存一次标注请求（最多 12 个子 Agent）及其结果。缓存覆盖论文中的全部运行，重新评测这些运行无需调用 API。

## 使用方法

[DA 评测器](../README.zh-CN.md)默认读取本目录，可用 `--cache DIR` 指定其他目录。加上 `--match` 时，缺失的标签由 [LLM 审核模型](../README.zh-CN.md#llm-reviewer)生成并写入本目录。共享缓存时请保留已有条目。

## 格式

| 字段 | 内容 |
| --- | --- |
| `input_hash` | 缓存键，与文件名一致 |
| `reviewer`、`prompt_version`、`system_sha256` | 标注协议 |
| `payload` | 任务文本、子 Agent 输入与词表版本 |
| `result.tags` | 功能标签 |

缓存键由审核模型、提示词和输入内容共同决定，其他提示词版本的条目不会被使用。当前协议：词表 `expanded-20260912-v2`，提示词 `expanded-20260912-llm-v2`，审核模型 `deepseek-v4-flash`。
