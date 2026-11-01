#!/usr/bin/env python3
"""Variable-depth, task-weighted Oracle category / benchmark domain distribution."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import fitz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import numpy as np


HERE = Path(__file__).resolve().parent
STEM = 'benchmark_oracle_nested_pie'
CATEGORIES = [
    ('no_delegation', 'No delegation', 'no_need_subagent/no_need_subagent.txt', '#A8CCE4', '#D7E9F4'),
    ('read_and_write', 'Read & Write', 'need_subagent/read_and_write/read_and_write.txt', '#D9B24C', '#F4E7B3'),
    ('writable', 'Write', 'need_subagent/writable/writable.txt', '#E9BDA3', '#F4DECE'),
    ('read_only', 'Read-Only', 'need_subagent/read_only/read_only.txt', '#ACD4BF', '#DCEDE2'),
]
TOP_LEVELS = [
    ('no_need', r'$\mathcal{D}_{\text{no-need}}$', 77, '#8FBBD7'),
    ('need', r'$\mathcal{D}_{\text{need}}$', 89, '#B9A8D3'),
]
DOMAINS = [
    ('learning_management_system', 'Learning Management System', 'Learning Mgmt.\nSystem'),
    ('enterprise_data_warehouse', 'Enterprise Data Warehouse', 'Enterprise Data\nWarehouse'),
    ('e-commerce', 'E-Commerce', 'E-Commerce'),
    ('stock_market', 'Stock Market', 'Stock Market'),
    ('video_platform', 'Video Platform', 'Video Platform'),
    ('railway_system', 'Railway System', 'Railway System'),
    ('academic_research', 'Academic Research', 'Academic Research'),
    ('food_and_catering', 'Food & Catering', 'Food & Catering'),
]


def write_csv(name, rows, fieldnames):
    with (HERE / name).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_data():
    source = HERE / 'source'
    with (source / 'domain/domain-cases.tsv').open() as handle:
        domain_rows = list(csv.DictReader(handle, delimiter='\t'))
    domains = {row['case_name']: row['domain'] for row in domain_rows}
    assert len(domain_rows) == len(domains) == 166
    assert set(domains.values()) == {item[0] for item in DOMAINS}
    assignments = {}
    category_counts = Counter()
    counts = Counter()
    for category, _, relative_path, *_ in CATEGORIES:
        names = (source / 'delegation' / relative_path).read_text().split()
        assert len(names) == len(set(names))
        for name in names:
            assert name not in assignments, name
            assert name in domains, name
            assignments[name] = category
            category_counts[category] += 1
            counts[category, domains[name]] += 1
    assert set(assignments) == set(domains)
    assert dict(category_counts) == {'no_delegation': 77, 'read_only': 22, 'writable': 23, 'read_and_write': 44}
    need = set((source / 'delegation/need_subagent/need_subagent.txt').read_text().split())
    assert need == {name for name, category in assignments.items() if category != 'no_delegation'}
    assert len(need) == 89
    with (source / 'delegation/need_subagent/domain_descriptive_statistics.tsv').open() as handle:
        stats = list(csv.DictReader(handle, delimiter='\t'))
    need_domain_counts = Counter(domains[name] for name in need)
    full_names = {key: full.replace('&', 'and') for key, full, _ in DOMAINS}
    for row in stats:
        if row['Domain'] == 'ALL Data':
            assert int(row['Task Number']) == len(need)
        else:
            domain = next(key for key, full in full_names.items() if full == row['Domain'])
            assert int(row['Task Number']) == need_domain_counts[domain]
    audit = json.loads((source / 'oracle_source_audit.json').read_text())
    assert {row['task'] for row in audit} == set(assignments)
    assert all(row['oracle_sha256'] == row['category_copy_sha256'] == row['tag_source_sha256'] for row in audit)
    provenance = json.loads((HERE / 'provenance.json').read_text())
    for row in provenance['sources']:
        assert hashlib.sha256((HERE / row['snapshot_path']).read_bytes()).hexdigest() == row['sha256']
    task_rows = [dict(task=name, domain=domains[name], oracle_category=assignments[name]) for name in sorted(domains)]
    write_csv('task_classification.csv', task_rows, ['task', 'domain', 'oracle_category'])
    aggregate = []
    for category, *_ in CATEGORIES:
        for domain, *_ in DOMAINS:
            count = counts[category, domain]
            aggregate.append(dict(oracle_category=category, domain=domain, task_count=count,
                                  percent_of_all_tasks=100*count/len(domains),
                                  percent_within_category=100*count/category_counts[category]))
    write_csv('category_domain_counts.csv', aggregate,
              ['oracle_category', 'domain', 'task_count', 'percent_of_all_tasks', 'percent_within_category'])
    validation = dict(total_tasks=166, need_delegation=89, no_delegation=77,
                      category_counts=dict(category_counts), domain_counts=dict(Counter(domains.values())),
                      no_delegation_domain_counts={domain: counts['no_delegation', domain] for domain, *_ in DOMAINS},
                      unique_task_assignment=True, domain_coverage_complete=True,
                      oracle_source_hashes_checked=166,
                      weighting='one equal weight per task, across variable-depth rings',
                      plotted_category_source='curated annotations/delegation task lists',
                      automatic_tag_disagreements=len(provenance['automatic_tag_disagreements']))
    return counts, category_counts, validation


def upright(angle):
    angle = (angle + 180) % 360 - 180
    if angle > 90:
        angle -= 180
    if angle < -90:
        angle += 180
    return angle


def polar(radius, angle):
    theta = np.deg2rad(angle)
    return radius*np.cos(theta), radius*np.sin(theta)


DOMAIN_COMPACT = {
    'learning_management_system': 'LMS',
    'enterprise_data_warehouse': 'EDW',
    'e-commerce': 'EC',
    'stock_market': 'SM',
    'video_platform': 'VP',
    'railway_system': 'RS',
    'academic_research': 'AR',
    'food_and_catering': 'FC',
}


TAG_FONT_SIZE = 64
TOP_LEVEL_FONT_SIZE = 60
# Small outer-ring sectors get their labels pulled outside the circle with a
# radial leader line instead of shrinking the in-slice text. The leading '_'
# entries nudge the label perpendicular to the leader (in data units) to
# avoid colliding with neighboring leader lines or the circle.
LEADER_LABELS = {
    ('no_delegation', 'railway_system'): .06,
    ('read_and_write', 'video_platform'): 0.0,
    ('read_and_write', 'food_and_catering'): 0.0,
    ('writable', 'food_and_catering'): 0.0,
    ('writable', 'video_platform'): 0.0,
    ('writable', 'e-commerce'): 0.0,
    ('read_only', 'food_and_catering'): 0.0,
    ('read_only', 'railway_system'): .05,
    ('read_only', 'stock_market'): 0.0,
}
LEADER_LABEL_RADIUS = 1.055
LEADER_LINE_WIDTH = 2.2


def domain_label(domain):
    """Use the requested compact abbreviation as a single-line tag."""
    return DOMAIN_COMPACT[domain]


def domain_font_size(angle_span):
    """Keep compact labels legible while fitting the smallest task sectors."""
    if angle_span < 3.0:
        return 28
    if angle_span < 5.0:
        return 36
    if angle_span < 8.0:
        return 48
    return TAG_FONT_SIZE


def domain_rotation(angle_span, middle_angle):
    """Keep labels aligned with the radial direction inside each sector."""
    return upright(middle_angle)


def draw_figure(counts, category_counts, validation):
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': 48,
        'mathtext.fontset': 'dejavusans',
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        'svg.fonttype': 'none',
    })
    fig, ax = plt.subplots(figsize=(14.8, 14.6), dpi=150)
    fig.subplots_adjust(left=.012, right=.988, bottom=.018, top=.982)
    ax.set_aspect('equal')
    ax.set_xlim(-1.17, 1.17)
    ax.set_ylim(-1.17, 1.17)
    ax.set_axis_off()
    top_radius = .37
    middle_radius = .67
    outer_radius = 1.0
    angle = 90.0
    sectors = []
    texts = []
    leader_lines = []
    top_patches, middle_patches, domain_patches = [], [], []
    category_by_key = {row[0]: row for row in CATEGORIES}
    total_tasks = 166

    # The center ring establishes the two top-level delegation branches.
    for key, label, count, color in TOP_LEVELS:
        end = angle + 360 * count / total_tasks
        patch = Wedge(
            (0, 0), top_radius, angle, end,
            facecolor=color, edgecolor='white', linewidth=1.25,
        )
        ax.add_patch(patch)
        top_patches.append((patch, count, key))
        middle = (angle + end) / 2
        label_position = polar(.225, middle)
        if key == 'need':
            # The extra count line makes the right-hand center label wider;
            # move it inward and slightly left within the D_need sector.
            label_position = (label_position[0] - .07, label_position[1] - .005)
        text = ax.text(
            *label_position,
            f'{label} {count}\n({100 * count / total_tasks:.1f}%)',
            ha='center', va='center', fontsize=48, linespacing=1.00,
            rotation=upright(middle), rotation_mode='anchor', color='black',
        )
        text.set_gid('top_' + key)
        texts.append(text)
        angle = end

    np.testing.assert_allclose(angle, 450, atol=1e-9)
    angle = 90.0

    def draw_domain_ring(category, start_angle, end_angle, inner_radius, outer_color):
        """Draw one branch's domain ring with all labels kept inside the wedges."""
        child_angle = start_angle
        for domain, full_name, display_name in DOMAINS:
            child_count = counts[category, domain]
            if not child_count:
                continue
            child_end = child_angle + 360 * child_count / total_tasks
            child_middle = (child_angle + child_end) / 2
            angle_span = child_end - child_angle
            patch = Wedge(
                (0, 0), outer_radius, child_angle, child_end,
                width=outer_radius - inner_radius,
                facecolor=outer_color, edgecolor='white', linewidth=1.0,
            )
            ax.add_patch(patch)
            domain_patches.append((patch, child_count, category, domain))
            use_leader = (category, domain) in LEADER_LABELS
            sectors.append(dict(
                oracle_category=category, domain=domain, task_count=child_count,
                theta_start=child_angle, theta_end=child_end,
                label_external=use_leader,
            ))
            label = domain_label(domain)
            if use_leader:
                # Tiny sector: pull the label outside the circle and connect
                # it to the slice with a short radial leader line.
                line_start = polar(outer_radius - .004, child_middle)
                line_end = polar(LEADER_LABEL_RADIUS + .008, child_middle)
                (line,) = ax.plot(
                    [line_start[0], line_end[0]], [line_start[1], line_end[1]],
                    color='black', linewidth=LEADER_LINE_WIDTH,
                    solid_capstyle='round', zorder=6,
                )
                line.set_gid(f'leader_{category}_{domain}')
                leader_lines.append(line)
                label_x, label_y = polar(LEADER_LABEL_RADIUS + .028, child_middle)
                theta = np.deg2rad(child_middle)
                label_x -= LEADER_LABELS[category, domain] * np.sin(theta)
                label_y += LEADER_LABELS[category, domain] * np.cos(theta)
                text = ax.text(
                    label_x, label_y,
                    label,
                    ha='center', va='center',
                    fontsize=TAG_FONT_SIZE,
                    linespacing=1.0,
                    color='black',
                    rotation=0,
                )
            else:
                text = ax.text(
                    *polar((inner_radius + outer_radius) / 2, child_middle),
                    label,
                    ha='center', va='center',
                    fontsize=domain_font_size(angle_span),
                    linespacing=1.0,
                    color='black',
                    rotation=domain_rotation(angle_span, child_middle),
                    rotation_mode='anchor',
                )
            text.set_gid(f'domain_{category}_{domain}')
            texts.append(text)
            child_angle = child_end
        np.testing.assert_allclose(child_angle, end_angle, atol=1e-9)

    # D_no-need has two levels: its domains start immediately outside the
    # center ring. D_need has three levels: mode ring, then domain ring.
    no_need_end = 90.0 + 360 * category_counts['no_delegation'] / total_tasks
    draw_domain_ring(
        'no_delegation', 90.0, no_need_end, top_radius,
        category_by_key['no_delegation'][4],
    )

    angle = no_need_end
    need_categories = [row for row in CATEGORIES if row[0] != 'no_delegation']
    for category, label, _, inner_color, outer_color in need_categories:
        count = category_counts[category]
        end = angle + 360 * count / total_tasks
        patch = Wedge(
            (0, 0), middle_radius, angle, end,
            width=middle_radius - top_radius,
            facecolor=inner_color, edgecolor='white', linewidth=1.25,
        )
        ax.add_patch(patch)
        middle_patches.append((patch, count, category))
        middle_angle = (angle + end) / 2
        display_label = {
            'read_and_write': f'Read &\nWrite ({count})',
            'writable': f'Write\n({count})',
            'read_only': f'Read-Only\n({count})',
        }[category]
        middle_rotation = 0
        middle_label_radius = {
            'read_and_write': .49,
            'writable': .50,
            'read_only': .51,
        }[category]
        middle_label_font_size = 52 if category == 'read_only' else TAG_FONT_SIZE
        text = ax.text(
            *polar(middle_label_radius, middle_angle), display_label,
            ha='center', va='center', fontsize=middle_label_font_size, linespacing=1.02,
            rotation=middle_rotation, rotation_mode='anchor', color='black',
        )
        text.set_gid('middle_' + category)
        texts.append(text)
        draw_domain_ring(category, angle, end, middle_radius, outer_color)
        angle = end

    np.testing.assert_allclose(angle, 450, atol=1e-9)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for text in texts:
        bb = text.get_window_extent(renderer)
        assert fig.bbox.contains(bb.x0, bb.y0) and fig.bbox.contains(bb.x1, bb.y1), text.get_text()
    assert len(top_patches) == 2 and len(middle_patches) == 3 and len(domain_patches) == 28
    assert len(leader_lines) == len(LEADER_LABELS)
    assert {line.get_gid() for line in leader_lines} == {f'leader_{category}_{domain}' for category, domain in LEADER_LABELS}
    assert {sector for sector in LEADER_LABELS} == {
        (row['oracle_category'], row['domain']) for row in sectors if row['label_external']
    }
    assert sum(count for _, count, _ in top_patches) == total_tasks
    assert sum(count for _, count, _ in middle_patches) == category_counts['read_only'] + category_counts['writable'] + category_counts['read_and_write']
    assert sum(count for _, count, _, _ in domain_patches) == total_tasks
    for patch, count, _ in top_patches:
        np.testing.assert_allclose(patch.theta2 - patch.theta1, 360 * count / total_tasks, atol=1e-9)
    for patch, count, _ in middle_patches:
        np.testing.assert_allclose(patch.theta2 - patch.theta1, 360 * count / total_tasks, atol=1e-9)
    for patch, count, category, domain in domain_patches:
        np.testing.assert_allclose(patch.theta2 - patch.theta1, 360 * count / total_tasks, atol=1e-9)
    assert len([row for row in domain_patches if row[2] == 'no_delegation']) == 8
    write_csv('plotted_sectors.csv', sectors,
              ['oracle_category', 'domain', 'task_count', 'theta_start', 'theta_end', 'label_external'])
    for extension in ['pdf', 'svg', 'png']:
        fig.savefig(HERE / f'{STEM}.{extension}', dpi=300, facecolor='white')
    plt.close(fig)
    with fitz.open(HERE / f'{STEM}.pdf') as doc:
        page = doc[0]
        svg_text = (HERE / f'{STEM}.svg').read_text()
        assert 'Read &amp;' in svg_text
        assert 'Read-' in svg_text
        assert 'Write' in svg_text
        for font in page.get_fonts(full=True):
            assert doc.extract_font(font[0])[3]
        page.get_pixmap(matrix=fitz.Matrix(1800 / page.rect.width, 1800 / page.rect.width),
                        alpha=False).save(HERE / f'{STEM}_preview.png')
    validation.update(
        top_level_sectors=2, middle_sectors=3, outer_sectors=28, plot_rings=3,
        no_delegation_domains_shown=8, outer_radius=outer_radius,
        middle_radius=middle_radius, top_radius=top_radius,
        all_angles_proportional_to_task_counts=True, text_clipped=False,
        fonts_embedded=True, top_label_font_pt=48,
        middle_label_font_pt=TAG_FONT_SIZE, outer_label_font_pt=TAG_FONT_SIZE,
        middle_label_font_sizes={'read_and_write': TAG_FONT_SIZE,
                                 'writable': TAG_FONT_SIZE,
                                 'read_only': 52},
        external_domain_labels=len(LEADER_LABELS),
        external_leader_label_sectors=sorted(f'{category}:{domain}' for category, domain in LEADER_LABELS),
        leader_label_radius=LEADER_LABEL_RADIUS,
        compact_domain_labels=True,
        domain_abbreviation_map=DOMAIN_COMPACT,
        top_level_count_labels=True,
        top_count_labels_inline=True,
        middle_count_labels=True,
        middle_category_colors={
            'read_and_write': category_by_key['read_and_write'][3],
            'writable': category_by_key['writable'][3],
            'read_only': category_by_key['read_only'][3],
        },
        compact_domain_font_sizes=sorted({
            domain_font_size(row['theta_end'] - row['theta_start'])
            for row in sectors if not row['label_external']
        } | {TAG_FONT_SIZE}),
        compact_domain_font_rule='64 pt normally; 48 pt for 5-8 degree sectors; 36 pt for 3-5 degree sectors; 28 pt below 3 degrees; leader-line labels always 64 pt',
        hierarchy='D_no-need -> domain; D_need -> read/write mode -> domain',
    )
    (HERE / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    print(json.dumps(validation, indent=2))


def checksums():
    # Skip hidden files and directories (.DS_Store, ._*, tool state) and caches.
    paths = sorted(path for path in HERE.rglob('*') if path.is_file() and path.name != 'SHA256SUMS'
                   and not any(part.startswith('.') or part == '__pycache__'
                               for part in path.relative_to(HERE).parts))
    (HERE/'SHA256SUMS').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest()
                                       +'  '+str(path.relative_to(HERE))+'\n' for path in paths))


if __name__ == '__main__':
    counts, category_counts, validation = load_data()
    draw_figure(counts, category_counts, validation)
    checksums()
