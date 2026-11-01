# Task categories by delegation need

The lists partition the 166 [oracle tasks](../../oracle166/README.md). Each text file contains one task ID per line. Category READMEs provide links to the canonical documents.

| Category | Tasks | List |
| --- | ---: | --- |
| Delegation required | 89 | [need_subagent.txt](need_subagent/need_subagent.txt) |
| Delegation not required | 77 | [no_need_subagent.txt](no_need_subagent/no_need_subagent.txt) |
| Required: read-only | 22 | [read_only.txt](need_subagent/read_only/read_only.txt) |
| Required: writable | 23 | [writable.txt](need_subagent/writable/writable.txt) |
| Required: read and write | 44 | [read_and_write.txt](need_subagent/read_and_write/read_and_write.txt) |

The final three rows are disjoint subsets of the 89 tasks requiring delegation. `descriptive_statistics.txt` files summarize the original annotation counts; `domain_descriptive_statistics.tsv` describes the domains of those 89 tasks. The evaluator reads `need_delegation` from the frozen [GT index](../../../eval/delegation_appropriateness/delegate_gt_tag/_index.json), whose need/no-need partition agrees with these lists.

These curated task-level categories are maintained separately from automatic node tags and can differ from rule-derived node classifications. Golden delegation tags and cached functional labels are bundled with the [DA evaluator](../../../eval/delegation_appropriateness/README.md); see that guide for scoring commands and version details.
