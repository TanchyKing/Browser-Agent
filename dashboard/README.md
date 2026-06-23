# Evaluation Dashboard

This dashboard is dependency-light by design. It renders a static HTML report
from the JSON produced by `scripts/evaluate_tasks.py`.

Example:

```powershell
python -B scripts\evaluate_tasks.py `
  --traces tests\eval\fixtures\mock_traces.jsonl `
  --out-json artifacts\eval\mock_summary.json

python -B dashboard\render_report.py `
  --summary artifacts\eval\mock_summary.json `
  --out-html artifacts\eval\mock_report.html
```

The report is safe to generate from mock traces. Do not treat mock reports as
real model results in README or resume material.
