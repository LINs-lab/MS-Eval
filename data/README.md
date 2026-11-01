# Data

English | [简体中文](README.zh-CN.md)

The 166 MS-Eval tasks and their categories.

```text
data/
├── oracle166/                    # One <task-id>.task.md per task
└── task_categories/
    ├── cluster_by_delegation/    # Delegation need and read/write type
    └── cluster_by_domain/        # Application domain
```

## Tasks

Each [`oracle166/<task-id>.task.md`](oracle166/README.md) contains the task description followed by its **Delegation Prior**: the golden plan of waves, sub-agent types, and sub-tasks. The DA evaluator scores runs against these plans, and the `oracle` mode gives them to the agent as task briefs. The task ID, the filename without `.task.md`, links task documents, golden tags, category lists, and run outputs.

## Categories

| [Delegation need](task_categories/cluster_by_delegation/README.md) | Tasks |
| --- | ---: |
| Delegation required ($\mathcal{D}_{\text{need}}$) | 89 |
| &nbsp;&nbsp;• Read-only | 22 |
| &nbsp;&nbsp;• Writable | 23 |
| &nbsp;&nbsp;• Read and write | 44 |
| Delegation not required ($\mathcal{D}_{\text{no-need}}$) | 77 |

| [Domain](task_categories/cluster_by_domain/README.md) | Tasks | Domain | Tasks |
| --- | ---: | --- | ---: |
| Enterprise data warehouse | 47 | Stock market | 16 |
| Learning management system | 35 | Food and catering | 11 |
| Academic research | 21 | Video platform | 9 |
| E-commerce | 21 | Railway system | 6 |

Category directories hold task-ID lists that link back to `oracle166/`. Golden tags and the label cache live with the [DA evaluator](../eval/delegation_appropriateness/README.md). Benchmark runs are written to `results/` (git-ignored), not to this directory.
