import base64
import contextlib
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
path = root / 'UKDA-6970-stata/case_study.ipynb'
notebook = json.loads(path.read_text(encoding='utf-8'))
original_cells = notebook['cells'][:]

missing_code = '''# Compare missing income within each group (unweighted respondents).
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

for ax, group, title in zip(
    axes, ['Ethnicity', 'Party'], ['By ethnic group', 'By party identification']
):
    chart_data = missing_summary(analysis, group).sort_values('Missing_percent')
    ax.barh(chart_data.index, chart_data['Missing_percent'], color='#41699b', height=0.6)
    for i, row in enumerate(chart_data.itertuples()):
        ax.text(row.Missing_percent + 0.8, i,
                f'{row.Missing_percent:.1f}%  ({row.Missing_income}/{row.Respondents})',
                va='center', fontsize=10)
    ax.set_xlim(0, 68)
    ax.set_xticks([0, 10, 20, 30, 40, 50, 60])
    ax.set_xlabel('Respondents with missing income (%)')
    ax.set_title(title, loc='left', fontsize=12, fontweight='bold')
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.grid(axis='x', alpha=0.15)
    ax.set_axisbelow(True)

fig.suptitle('Missing income is uneven across respondent groups',
             x=0.03, ha='left', fontsize=16, fontweight='bold')
fig.text(0.03, 0.03,
         'Labels show missing / total respondents in each group. Counts and percentages are unweighted.\\n'
         'The party panel includes valid party responses, including None/No; refused and unknown party responses are excluded.',
         fontsize=9, color='#485362')
fig.tight_layout(rect=[0, 0.13, 1, 0.92], w_pad=3)
plt.show()
'''

sample_code = '''# Show the sample available for the income–party analysis.
sample_counts = [len(complete), len(analysis) - len(complete)]
sample_labels = ['Included: valid income and party', 'Excluded: missing income and/or party']

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.barh(sample_labels, sample_counts, color=['#41699b', '#bbc1cb'], height=0.55)
ax.invert_yaxis()
for i, count in enumerate(sample_counts):
    ax.text(count + 35, i, f'{count:,} ({count / len(analysis):.1%})',
            va='center', fontsize=12)
ax.set_xlim(0, max(sample_counts) * 1.3)
ax.set_xlabel('Number of respondents (unweighted)')
ax.set_title(f'{len(complete) / len(analysis):.1%} of respondents enter the main analysis',
             loc='left', fontsize=16, fontweight='bold', pad=18)
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.grid(axis='x', alpha=0.15)
ax.set_axisbelow(True)
fig.text(0.03, 0.03,
         f'Original sample: {len(analysis):,}. Each respondent is counted once. None/No party identification is retained.\\n'
         'Excluding incomplete responses does not remove the risk of bias from missing income.',
         fontsize=9, color='#485362')
fig.tight_layout(rect=[0, 0.15, 1, 1])
plt.show()
'''

test_code = '''# Present the existing test results alongside their effect sizes.
# These ordinary chi-square tests are exploratory and are NOT survey-adjusted.
test_results = pd.DataFrame(results).set_index('Grouping')
fig, (ax_table, ax_effect) = plt.subplots(
    1, 2, figsize=(13, 5.5), gridspec_kw={'width_ratios': [1.65, 1]}
)

table_rows = []
for group, row in test_results.iterrows():
    table_rows.append([
        group, f"{int(row['N']):,}", f"{row['Chi_square_unweighted']:.2f}",
        str(int(row['Degrees_of_freedom'])),
        f"{row['P_value_exploratory']:.4f}",
        f"{row['Minimum_expected_count']:.2f}"
    ])

ax_table.axis('off')
ax_table.set_title('Ordinary chi-square results (unweighted)',
                   loc='left', fontsize=12, fontweight='bold', pad=20)
table = ax_table.table(
    cellText=table_rows,
    colLabels=['Grouping', 'N', 'Chi-square', 'df', 'p-value', 'Min. expected\\ncount'],
    colWidths=[0.25, 0.13, 0.17, 0.08, 0.15, 0.22],
    cellLoc='center', bbox=[0, 0.32, 1, 0.53]
)
table.auto_set_font_size(False)
table.set_fontsize(10)
for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor('white')
    cell.set_facecolor('#41699b' if row == 0 else '#eef2f6')
    if row == 0:
        cell.set_text_props(color='white', fontweight='bold')

effect_sizes = test_results['Cramers_V_unweighted']
ax_effect.barh(effect_sizes.index, effect_sizes, color='#41699b', height=0.45)
ax_effect.invert_yaxis()
for i, value in enumerate(effect_sizes):
    ax_effect.text(value + 0.02, i, f'{value:.3f}', va='center', fontsize=12)
ax_effect.set_xlim(0, 1)
ax_effect.set_xlabel("Cramér's V (0 = no association; 1 = maximum)", fontsize=9)
ax_effect.set_title('Measured association is small',
                    loc='left', fontsize=12, fontweight='bold', pad=20)
ax_effect.spines[['top', 'right', 'left']].set_visible(False)
ax_effect.grid(axis='x', alpha=0.15)
ax_effect.set_axisbelow(True)

fig.suptitle('Sensitivity check: two income groupings, the same respondents',
             x=0.03, ha='left', fontsize=16, fontweight='bold')
fig.text(0.03, 0.03,
         'Both p-values are below 0.05; the smaller p-value does not identify a better grouping. df = degrees of freedom.\\n'
         'Neither test adjusts for survey weights, sampling areas or strata. Final inference requires a survey-adjusted test.\\n'
         'Effect sizes are unweighted. Changing income groups does not address bias from missing responses or establish causation.',
         fontsize=9, color='#485362')
fig.tight_layout(rect=[0, 0.2, 1, 0.9], w_pad=3)
plt.show()
'''

def cell(kind, source):
    result = {'cell_type': kind, 'metadata': {}, 'source': source.splitlines(keepends=True)}
    if kind == 'code':
        result.update(execution_count=None, outputs=[])
    return result

new_cells = [
    cell('markdown', '### Missing income across groups\nThese charts show who may be underrepresented after incomplete responses are excluded. Percentages use the total within each group.'),
    cell('code', missing_code),
    cell('markdown', '### Respondents retained for analysis\nA valid income response and a valid party-identification response are required. None/No remains a valid party response.'),
    cell('code', sample_code),
    cell('markdown', '### Chi-square sensitivity results\nThe table compares the existing exploratory tests. The adjacent chart shows association strength on the full 0–1 scale. These are **unweighted tests**, unlike the weighted party-percentage chart below.'),
    cell('code', test_code)
]

# Validate using the existing preparation and analysis without rerunning CSV exports.
namespace = {'display': lambda *args, **kwargs: None}
with contextlib.redirect_stdout(io.StringIO()):
    for i in [1, 2, 3, 4, 5, 6, 8, 9]:
        exec(''.join(original_cells[i]['source']), namespace)

output_dir = root / 'tmp/notebook_chart_review'
output_dir.mkdir(parents=True, exist_ok=True)
for index, new_cell in enumerate(new_cells):
    if new_cell['cell_type'] != 'code':
        continue
    plt.close('all')
    exec(''.join(new_cell['source']), namespace)
    fig = plt.gcf()
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=130, facecolor='white')
    (output_dir / f'chart_{index}.png').write_bytes(buffer.getvalue())
    new_cell['outputs'] = [{
        'output_type': 'display_data', 'metadata': {},
        'data': {'image/png': base64.b64encode(buffer.getvalue()).decode(),
                 'text/plain': [f'<Figure: supplementary analysis chart>']}
    }]

notebook['cells'] = original_cells[:10] + new_cells + original_cells[10:]
assert [c for c in notebook['cells'] if c not in new_cells] == original_cells
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Added and rendered three charts. All original cells preserved.')
print(output_dir)
