"""Draw the enlarged MSQ ranking figure from the local CSV snapshot."""
from pathlib import Path
import csv
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Patch
from PIL import Image
import numpy as np


ROOT = Path(__file__).resolve().parent

# Use Times New Roman when installed, else Nimbus Roman (URW base35), else DejaVu Serif.
for font_path in Path("/usr/share/fonts/urw-base35").glob("NimbusRoman*.otf"):
    font_manager.fontManager.addfont(str(font_path))
available_fonts = {font.name for font in font_manager.fontManager.ttflist}
font_family = next(name for name in ("Times New Roman", "Nimbus Roman", "DejaVu Serif")
                   if name in available_fonts)

plt.rcParams.update({
    "font.family": font_family,
    "font.size": 26,
    "text.color": "black",
    "axes.labelcolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

styles = {
    "GLM-5.3": ("glm", "#1687EF"),
    "Qwen-3.8-Max": ("qwen", "#7862D5"),
    "DeepSeek-V4-Flash-0731": ("dpsk", "#3754E8"),
    "Kimi-K3": ("kimi", "#222222"),
    "GLM-5.3-Flash": ("glm", "#1687EF"),
    "GPT-5.6-Sol": ("gpt", "#222222"),
    "Claude-Sonnet-5": ("anthropic", "#CC7C60"),
    "MiniMax-M3": ("minimax", "#EC3476"),
}

backgrounds = {
    "Oracle": "#FFF3D5",
    "Open-source": "#EDF4FC",
    "Closed-source": "#FCEFE8",
}
legend_order = ("Oracle", "Open-source", "Closed-source")
closed_models = {"GPT-5.6-Sol", "Claude-Sonnet-5"}


def read_rows():
    with (ROOT / "msq_values.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["msq_percent"] = float(row["msq_percent"])
    return rows


def rounded_bar(ax, center, height, width, color, radius_x, radius_y):
    left, right = center - width / 2, center + width / 2
    vertices = [
        (left, 0),
        (left, height - radius_y),
        (left, height),
        (left + radius_x, height),
        (right - radius_x, height),
        (right, height),
        (right, height - radius_y),
        (right, 0),
        (left, 0),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.LINETO,
        MplPath.CURVE3,
        MplPath.CURVE3,
        MplPath.LINETO,
        MplPath.CURVE3,
        MplPath.CURVE3,
        MplPath.LINETO,
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(PathPatch(
        MplPath(vertices, codes),
        facecolor=color,
        edgecolor="none",
        linewidth=0,
    ))


def main():
    rows = read_rows()
    assert len(rows) == 11

    # The original type sizes were 13/14/15/17 pt; all are exactly doubled here.
    fig = plt.figure(figsize=(25.5, 10.8), facecolor="white")
    ax_rect = [0.075, 0.39, 0.91, 0.49]
    ax = fig.add_axes(ax_rect)

    step = 1.42
    x_positions = np.arange(len(rows), dtype=float) * step
    ax.set_xlim(x_positions[0] - 0.82, x_positions[-1] + 0.82)
    ax.set_ylim(0, 45.5)
    ax.set_yticks(np.arange(0, 41, 10))
    ax.set_yticklabels([str(v) for v in range(0, 41, 10)], color="black", fontsize=28)
    ax.yaxis.grid(True, linestyle=(0, (2, 4)), color="#D7D7DB", linewidth=1.25)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0, pad=12)
    ax.set_xticks([])
    ax.axhline(0, color="#C7C7CB", linewidth=1.1)

    fig.text(
        0.075,
        0.945,
        "MSQ (%)",
        fontsize=34,
        weight="bold",
        color="black",
        va="center",
    )
    fig.legend(
        handles=[
            Patch(facecolor=backgrounds[label], edgecolor="none", label=label)
            for label in legend_order
        ],
        loc="upper right",
        bbox_to_anchor=(0.985, 0.982),
        borderaxespad=0,
        frameon=False,
        ncol=3,
        fontsize=32,
        labelcolor="black",
        handlelength=1.45,
        handleheight=1.05,
        columnspacing=1.5,
    )

    fig.canvas.draw()
    sx = ax.bbox.width / (x_positions[-1] - x_positions[0] + 1.42)
    sy = ax.bbox.height / 45.5
    radius_x = 0.07
    radius_y = radius_x * sx / sy
    labels = []

    for i, row in enumerate(rows):
        model = row["model"]
        height = row["msq_percent"]
        icon_name, color = styles[model]
        category = (
            "Oracle"
            if row["mode"] == "Oracle"
            else ("Closed-source" if model in closed_models else "Open-source")
        )
        x = x_positions[i]

        ax.axvspan(
            x - step / 2,
            x + step / 2,
            facecolor=backgrounds[category],
            edgecolor="none",
            zorder=-2,
        )

        # Oracle keeps its category background, but uses the same DeepSeek color
        # as all other DeepSeek-V4-Flash-0731 experiments.
        rounded_bar(ax, x, height, 0.86, color, radius_x, radius_y)
        ax.text(
            x,
            height + 0.75,
            f"{height:.1f}",
            color="black",
            fontsize=30,
            ha="center",
            va="bottom",
            weight="bold" if i == 0 else "normal",
            clip_on=False,
        )

        icon = Image.open(ROOT / "icons" / f"{icon_name}.png").convert("RGBA")
        alpha_bbox = icon.getchannel("A").getbbox()
        if alpha_bbox:
            icon = icon.crop(alpha_bbox)
        icon.thumbnail((320, 320), Image.Resampling.LANCZOS)
        icon_box = AnnotationBbox(
            OffsetImage(np.asarray(icon), zoom=50 / max(icon.size)),
            (x, 0),
            xybox=(0, -58),
            xycoords="data",
            boxcoords="offset points",
            frameon=False,
            pad=0,
        )
        ax.add_artist(icon_box)

        label = model.replace("DeepSeek-V4-Flash-0731", "DeepSeek-V4-\nFlash-0731")
        display_mode = (
            row["mode"]
            .replace("Auto (Spec)", "Spec")
            .replace("Auto (Gen)", "Gen")
        )
        label += f"\n({display_mode})"
        labels.append(ax.annotate(
            label,
            (x, 0),
            xytext=(0, -112),
            textcoords="offset points",
            rotation=55,
            ha="right",
            va="top",
            fontsize=28,
            color="black",
            linespacing=1.05,
            annotation_clip=False,
        ))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for label in labels:
        bbox = label.get_window_extent(renderer)
        assert bbox.x0 >= 0 and bbox.y0 >= 0
        assert bbox.x1 <= fig.bbox.width and bbox.y1 <= fig.bbox.height

    for suffix in ("pdf", "svg", "png"):
        fig.savefig(
            ROOT / f"msq_ranking_MSE_Kit.{suffix}",
            dpi=300,
            facecolor="white",
            edgecolor="none",
            bbox_inches=None,
        )

    (ROOT / "provenance.json").write_text(json.dumps({
        "source": "msq_values.csv",
        "metric": "MSQ (percent)",
        "setting": "Eight Auto (Spec) runs and three additional DeepSeek modes",
        "order": "descending",
        "font_size_multiplier": 2,
        "icon_size_multiplier": 2,
        "icon_display_size": "50 px-equivalent display size after transparent-padding crop",
        "figsize_inches": [25.5, 10.8],
        "axes_rect": ax_rect,
        "legend_order": list(legend_order),
        "legend_font_matches_model_name": True,
        "value_label_weight": "bold only for the highest value; normal otherwise",
        "font_sizes_pt": {
            "global": 26,
            "axis_title": 34,
            "legend": 32,
            "ticks": 28,
            "bar_values": 30,
            "x_labels": 28,
        },
        "text_color": "black",
        "outer_spines": "hidden",
        "deepseek_experiment_color": styles["DeepSeek-V4-Flash-0731"][1],
        "background_categories": backgrounds,
        "rows": rows,
        "csv_sha256": hashlib.sha256((ROOT / "msq_values.csv").read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    plt.close(fig)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
