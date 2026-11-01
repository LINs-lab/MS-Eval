# Orchestration Utilities (OU)

English | [简体中文](README.zh-CN.md)

Compare MAD-SAE with its single-agent (SA) baseline on the tasks where the main agent actually delegated. Each utility lies in [0, 1]: **0.5 means parity**, and higher favors MAD-SAE.

| Utility | Formula | Tasks |
| --- | --- | --- |
| **U<sub>p</sub>** performance | `SR_mad / (SR_mad + SR_sa)` | `D_del` |
| **U<sub>e</sub>** efficiency | `Csteps_sa / (Csteps_mad + Csteps_sa)` | `D_del+` |
| **U<sub>c</sub>** cost | `Cost_sa / (Cost_mad + Cost_sa)` | `D_del+` |

- `D_del`: tasks where the MAD-SAE run invoked at least one non-planning sub-agent (from DA output) and both runs have a summary. `D_del+`: the subset MAD-SAE solved.
- `SR` is the success rate; `Csteps` and `Cost` are mean critical steps and mean cost per task. SA values are taken on the same tasks, whether or not SA succeeded.

## Usage

Run the [summary builder](../common/README.md) on both experiments and [DA](../delegation_appropriateness/README.md) on the MAD-SAE experiment first.

```bash
python3 -m eval.orchestration_utilities.evaluate \
  --mad results/MODEL/spec --sa results/MODEL/sa \
  --out results/MODEL/spec/utilities.json
```

| Option | Description |
| --- | --- |
| `--mad DIR` | MAD-SAE experiment (required) |
| `--sa DIR` | SA baseline (required) |
| `--out FILE` | Output JSON (default: stdout) |
| `--da DIR` | DA output directory (default: `--mad`) |
| `--include-failed` | Diagnostic only: include MAD-SAE failures in U<sub>e</sub> / U<sub>c</sub>; differs from the paper |

The output holds the three utilities, their underlying success counts and means, and any tasks missing DA coverage or a paired summary. Empty task sets give `null`.

Costs come from `total-Cost` in `summary.csv`, priced with [`pricing.json`](pricing.json); see [cost estimation](../common/README.md#cost-estimation).
