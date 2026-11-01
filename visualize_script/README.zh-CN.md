# 论文图表

[English](README.md) | 简体中文

基于同目录下的数据重新绘制论文图表。

| 目录 | 图表 | 输入 |
| --- | --- | --- |
| `msq_ranking/` | 各配置的 MSQ 排名 | `msq_values.csv` |
| `relationship/` | 成功率差值与费用差值、关键步数差值的关系（MAD-SAE − SA） | `source_summary.csv` |
| `domain/` | 按委派需求与领域划分的任务分布 | `source/` |

## 使用方法

```bash
pip install matplotlib numpy pillow pymupdf
python3 visualize_script/msq_ranking/draw_msq.py
python3 visualize_script/relationship/draw_relationship.py
python3 visualize_script/domain/gen_benchmark_oracle_nested_pie.py
```

各脚本将 PDF、SVG 和 PNG 文件写入各自目录。若已安装 Times New Roman 或 Nimbus Roman 字体，将优先使用。
