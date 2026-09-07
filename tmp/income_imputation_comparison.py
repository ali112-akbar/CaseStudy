from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

root = Path(__file__).resolve().parents[1]
df = pd.read_stata(root / 'UKDA-6970-stata/BSE_2010.dta', convert_categoricals=False)
# Rounded band midpoints; the open top band requires an explicit assumption.
# Use the questionnaire's 40,001–45,000 boundaries for band 9.
midpoints = dict(zip(range(1, 15), [2500, 7500, 12500, 17500, 22500,
    27500, 32500, 37500, 42500, 47500, 55000, 65000, 75000, 85000]))
income = df.zqinc.map(midpoints)
party = df.bq9_1.where(df.bq9_1.between(1, 12))
income_mean = float(income.mean())
party_mode = int(party.mode().iloc[0])
party_labels = {1: 'None/No', 2: 'Labour', 3: 'Conservative', 4: 'Liberal Democrat',
                **dict.fromkeys(range(5, 13), 'Other parties')}

def analyse(name, inc, par):
    groups = pd.cut(inc, [0, 10000, 20000, 40000, np.inf], include_lowest=True,
                    labels=['Up to 10k', '10–20k', '20–40k', 'Above 40k'])
    labels = par.map(party_labels)
    counts = pd.crosstab(groups, labels)
    chi, p, dof, expected = chi2_contingency(counts, correction=False)
    n = int(counts.to_numpy().sum())
    v = np.sqrt(chi / (n * min(counts.shape[0]-1, counts.shape[1]-1)))
    return {'scenario': name, 'n': n, 'chi_square': chi, 'df': dof, 'p': p,
            'cramers_v': v, 'minimum_expected': float(expected.min()),
            'expected_below_5': int((expected < 5).sum()),
            'counts': counts.to_dict(),
            'unweighted_percent': (counts.div(counts.sum(axis=1), axis=0)*100).round(2).to_dict()}

results = [analyse('Complete cases', income, party),
           analyse('Income mean only', income.fillna(income_mean), party),
           analyse('Party mode only', income, party.fillna(party_mode)),
           analyse('Both mean and mode', income.fillna(income_mean), party.fillna(party_mode))]
print(json.dumps({'mean_estimated_income': income_mean,
                  'party_mode_code': party_mode,
                  'missing_income': int(income.isna().sum()),
                  'missing_party': int(party.isna().sum()),
                  'both_missing': int((income.isna() & party.isna()).sum()),
                  'results': results}, indent=2))
