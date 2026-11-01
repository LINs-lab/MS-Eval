# Paper Figures

English | [简体中文](README.zh-CN.md)

Scripts that redraw the paper figures from the data stored next to them.

| Directory | Figure | Input |
| --- | --- | --- |
| `msq_ranking/` | MSQ ranking of all configurations | `msq_values.csv` |
| `relationship/` | Δ success rate vs. Δ cost and Δ critical steps (MAD-SAE − SA) | `source_summary.csv` |
| `domain/` | Task distribution by delegation need and domain | `source/` |

## Usage

```bash
pip install matplotlib numpy pillow pymupdf
python3 visualize_script/msq_ranking/draw_msq.py
python3 visualize_script/relationship/draw_relationship.py
python3 visualize_script/domain/gen_benchmark_oracle_nested_pie.py
```

Each script writes PDF, SVG, and PNG files into its own directory. Times New Roman or Nimbus Roman is used if installed.
