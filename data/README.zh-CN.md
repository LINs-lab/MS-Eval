# 数据

[English](README.md) | 简体中文

MS-Eval 的 166 个任务及其分类。

```text
data/
├── oracle166/                    # 每个任务一个 <task-id>.task.md
└── task_categories/
    ├── cluster_by_delegation/    # 委派需求与读写类型
    └── cluster_by_domain/        # 应用领域
```

## 任务

每个 [`oracle166/<task-id>.task.md`](oracle166/README.md) 包含任务描述及其**委派先验（Delegation Prior）**：由波次、子 Agent 类型和子任务构成的金标准方案。DA 评测器以此为参照为运行结果打分；`oracle` 模式则把它作为任务说明提供给 Agent。任务 ID 即去掉 `.task.md` 后的文件名，用于关联任务文档、金标准标签、分类清单和运行结果。

## 分类

| [委派需求](task_categories/cluster_by_delegation/README.md) | 任务数 |
| --- | ---: |
| 需要委派（$`\mathcal{D}_{\text{need}}`$） | 89 |
| &nbsp;&nbsp;• 只读 | 22 |
| &nbsp;&nbsp;• 写入 | 23 |
| &nbsp;&nbsp;• 读写 | 44 |
| 无需委派（$`\mathcal{D}_{\text{no-need}}`$） | 77 |

| [领域](task_categories/cluster_by_domain/README.md) | 任务数 | 领域 | 任务数 |
| --- | ---: | --- | ---: |
| 企业数据仓库 | 47 | 股票市场 | 16 |
| 学习管理系统 | 35 | 餐饮 | 11 |
| 学术研究 | 21 | 视频平台 | 9 |
| 电子商务 | 21 | 铁路系统 | 6 |

分类目录中保存任务 ID 清单，并链接回 `oracle166/`。金标准标签与标签缓存随 [DA 评测器](../eval/delegation_appropriateness/README.zh-CN.md)提供。benchmark 运行结果写入 `results/`（Git 忽略），而非本目录。
