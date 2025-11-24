"""
P-TREE STRUCTURE VISUALIZATION - TREE DIAGRAMS

Parses and visualizes the actual P-Tree structure from saved tree files.
Creates hierarchical tree diagrams showing splits, thresholds, and leaf nodes.

Run this AFTER 1_ptree_analysis.R has completed and saved tree structure files.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path
import numpy as np

print("=" * 80)
print("P-TREE STRUCTURE VISUALIZATION")
print("=" * 80)

# Characteristic name mapping
CHAR_NAMES = {
    0: 'SUE', 1: 'DOLVOL', 2: 'BM_IA', 3: 'ME_IA', 4: 'ROE', 5: 'ZEROTRADE',
    6: 'MOM1M', 7: 'MOM6M', 8: 'MOM12M', 9: 'MOM36M', 10: 'MOM60M',
    11: 'ME', 12: 'BM', 13: 'EP', 14: 'CFP', 15: 'SP', 16: 'ROA',
    17: 'GP', 18: 'OP', 19: 'PM', 20: 'SALES_GR', 21: 'AGR',
    22: 'CAPEX', 23: 'NI', 24: 'TURN', 25: 'SVAR', 26: 'STD_TURN',
    27: 'STD_DOLVOL', 28: 'ATO', 29: 'DE', 30: 'AQ', 31: 'CFOA', 32: 'PA'
}

def parse_tree_structure(tree_file):
    """Parse P-Tree structure file and extract splits."""
    if not tree_file.exists():
        return None

    with open(tree_file, 'r') as f:
        lines = f.readlines()

    if len(lines) == 0:
        return None

    # First line is number of nodes
    num_nodes = int(lines[0].strip())

    nodes = []
    splits = []

    # Parse each line
    for i, line in enumerate(lines[1:], 1):
        parts = line.strip().split()
        if len(parts) >= 3:
            # Extract split information
            # Format varies by PTree version, but typically:
            # node_id characteristic_index threshold left_child right_child
            try:
                node_id = i - 1
                char_idx = int(float(parts[0])) if parts[0] != '-1' else -1
                threshold = float(parts[1]) if len(parts) > 1 else 0

                nodes.append({
                    'id': node_id,
                    'char': char_idx,
                    'threshold': threshold,
                    'is_leaf': char_idx == -1
                })

                if char_idx >= 0:
                    char_name = CHAR_NAMES.get(char_idx, f'Char_{char_idx}')
                    splits.append({
                        'depth': 0,  # Will calculate later
                        'char': char_name,
                        'threshold': threshold
                    })
            except (ValueError, IndexError):
                continue

    return {'num_nodes': num_nodes, 'nodes': nodes, 'splits': splits}

def calculate_tree_layout(nodes, max_width=10):
    """Calculate positions for tree nodes in a hierarchical layout."""
    if not nodes:
        return {}

    # Build tree structure
    children = {}
    for node in nodes:
        node_id = node['id']
        children[node_id] = []

    # For simplicity, assume binary tree structure
    # Node 0 is root, then alternating left/right children
    for i, node in enumerate(nodes[1:], 1):
        parent = (i - 1) // 2
        children[parent].append(i)

    # Calculate positions using level-order traversal
    positions = {}
    level_nodes = {0: [0]}  # Level -> list of node ids

    # Assign levels
    queue = [(0, 0)]  # (node_id, level)
    max_level = 0
    while queue:
        node_id, level = queue.pop(0)
        if level not in level_nodes:
            level_nodes[level] = []
        if node_id not in level_nodes[level]:
            level_nodes[level].append(node_id)
        max_level = max(max_level, level)

        for child in children.get(node_id, []):
            if child < len(nodes):
                queue.append((child, level + 1))

    # Calculate x positions for each level
    for level, node_ids in level_nodes.items():
        n_nodes = len(node_ids)
        if n_nodes == 1:
            positions[node_ids[0]] = (max_width / 2, max_level - level)
        else:
            spacing = max_width / (n_nodes + 1)
            for i, node_id in enumerate(node_ids):
                x = spacing * (i + 1)
                y = max_level - level
                positions[node_id] = (x, y)

    return positions, children

def draw_tree_diagram(tree_data, scenario_name, output_path):
    """Create a hierarchical tree diagram showing the structure."""
    if tree_data is None or len(tree_data['nodes']) == 0:
        print(f"  [SKIP] No valid tree structure for {scenario_name}")
        return

    nodes = tree_data['nodes']

    # Calculate layout
    positions, children = calculate_tree_layout(nodes)

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_aspect('equal')

    # Draw edges first
    for parent_id, child_ids in children.items():
        if parent_id not in positions:
            continue
        px, py = positions[parent_id]

        for i, child_id in enumerate(child_ids):
            if child_id not in positions or child_id >= len(nodes):
                continue
            cx, cy = positions[child_id]

            # Draw arrow
            arrow = FancyArrowPatch(
                (px, py - 0.3), (cx, cy + 0.3),
                arrowstyle='->', mutation_scale=20, linewidth=2,
                color='gray', alpha=0.6
            )
            ax.add_patch(arrow)

            # Add label on edge (Left/Right)
            mid_x, mid_y = (px + cx) / 2, (py + cy) / 2
            label = 'Left' if i == 0 else 'Right'
            ax.text(mid_x, mid_y, label, fontsize=8, ha='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

    # Draw nodes
    for node_id, node in enumerate(nodes):
        if node_id not in positions:
            continue

        x, y = positions[node_id]

        if node['is_leaf']:
            # Leaf node - green box
            box = FancyBboxPatch(
                (x - 0.8, y - 0.3), 1.6, 0.6,
                boxstyle="round,pad=0.1",
                facecolor='lightgreen', edgecolor='darkgreen',
                linewidth=2, alpha=0.8
            )
            ax.add_patch(box)
            ax.text(x, y, f'Leaf {node_id}', ha='center', va='center',
                   fontsize=10, fontweight='bold')
        else:
            # Split node - blue box
            char_name = CHAR_NAMES.get(node['char'], f"Char{node['char']}")
            threshold = node['threshold']

            box = FancyBboxPatch(
                (x - 1.0, y - 0.4), 2.0, 0.8,
                boxstyle="round,pad=0.1",
                facecolor='lightblue', edgecolor='darkblue',
                linewidth=2, alpha=0.8
            )
            ax.add_patch(box)

            # Node text
            text = f'{char_name}\n≤ {threshold:.2f}'
            ax.text(x, y, text, ha='center', va='center',
                   fontsize=9, fontweight='bold')

    # Set axis limits and remove ticks
    if positions:
        xs = [p[0] for p in positions.values()]
        ys = [p[1] for p in positions.values()]
        ax.set_xlim(min(xs) - 2, max(xs) + 2)
        ax.set_ylim(min(ys) - 1, max(ys) + 1)

    ax.axis('off')

    # Title
    ax.set_title(f'P-Tree Structure: {scenario_name}\n' +
                f'{tree_data["num_nodes"]} Nodes Total',
                fontsize=14, fontweight='bold', pad=20)

    # Legend
    legend_elements = [
        mpatches.Rectangle((0, 0), 1, 1, facecolor='lightblue', edgecolor='darkblue',
                          linewidth=2, label='Split Node'),
        mpatches.Rectangle((0, 0), 1, 1, facecolor='lightgreen', edgecolor='darkgreen',
                          linewidth=2, label='Leaf Node')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  [OK] Saved: {output_path.name}")

    return True

# =============================================================================
# LOAD AND VISUALIZE TREE STRUCTURES
# =============================================================================

print("\n[1] Loading tree structures from P-Tree models...")

results_dir = Path('../../results/ptree_34chars')
vis_dir = results_dir / 'visualizations'
vis_dir.mkdir(exist_ok=True, parents=True)

scenarios = {
    'Scenario A: Full Sample': results_dir / 'scenario_a_full' / 'ptree_structure.txt',
    'Scenario B: Time Split': results_dir / 'scenario_b_split' / 'ptree_structure.txt',
    'Scenario C: Reverse Split': results_dir / 'scenario_c_reverse' / 'ptree_structure.txt'
}

for scenario_name, tree_file in scenarios.items():
    print(f"\n  {scenario_name}")

    if not tree_file.exists():
        print(f"    [WARNING] Tree structure file not found: {tree_file.name}")
        print(f"    Run 1_ptree_analysis.R first to generate tree structures")
        continue

    # Parse tree
    tree_data = parse_tree_structure(tree_file)

    if tree_data is None:
        print(f"    [ERROR] Could not parse tree structure")
        continue

    print(f"    Nodes: {tree_data['num_nodes']}, Splits: {len(tree_data['splits'])}")

    # Visualize tree diagram
    output_name = scenario_name.lower().replace(':', '').replace(' ', '_') + '_tree_diagram.png'
    output_path = vis_dir / output_name

    draw_tree_diagram(tree_data, scenario_name, output_path)


# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("TREE STRUCTURE VISUALIZATION COMPLETE")
print("=" * 80)
print(f"\nTree diagrams saved to: {vis_dir}")
print("\nGenerated hierarchical tree diagrams showing:")
print("  - Split nodes (blue boxes) with characteristic and threshold")
print("  - Leaf nodes (green boxes) representing portfolios")
print("  - Tree structure with left/right branches")
print()
