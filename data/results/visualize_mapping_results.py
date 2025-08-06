import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import matplotlib.patches as patches
from matplotlib.patches import Ellipse
from matplotlib_venn import venn2
import matplotlib.gridspec as gridspec

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Find all result directories
results_dir = Path("/home/ubuntu/biomapper/data/results")
mapping_dirs = [d for d in results_dir.iterdir() if d.is_dir()]

# Collect all overlap statistics
overlap_data = []
match_type_data = []

for mapping_dir in mapping_dirs:
    overlap_file = mapping_dir / "overlap_statistics.csv"
    match_type_file = mapping_dir / "match_type_breakdown.csv"
    
    if overlap_file.exists():
        df = pd.read_csv(overlap_file)
        if not df.empty:
            overlap_data.append(df)
    
    if match_type_file.exists():
        df = pd.read_csv(match_type_file)
        if not df.empty:
            df['mapping'] = mapping_dir.name
            match_type_data.append(df)

# Combine all data
overlap_df = pd.concat(overlap_data, ignore_index=True)
match_type_df = pd.concat(match_type_data, ignore_index=True)

# Create figure with multiple subplots
fig = plt.figure(figsize=(20, 16))
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

# 1. Jaccard Index comparison
ax1 = fig.add_subplot(gs[0, 0])
jaccard_data = overlap_df[['mapping_combo_id', 'jaccard_index']].sort_values('jaccard_index', ascending=True)
ax1.barh(jaccard_data['mapping_combo_id'], jaccard_data['jaccard_index'])
ax1.set_xlabel('Jaccard Index')
ax1.set_title('Jaccard Index by Mapping Pair')
ax1.set_xlim(0, max(0.3, jaccard_data['jaccard_index'].max() * 1.1))

# 2. Match rates comparison
ax2 = fig.add_subplot(gs[0, 1])
match_rates = overlap_df[['mapping_combo_id', 'source_match_rate', 'target_match_rate']].set_index('mapping_combo_id')
match_rates.plot(kind='bar', ax=ax2)
ax2.set_ylabel('Match Rate')
ax2.set_title('Source vs Target Match Rates')
ax2.legend(['Source', 'Target'])
ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')

# 3. Total rows and matched rows
ax3 = fig.add_subplot(gs[0, 2])
row_data = overlap_df[['mapping_combo_id', 'total_rows', 'matched_rows']].set_index('mapping_combo_id')
row_data.plot(kind='bar', ax=ax3, logy=True)
ax3.set_ylabel('Number of Rows (log scale)')
ax3.set_title('Total vs Matched Rows')
ax3.legend(['Total', 'Matched'])
ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right')

# 4. Match type breakdown stacked bar chart
ax4 = fig.add_subplot(gs[1, 0])
pivot_match_type = match_type_df.pivot(index='mapping', columns='match_type', values='count').fillna(0)
pivot_match_type.plot(kind='bar', stacked=True, ax=ax4)
ax4.set_ylabel('Number of Entities')
ax4.set_title('Match Type Distribution Across Mappings')
ax4.set_xticklabels(ax4.get_xticklabels(), rotation=45, ha='right')
ax4.legend(title='Match Type', bbox_to_anchor=(1.05, 1), loc='upper left')

# 5. Match type breakdown stacked bar chart
ax5 = fig.add_subplot(gs[1, 2])
filtered_match_type = match_type_df[~match_type_df['match_type'].isin(['source_only', 'target_only'])]
pivot_match_type = filtered_match_type.pivot(index='mapping', columns='match_type', values='count').fillna(0)
pivot_match_type.plot(kind='bar', stacked=True, ax=ax5)
ax5.set_ylabel('Number of Entities')
ax5.set_title('Match Type Distribution Across Mappings')
ax5.set_xticklabels(ax5.get_xticklabels(), rotation=45, ha='right')
ax5.legend(title='Match Type', bbox_to_anchor=(1.05, 1), loc='upper left')

# 6. Dice coefficient heatmap
ax6 = fig.add_subplot(gs[2, 0])
dice_pivot = overlap_df.pivot_table(index='source_name', columns='target_name', values='dice_coefficient')
sns.heatmap(dice_pivot, annot=True, fmt='.3f', ax=ax6, cmap='YlOrRd')
ax6.set_title('Dice Coefficient Heatmap')

# 7. Match success rate pie chart for overall statistics
ax7 = fig.add_subplot(gs[2, 1])
total_matched = overlap_df['matched_rows'].sum()
total_source_only = overlap_df['source_only_rows'].sum()
total_target_only = overlap_df['target_only_rows'].sum()
pie_data = [total_matched, total_source_only, total_target_only]
pie_labels = ['Matched', 'Source Only', 'Target Only']
ax7.pie(pie_data, labels=pie_labels, autopct='%1.1f%%', startangle=90)
ax7.set_title('Overall Match Distribution')

# 8. Mapping pair size scatter plot
ax8 = fig.add_subplot(gs[2, 2])
ax8.scatter(overlap_df['source_only_rows'] + overlap_df['matched_rows'], 
           overlap_df['target_only_rows'] + overlap_df['matched_rows'],
           s=overlap_df['matched_rows']*2, alpha=0.6)
for idx, row in overlap_df.iterrows():
    ax8.annotate(row['mapping_combo_id'], 
                (row['source_only_rows'] + row['matched_rows'], 
                 row['target_only_rows'] + row['matched_rows']),
                fontsize=8, ha='center')
ax8.set_xlabel('Source Dataset Size')
ax8.set_ylabel('Target Dataset Size')
ax8.set_title('Dataset Sizes (bubble size = matched rows)')

plt.suptitle('Biomapper Results Meta-Analysis', fontsize=16, y=0.98)
plt.tight_layout()
plt.savefig(results_dir / 'meta_analysis_overview.png', dpi=300, bbox_inches='tight')
plt.close()

# Create combined Venn diagram figure
fig_venn = plt.figure(figsize=(20, 12))
n_mappings = len(mapping_dirs)
n_cols = 3
n_rows = (n_mappings + n_cols - 1) // n_cols

for idx, mapping_dir in enumerate(mapping_dirs):
    venn_img = mapping_dir / "venn_diagram.png"
    if venn_img.exists():
        ax = fig_venn.add_subplot(n_rows, n_cols, idx + 1)
        img = plt.imread(venn_img)
        ax.imshow(img)
        ax.axis('off')
        ax.set_title(mapping_dir.name, fontsize=12)

plt.suptitle('All Venn Diagrams', fontsize=16)
plt.tight_layout()
plt.savefig(results_dir / 'all_venn_diagrams.png', dpi=300, bbox_inches='tight')
plt.close()

# Create additional visualizations
# 1. Match type proportions
fig_match_types = plt.figure(figsize=(15, 8))

# Normalize match types to percentages
match_type_pivot = match_type_df.pivot(index='mapping', columns='match_type', values='count').fillna(0)
match_type_pct = match_type_pivot.div(match_type_pivot.sum(axis=1), axis=0) * 100

ax_pct = fig_match_types.add_subplot(121)
match_type_pct.plot(kind='bar', stacked=True, ax=ax_pct)
ax_pct.set_ylabel('Percentage (%)')
ax_pct.set_title('Match Type Distribution (Percentage)')
ax_pct.set_xticklabels(ax_pct.get_xticklabels(), rotation=45, ha='right')
ax_pct.legend(title='Match Type', bbox_to_anchor=(1.05, 1), loc='upper left')

# 2. Match efficiency radar chart
ax_radar = fig_match_types.add_subplot(122, projection='polar')
categories = overlap_df['mapping_combo_id'].tolist()
values = overlap_df['jaccard_index'].tolist()

angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
values += values[:1]  # Complete the circle
angles += angles[:1]

ax_radar.plot(angles, values, 'o-', linewidth=2)
ax_radar.fill(angles, values, alpha=0.25)
ax_radar.set_xticks(angles[:-1])
ax_radar.set_xticklabels(categories, size=8)
ax_radar.set_ylim(0, max(0.3, max(values) * 1.1))
ax_radar.set_title('Jaccard Index Radar Chart', y=1.08)
ax_radar.grid(True)

plt.tight_layout()
plt.savefig(results_dir / 'match_type_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# Generate summary statistics report
with open(results_dir / 'meta_analysis_summary.txt', 'w') as f:
    f.write("BIOMAPPER RESULTS META-ANALYSIS SUMMARY\n")
    f.write("=" * 50 + "\n\n")
    
    f.write("Overall Statistics:\n")
    f.write(f"Total mappings analyzed: {len(overlap_df)}\n")
    f.write(f"Total entities processed: {overlap_df['total_rows'].sum():,}\n")
    f.write(f"Total matches found: {overlap_df['matched_rows'].sum():,}\n")
    f.write(f"Average match rate: {(overlap_df['matched_rows'].sum() / overlap_df['total_rows'].sum() * 100):.2f}%\n\n")
    
    f.write("Top 5 mappings by Jaccard Index:\n")
    top_jaccard = overlap_df.nlargest(5, 'jaccard_index')[['mapping_combo_id', 'jaccard_index']]
    for _, row in top_jaccard.iterrows():
        f.write(f"  {row['mapping_combo_id']}: {row['jaccard_index']:.4f}\n")
    
    f.write("\nTop 5 mappings by number of matches:\n")
    top_matches = overlap_df.nlargest(5, 'matched_rows')[['mapping_combo_id', 'matched_rows']]
    for _, row in top_matches.iterrows():
        f.write(f"  {row['mapping_combo_id']}: {row['matched_rows']:,} matches\n")
    
    f.write("\nMatch Type Summary:\n")
    total_by_type = match_type_df.groupby('match_type')['count'].sum()
    for match_type, count in total_by_type.items():
        f.write(f"  {match_type}: {count:,} ({count/total_by_type.sum()*100:.1f}%)\n")

print("Visualizations created successfully!")
print(f"Generated files:")
print(f"  - {results_dir / 'meta_analysis_overview.png'}")
print(f"  - {results_dir / 'all_venn_diagrams.png'}")
print(f"  - {results_dir / 'match_type_analysis.png'}")
print(f"  - {results_dir / 'meta_analysis_summary.txt'}")