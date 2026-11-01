# 委派适当性（DA）

[English](README.md) | 简体中文

以金标准委派先验（Delegation Prior）为参照，衡量主 Agent *是否*委派、*如何*委派。

| 指标 | 含义 |
| --- | --- |
| **UDR** ↓ | 89 个需要委派的任务中，未发生委派的比例 |
| **ODR** ↓ | 77 个无需委派的任务中，仍发生委派的比例 |
| **P / R / F1<sub>hit</sub>** ↑ | 实际与金标准子 Agent 单元的一对一匹配 |

仅做规划的子 Agent 不计为委派。

## 使用方法

```bash
python3 -m eval.delegation_appropriateness.evaluate \
  --dump results/MODEL/spec --out results/MODEL/spec
```

`--dump` 目录下须有 [`summary.csv`](../common/README.zh-CN.md)，用于选定每个任务的运行。

| 参数 | 说明 |
| --- | --- |
| `--dump DIR` | 实验目录（必填） |
| `--out DIR` | 输出目录（必填，可与 `--dump` 相同） |
| `--summary CSV` | 运行选择 CSV（默认 `<dump>/summary.csv`） |
| `--match` | 调用 LLM 审核模型，为未缓存的子 Agent 打标签 |
| `--llm-key FILE` | 从文件读取审核模型的 API 密钥 |
| `--workers N` | 打标签并发数（默认 `6`） |
| `--gt-path DIR`、`--cache DIR` | 使用其他金标准标签或标签缓存 |

评测多个实验：`bash eval/delegation_appropriateness/scripts/run_batch.sh DIR1 DIR2 -- --match`。

| 输出 | 内容 |
| --- | --- |
| `summary.json` | 覆盖率、UDR / ODR 与 `hit_scores`（`gt_total`、`actual_total`、`matched`、`precision`、`recall`、`f1`） |
| `task_metrics.json` | 逐任务：委派判定、单元与匹配结果 |
| `task_metrics.csv` | 逐任务：覆盖情况与 `hit_*` 指标 |

<a id="llm-reviewer"></a>

## LLM 审核模型

LLM 审核模型为每个子 Agent 标注功能标签，标签缓存在 [`delegate_llm_tag_cache/`](delegate_llm_tag_cache/README.zh-CN.md)。不加 `--match` 时，评测器不调用任何 API，缺少标签即报错；加上 `--match` 后，仅为缺失的子 Agent 打标签并写入缓存。

| 环境变量 | 默认值 |
| --- | --- |
| `DELEGATE_LLM_API_KEY` | API 密钥（也可通过 `DELEGATE_LLM_KEY` / `--llm-key` 指定密钥文件） |
| `DELEGATE_LLM_MODEL` | `deepseek-v4-flash` |
| `DELEGATE_LLM_ENDPOINT` | `https://api.deepseek.com/chat/completions`（兼容任意 chat-completions API） |
| `DELEGATE_LLM_REASONING_EFFORT` | `none`（设为空字符串则不发送该字段） |

请保持默认审核模型：金标准标签由它标注，更换模型会导致命中指标不可比。

<a id="matching"></a>

## 匹配规则

每个子 Agent 从固定词表中获得功能标签：

```text
Read  (14): rail_12306, woocommerce, yahoo-finance, snowflake, scholarly-arxiv,
            external-fetch, notion, youtube, playwright-web, filesystem-workspace,
            canvas, howtocook, emails, github
Write (11): excel, word, ppt, notion, email, calendar, gsheet, gform, pdf,
            processor, other-write
```

- **单元**：每个写入型子 Agent 构成一个单元；同一波次（wave）内读取同一领域的子 Agent 合并为一个单元，涉及多个领域的子 Agent 计入多个单元。
- **匹配**：标签相同的金标准单元与实际单元通过最大二分匹配一对一配对。`other-write` 计入总数，但不参与匹配。
- **汇总**：命中指标在有执行轨迹的任务上做微平均，缺少轨迹的任务不参与计分。

## 内置数据

| 目录 | 内容 |
| --- | --- |
| [`delegate_gt_tag/`](delegate_gt_tag/README.zh-CN.md) | 全部 166 个任务的金标准标签（265 个单元） |
| [`delegate_llm_tag_cache/`](delegate_llm_tag_cache/README.zh-CN.md) | 金标准与实际子 Agent 的标签缓存 |
