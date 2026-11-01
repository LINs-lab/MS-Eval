#!/usr/bin/env python3
"""Reproduce both MAD minus SA plots from the frozen Pareto summary."""
from pathlib import Path
import csv
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from matplotlib.transforms import Bbox
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
SETTINGS = [
    ('deepseek-auto-gen', 'V4-F-Gen', 'DeepSeek-V4-Flash-0731-Gen', 'Gen'),
    ('deepseek-auto-spec', 'V4-F-Spec', 'DeepSeek-V4-Flash-0731-Spec', 'Spec'),
    ('deepseek-plan-1st', 'V4-F-Plan1st', 'DeepSeek-V4-Flash-0731-Plan1st', 'Plan-1st'),
    ('deepseek-oracle', 'V4-F-Oracle', 'DeepSeek-V4-Flash-0731-Oracle', 'Oracle'),
    ('claude-auto-spec', 'Sonnet-5-Spec', 'Claude-Sonnet-5-Spec', None),
    ('gpt-5.6-sol-auto-spec', '5.6-Sol-Spec', 'GPT-5.6-Sol-Spec', None),
    ('qwen-3.8-max-auto-spec', '3.8-Max-Spec', 'Qwen-3.8-Max-Spec', None),
    ('glm-5.3-auto-spec', '5.3-Spec', 'GLM-5.3-Spec', None),
    ('kimi-k3-auto-spec', 'K3-Spec', 'Kimi-K3-Spec', None),
    ('minimax-m3-auto-spec', 'M3-Spec', 'Minimax-M3-Spec', None),
    ('glm-5.3-flash-auto-spec', '5.3-F-Spec', 'GLM-5.3-Flash-Spec', None),
]
STYLES = json.loads((ROOT / 'model_styles.json').read_text())
ICON_PT = 25
LABEL_PT = 15


def read_deltas():
    with (ROOT / 'source_summary.csv').open(newline='') as f:
        source = list(csv.DictReader(f))
    assert len(source) == 19
    assert len({r['experiment'] for r in source}) == 19
    for r in source:
        assert r['scope'] == 'all'
        assert int(r['n_total']) == int(r['n_metric_rows']) == 166
        assert math.isclose(float(r['success_rate']), int(r['n_success']) / 166, abs_tol=1e-10)
    experiments = {r['experiment']: r for r in source}
    baselines = {r['model']: r for r in source if r['mode'] == 'SA'}
    rows = []
    for experiment, short, tag, mode_label in SETTINGS:
        mad = experiments[experiment]
        sa = baselines[mad['model']]
        # Use the integer success counts to avoid rounding noise at zero.
        p_mad = 100 * int(mad['n_success']) / int(mad['n_total'])
        p_sa = 100 * int(sa['n_success']) / int(sa['n_total'])
        rows.append(dict(
            setting=mad['model'] + (f' ({mode_label})' if mode_label else ''),
            abbreviation=short, tag=tag, model=mad['model'], mad_mode=mad['mode'],
            mad_experiment=experiment, sa_experiment=sa['experiment'], n_tasks=166,
            mad_success_rate_percent=p_mad, sa_success_rate_percent=p_sa,
            mad_mean_cost_usd=float(mad['mean_cost_usd']),
            sa_mean_cost_usd=float(sa['mean_cost_usd']),
            mad_mean_csteps=float(mad['mean_critical_steps']),
            sa_mean_csteps=float(sa['mean_critical_steps']),
            delta_performance_pp=p_mad-p_sa,
            delta_cost_usd=float(mad['mean_cost_usd'])-float(sa['mean_cost_usd']),
            delta_csteps=float(mad['mean_critical_steps'])-float(sa['mean_critical_steps']),
        ))
    return rows


def signed(value, digits=2):
    return f'{value:+.{digits}f}' if abs(value) > 1e-10 else f'{0:.{digits}f}'


def write_tables(rows):
    with (ROOT / 'relationship_data.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    headers = ['Settings', 'Abbreviation', 'Delta Performance (MAD-SA, pp)',
               'Delta Cost (MAD-SA, USD)', 'Delta Csteps (MAD-SA)']
    lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---']*5) + ' |']
    compact = []
    for r in rows:
        values = [r['setting'], r['abbreviation'], signed(r['delta_performance_pp']),
                  signed(r['delta_cost_usd'], 4), signed(r['delta_csteps'])]
        lines.append('| ' + ' | '.join(values) + ' |')
        compact.append(values)
    (ROOT / 'delta_table.md').write_text('\n'.join(lines) + '\n')
    with (ROOT / 'delta_table.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(compact)


def area(a, b):
    intersection = Bbox.intersection(a, b)
    return 0 if intersection is None else intersection.width * intersection.height


def label_layout(fig, ax, labels, icons, captions, rows):
    """Move only text; icons remain centered at the exact measured coordinates."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = ax.get_window_extent(renderer).padded(-5)
    obstacles = [icon.get_window_extent(renderer).padded(4) for icon in icons]
    obstacles += [t.get_window_extent(renderer).padded(5) for t in captions]
    placed = []
    offsets = {}
    # Long labels are harder to place, so assign them first.
    order = sorted(range(len(labels)), key=lambda i: -len(rows[i]['tag']))
    for i in order:
        ann = labels[i]
        best = None
        for dy in [0, 18, -18, 30, -30, 44, -44, 60, -60]:
            for dx in [20, -20, 35, -35, 55, -55, 80, -80]:
                ha = 'left' if dx > 0 else 'right'
                ann.set_position((dx, dy))
                ann.set_ha(ha)
                ann.update_positions(renderer)
                box = Text.get_window_extent(ann, renderer).expanded(1.035, 1.22)
                outside = max(0, box.width*box.height - area(box, bounds))
                collision = sum(area(box, b) for b in obstacles + placed)
                score = 10000*(outside+collision) + math.hypot(dx, dy) + (3 if dx < 0 else 0)
                if best is None or score < best[0]:
                    best = (score, dx, dy, ha, box)
        _, dx, dy, ha, box = best
        ann.set_position((dx, dy))
        ann.set_ha(ha)
        placed.append(box)
        offsets[rows[i]['tag']] = [dx, dy]
        if dy == 0 and abs(dx) == 20:
            ann.arrow_patch.set_visible(False)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [Text.get_window_extent(a, renderer) for a in labels]
    icon_boxes = [i.get_window_extent(renderer) for i in icons]
    overlaps = [(rows[i]['tag'], rows[j]['tag'])
                for i, box in enumerate(boxes) for j in range(i) if area(box, boxes[j]) > 0]
    covered = [(rows[i]['tag'], rows[j]['tag'])
               for i, box in enumerate(boxes) for j, point in enumerate(icon_boxes) if area(box, point) > 0]
    clipped = [rows[i]['tag'] for i, box in enumerate(boxes+[])
               if area(box, bounds) < box.width*box.height-1]
    icon_overlaps = [(rows[i]['tag'], rows[j]['tag'])
                     for i, box in enumerate(icon_boxes) for j in range(i) if area(box, icon_boxes[j]) > 0]
    assert not overlaps, overlaps
    assert not covered, covered
    assert not clipped, clipped
    assert not icon_overlaps, icon_overlaps
    return dict(label_offsets_pt=offsets, label_overlaps=overlaps,
                label_icon_overlaps=covered, clipped_labels=clipped, icon_overlaps=icon_overlaps)


def draw(rows, kind):
    cost = kind == 'cost'
    key = 'delta_cost_usd' if cost else 'delta_csteps'
    fig, ax = plt.subplots(figsize=(10.2, 10.0), dpi=150)
    fig.subplots_adjust(left=.125, right=.975, bottom=.115, top=.96)
    ax.set_ylim(-26, 16)
    ax.set_yticks([-25, -20, -15, -10, -5, 0, 5, 10, 15])
    ax.set_ylabel(r'$\Delta$ Average Success Rate per task (%)', fontsize=25, labelpad=12)
    if cost:
        ax.set_xscale('symlog', base=10, linthresh=.1, linscale=1)
        ax.set_xlim(-6, 6)
        ax.xaxis.set_major_locator(FixedLocator([-5, -1, -.1, 0, .1, 1, 5]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlabel(r'$\Delta$ Average Cost per task (\$, log scale)', fontsize=25, labelpad=14)
    else:
        ax.set_xlim(-12, 14)
        ax.set_xticks([-10, -5, 0, 5, 10])
        ax.set_xlabel(r'$\Delta$ Average Csteps per task', fontsize=25, labelpad=14)
    formatter = FuncFormatter(lambda v, _: '0' if v == 0 else f'{v:+g}')
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    for left, right, bottom, top, color in [
        (xmin, 0, 0, ymax, '#ECF6EF'), (0, xmax, 0, ymax, '#FFF6E7'),
        (xmin, 0, ymin, 0, '#EDF3FA'), (0, xmax, ymin, 0, '#FBEDEE'),
    ]:
        ax.add_patch(Rectangle((left, bottom), right-left, top-bottom,
                               facecolor=color, edgecolor='none', zorder=0))
    ax.set_axisbelow(True)
    ax.grid(color='#D9DDE1', linewidth=.7, linestyle=(0, (2, 4)), alpha=.7)
    ax.axhline(0, color='#6E747D', lw=1.4, zorder=2)
    ax.axvline(0, color='#6E747D', lw=1.4, zorder=2)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, pad=9, labelsize=20)
    resource_less = 'Lower cost' if cost else 'Fewer steps'
    resource_more = 'Higher cost' if cost else 'More steps'
    captions = []
    for x, y, ha, va, text, color in [
        (.025, .975, 'left', 'top', 'Higher success\n'+resource_less, '#245E43'),
        (.975, .975, 'right', 'top', 'Higher success\n'+resource_more, '#805D18'),
        (.025, .025, 'left', 'bottom', 'Lower success\n'+resource_less, '#2F587A'),
        (.975, .025, 'right', 'bottom', 'Lower success\n'+resource_more, '#853F4D'),
    ]:
        captions.append(ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
                                color=color, fontsize=22, linespacing=1.15, zorder=3,
                                fontweight='normal'))
    labels, icons = [], []
    for r in rows:
        icon_name, color = STYLES[r['model']]
        icon = Image.open(ROOT / 'icons' / f'{icon_name}.png').convert('RGBA')
        icon = icon.crop(icon.getchannel('A').getbbox())
        icon.thumbnail((256, 256), Image.Resampling.LANCZOS)
        point = (r[key], r['delta_performance_pp'])
        artist = AnnotationBbox(OffsetImage(np.asarray(icon), zoom=ICON_PT/max(icon.size)),
                                point, frameon=False, pad=0, zorder=5)
        ax.add_artist(artist)
        icons.append(artist)
        labels.append(ax.annotate(r['tag'], point, xytext=(20, 0),
                                  textcoords='offset points', ha='left', va='center',
                                  color='black', fontsize=LABEL_PT, zorder=6,
                                  arrowprops=dict(arrowstyle='-', color='#222222', alpha=.65,
                                                  lw=.8, shrinkA=4, shrinkB=15)))
    audit = label_layout(fig, ax, labels, icons, captions, rows)
    audit['points'] = [dict(abbreviation=r['abbreviation'], x=r[key], y=r['delta_performance_pp']) for r in rows]
    out = ROOT / f'perform_{kind}'
    out.mkdir(exist_ok=True)
    stem = out / f'delta_performance_{kind}'
    for suffix in ['png', 'pdf', 'svg']:
        fig.savefig(stem.with_suffix('.'+suffix), dpi=300, facecolor='white')
    fig.savefig(out / 'preview.png', dpi=120, facecolor='white')
    plt.close(fig)
    return audit


def combine_figures():
    """Create a compact left-cost/right-efficiency composite in three formats."""
    from PIL import ImageOps
    combine_dir = ROOT / 'combine'
    combine_dir.mkdir(exist_ok=True)
    left = Image.open(ROOT / 'perform_cost' / 'delta_performance_cost.png').convert('RGB')
    right = Image.open(ROOT / 'perform_efficiency' / 'delta_performance_efficiency.png').convert('RGB')
    gap = 36
    canvas = Image.new('RGB', (left.width + right.width + gap, max(left.height, right.height)), 'white')
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width + gap, 0))
    canvas.save(combine_dir / 'performance_cost_efficiency.png', dpi=(300, 300))
    canvas.save(combine_dir / 'performance_cost_efficiency.pdf', resolution=300)
    # A vector container keeps the composite easy to place in LaTeX while
    # preserving the exact exported panel appearance.
    fig, axes = plt.subplots(1, 2, figsize=(20.4, 10.0), dpi=150)
    for ax, image in zip(axes, [left, right]):
        ax.imshow(image)
        ax.axis('off')
    fig.subplots_adjust(0, 0, 1, 1, wspace=.015)
    fig.savefig(combine_dir / 'performance_cost_efficiency.svg', facecolor='white',
                bbox_inches='tight', pad_inches=0)
    plt.close(fig)


def ranks(values):
    return np.array([sum(v < x for v in values) + (sum(v == x for v in values)+1)/2 for x in values])


def main():
    font_paths = list(Path('/usr/share/fonts/urw-base35').glob('NimbusRoman*.otf'))
    for font in font_paths:
        font_manager.fontManager.addfont(str(font))
    available = {f.name for f in font_manager.fontManager.ttflist}
    font_family = next(f for f in ['Times New Roman', 'Nimbus Roman', 'DejaVu Serif'] if f in available)
    plt.rcParams.update({'font.family':font_family, 'font.size':18, 'mathtext.fontset':'stix',
                         'pdf.fonttype':42, 'ps.fonttype':42, 'svg.fonttype':'none',
                         'axes.unicode_minus':False})
    rows = read_deltas()
    write_tables(rows)
    audit = {kind:draw(rows, kind) for kind in ['efficiency', 'cost']}
    combine_figures()
    correlations = {}
    y = np.array([r['delta_performance_pp'] for r in rows])
    for key in ['delta_csteps', 'delta_cost_usd']:
        x = np.array([r[key] for r in rows])
        correlations[key] = dict(n=11, pearson_r=float(np.corrcoef(x, y)[0, 1]),
                                 spearman_rho=float(np.corrcoef(ranks(x), ranks(y))[0, 1]))
    (ROOT / 'correlations.json').write_text(json.dumps(correlations, indent=2)+'\n')
    provenance = dict(
        source='source_summary.csv',
        source_sha256=hashlib.sha256((ROOT/'source_summary.csv').read_bytes()).hexdigest(),
        styles_source='../msq_ranking/draw_msq.py', icons_source='../msq_ranking/icons',
        data_scope='All 166 tasks per experiment; mean cost and mean critical steps.',
        delta_definition='MAD minus same-model SA; success-rate differences in percentage points.',
        default_mad_mode='Auto (Spec)', oracle_mode='Oracle (oracle-spec, frozen Pareto snapshot)',
        cost_axis=dict(scale='symlog', base=10, linthresh_usd=.1, linscale=1),
        table_header_correction='The duplicate last Delta Performance column is interpreted as Delta Csteps.',
        figure_inches=[10.2, 10.0], png_dpi=300, font=font_family,
        tag_style='black full model names', efficiency_linear_fit=False,
        axis_titles={
            'y': 'Delta Average Success Rate per task (%)',
            'cost_x': 'Delta Average Cost per task ($, log scale)',
            'efficiency_x': 'Delta Average Csteps per task',
        },
        label_fontsize_pt=LABEL_PT, icon_max_dimension_pt=ICON_PT,
        matplotlib_version=matplotlib.__version__, composite='combine/performance_cost_efficiency.*',
        quadrant_annotation_fontsize_pt=20, tick_fontsize_pt=20, layout=audit)
    (ROOT / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print((ROOT / 'delta_table.md').read_text())
    print(json.dumps(correlations, indent=2))
    print('All 11 points per figure exported; label and icon layout checks passed.')


if __name__ == '__main__':
    main()
