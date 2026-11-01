# Oracle task documents

This directory contains the **166 canonical `.task.md` task documents** used by MS-Eval. They provide task context and golden delegation guidance for the [golden delegation tags](../../eval/delegation_appropriateness/delegate_gt_tag/README.md).

Each filename defines a task ID by removing `.task.md`. The ID connects the task document, its golden-tag JSON, task-category lists, and execution summaries. Golden-tag records store the SHA-256 of the corresponding document in `source.oracle166_sha256`; changing task text requires a deliberate annotation update.

Browse tasks by [domain](../task_categories/cluster_by_domain/README.md) or by [delegation category](../task_categories/cluster_by_delegation/README.md). The category READMEs link here. Task documents are not duplicated inside the category directories.
