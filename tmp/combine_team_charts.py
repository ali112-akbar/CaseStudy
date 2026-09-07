import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
path = root / 'UKDA-6970-stata/case_study.ipynb'
friend = root / 'UKDA-6970-stata/case_study_raw.ipynb'
friend_hash = hashlib.sha256(friend.read_bytes()).hexdigest()
nb = json.loads(path.read_text(encoding='utf-8'))

# Consistent party colours across charts; stronger colours for general charts.
palette = {'#b74249': '#D81B60', '#41699b': '#6D28D9', '#dba642': '#FBBF24',
           '#82928b': '#14B8A6', '#bbc1cb': '#FDBA74'}
for c in nb['cells']:
    if c['cell_type'] != 'code':
        continue
    source = ''.join(c['source'])
    if 'plt.' not in source:
        continue
    for old, new in palette.items():
        source = source.replace(old, new)
    if '# Compare missing income' in source:
        source = source.replace("color='#6D28D9', height=0.6", "color=('#6D28D9' if group == 'Ethnicity' else '#D81B60'), height=0.6")
    if '# Present the existing test' in source:
        source = source.replace("color='#6D28D9', height=0.45", "color=['#6D28D9', '#D81B60'], height=0.45")
    if '# BIG parties' in source:
        start = source.index('colors = [')
        end = source.index('top_5.plot.bar', start)
        source = source[:start] + '''# Match colours to response names rather than their count ranking.
response_colors = {
    'Labour': '#D81B60', 'Conservatives': '#6D28D9',
    'Liberal Democrats': '#FBBF24', 'None/No': '#FDBA74',
    "Don't Know": '#475569', 'Refused': '#475569'
}
colors = [response_colors.get(response, '#14B8A6') for response in top_5.index]

''' + source[end:]
        source = source.replace('top_5.plot.bar(figsize=(8, 5), color=colors)',
                                "ax = top_5.plot.bar(figsize=(9, 5.5), color=colors)\nax.bar_label(ax.containers[0], padding=4, fontsize=10)\nax.set_ylim(0, top_5.max() * 1.15)\nax.spines[['top', 'right']].set_visible(False)")
    c['source'] = source.splitlines(keepends=True)

def cell(kind, source):
    c = {'cell_type': kind, 'metadata': {}, 'source': source.splitlines(keepends=True)}
    if kind == 'code':
        c.update(execution_count=None, outputs=[])
    return c

intro = '''### Team contribution: income distributions within Labour and Conservative identifiers
Adapted from the Labour–Conservative income-distribution comparison in `case_study_raw.ipynb`.
The teammate's comparison adds a complementary question: **within each party, how are respondents distributed across income bands?**
The main stacked chart instead asks which parties respondents identify with **within each income group**.

Here we use survey-weighted percentages, identical axes, and the original 14 income bands.
This makes the unequal party sample sizes comparable without assigning exact incomes or assuming an upper limit for the highest band.
This is a supporting descriptive comparison, not an additional significance test. People are party identifiers, not necessarily voters for that party.
'''
code = '''# Adapted from our teammate's Labour–Conservative distribution chart.
# Each party's bars sum to 100%; only respondents with valid income are included.
comparison_data = complete.loc[
    complete['Party'].isin(['Labour', 'Conservative'])
].copy()

income_band_labels = [
    '£0–5,000', '£5,001–10,000', '£10,001–15,000', '£15,001–20,000',
    '£20,001–25,000', '£25,001–30,000', '£30,001–35,000', '£35,001–40,000',
    '£40,001–45,000', '£45,001–50,000', '£50,001–60,000',
    '£60,001–70,000', '£70,001–80,000', '£80,001 or more'
]
# Band 9 follows the questionnaire (the data label says 41,000–45,000).
income_by_party = pd.crosstab(
    comparison_data['Income'], comparison_data['Party'],
    values=comparison_data['Weight'], aggfunc='sum'
).reindex(range(1, 15)).fillna(0)
income_by_party = income_by_party.div(income_by_party.sum(axis=0), axis=1) * 100
party_sizes = comparison_data['Party'].value_counts()

fig, axes = plt.subplots(1, 2, figsize=(13, 8), sharex=True, sharey=True)
for ax, party, color in zip(axes, ['Labour', 'Conservative'], ['#D81B60', '#6D28D9']):
    values = income_by_party[party]
    ax.barh(range(14), values, color=color, height=0.65)
    for i, value in enumerate(values):
        ax.text(value + 0.3, i, f'{value:.1f}%', va='center', fontsize=10)
    ax.set_title(f'{party} (n={party_sizes[party]:,})', loc='left', fontweight='bold')
    ax.set_xlabel('Weighted percentage within this party')
    ax.set_xlim(0, income_by_party.to_numpy().max() + 4)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.grid(axis='x', alpha=0.15)
    ax.set_axisbelow(True)
axes[0].set_yticks(range(14), income_band_labels)
axes[0].invert_yaxis()
fig.suptitle('How household income is distributed within each party',
             x=0.03, ha='left', fontsize=16, fontweight='bold')
fig.text(0.03, 0.025,
         'EMBES 2010 | F2F ALL5 weights | n = unweighted respondents with valid income and party answers.\\n'
         'Each panel sums to 100%. Original income bands have unequal widths; bars show category shares, not income density.\\n'
         'This two-party comparison complements the all-party analysis; it does not establish causation.',
         fontsize=9, color='#485362')
fig.tight_layout(rect=[0, 0.13, 1, 0.94], w_pad=3)
plt.show()

# A short weighted summary to help interpret the distribution chart.
above_20k = income_by_party.loc[5:14].sum()
for party in ['Labour', 'Conservative']:
    print(f'{party}: {above_20k[party]:.1f}% have household income above £20,000 (weighted).')
'''
nb['cells'].extend([cell('markdown', intro), cell('code', code)])

# Execute preparation, existing tests and every chart; preserve the CSV export cell.
review = root / 'tmp/combined_chart_review'
review.mkdir(parents=True, exist_ok=True)
namespace = {}
outputs = []
def display(*objects):
    for obj in objects:
        data = {'text/plain': [str(obj)]}
        if hasattr(obj, '_repr_html_'):
            data['text/html'] = [obj._repr_html_()]
        outputs.append({'output_type': 'display_data', 'metadata': {}, 'data': data})
namespace['display'] = display
def show():
    for number in plt.get_fignums():
        fig = plt.figure(number)
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=120, facecolor='white')
        (review / f'cell_{index}.png').write_bytes(buffer.getvalue())
        outputs.append({'output_type': 'display_data', 'metadata': {},
                        'data': {'image/png': base64.b64encode(buffer.getvalue()).decode(),
                                 'text/plain': ['<Figure: analysis chart>']}})
    plt.close('all')
plt.show = show
for index, c in enumerate(nb['cells']):
    if c['cell_type'] != 'code':
        continue
    source = ''.join(c['source'])
    if '.to_csv(' in source:
        continue
    outputs = []
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        exec(source, namespace)
    if stream.getvalue():
        outputs.append({'output_type': 'stream', 'name': 'stdout', 'text': stream.getvalue().splitlines(keepends=True)})
    if 'plt.' in source and 'plt.show()' in source:
        c['outputs'] = outputs
        c['execution_count'] = None

import numpy as np
assert np.allclose(namespace['income_by_party'].sum(), 100)
assert len(namespace['complete']) == 1597
assert np.isclose(namespace['results'][0]['P_value_exploratory'], 0.009339663812661015)
assert hashlib.sha256(friend.read_bytes()).hexdigest() == friend_hash
above = namespace['above_20k']
conclusion = f'''### Combined interpretation and contribution summary
The main analysis retains **1,597 respondents** with valid income and party answers and keeps None/No as a meaningful response.
Weighted party shares show Labour is the largest identification category in all four income groups, while Conservative identification is more common in the upper two groups.

The adapted teammate chart complements this: among identifiers with valid income, **{above['Conservative']:.1f}% of Conservative identifiers** and **{above['Labour']:.1f}% of Labour identifiers** report household income above £20,000 (weighted).
These percentages use a different denominator from the main chart, so they should not be compared directly with party shares within income groups.

The original exploratory four-group test remains **chi-square = 26.4255, df = 12, p = 0.0093, Cramér's V = 0.0743**.
This is evidence of a small association under the ordinary test assumptions. The test is unweighted and does not account for sampling areas or strata; survey-adjusted inference is still required.
Uneven missing income and the absence of adjustment for characteristics such as ethnicity also limit interpretation. These results do not demonstrate causation.

**Contributions:** The main notebook supplies missingness checks, the all-party weighted comparison, and chi-square/effect-size sensitivity analysis.
The teammate's notebook supplies the idea of examining income distributions within Labour and Conservative identifiers, adapted here to weighted original-band charts.
Midpoint-based box plots, the straight-line probability chart and additional two-party tests were not imported; the contribution is descriptive and does not change the main statistical results.
'''
nb['cells'].append(cell('markdown', conclusion))
path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Main notebook updated; all six charts rendered and checked computationally.')
print(above.to_string())
print('Friend notebook unchanged; original main p-value reproduced.')
