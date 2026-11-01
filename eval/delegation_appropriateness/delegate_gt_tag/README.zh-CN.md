# 金标准委派标签

[English](README.md) | 简体中文

[DA 评测器](../README.zh-CN.md)使用的已审核金标准标签：每个任务一个 JSON 文件，另有索引 `_index.json`。166 个任务中，89 个需要委派、77 个无需委派，共包含 265 个金标准子 Agent 单元。

## 格式

| 字段 | 内容 |
| --- | --- |
| `task`、`need_delegation` | 任务 ID 及是否需要委派 |
| `waves`、`nodes` | 金标准子 Agent 分配及功能标签 |
| `units`、`bag`、`counts` | 匹配单元及其计数 |
| `roles`、`write_labels`、`domains`、`matchable_roles` | 标签词表；`other-write` 不参与匹配（[详情](../README.zh-CN.md#matching)） |
| `source` | [`data/oracle166`](../../../data/oracle166/README.md) 中的源任务文档及其 SHA-256 |
| `reviewer`、`prompt_version`、`system_sha256`、`label_cache_keys` | 标注来源信息 |

数据格式 `delegate-gt-tag-v4`，词表 `expanded-20260912-v2`，提示词 `expanded-20260912-llm-v2`，审核模型 `deepseek-v4-flash`。

## 重新生成

```bash
python3 -m eval.delegation_appropriateness.export_delegate_gt_tags --out results/regenerated_gt
```

基于已有节点和[标签缓存](../delegate_llm_tag_cache/README.zh-CN.md)离线重建标签及派生字段，相同输入生成完全相同的文件。如需原地更新本目录，使用 `--out eval/delegation_appropriateness/delegate_gt_tag`。
