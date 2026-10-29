# Contributing

Thanks for helping make healthcare ML evaluation easier to understand.

## Start small

See [ROADMAP.md](ROADMAP.md) for bounded tasks. Open an issue before starting a large feature so its scope can be discussed. A useful first pull request can improve one explanation, add one focused regression test, or fix one accessibility problem.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
health-model-report serve
python -m pytest
```

The dashboard uses ordinary HTML, CSS, and JavaScript; Node.js and a frontend build are not needed. Refresh the browser after asset edits. Restart the Python server after Python edits.

| File | Responsibility |
| --- | --- |
| `src/health_model_report/data.py` | CSV validation and synthetic data generation |
| `src/health_model_report/metrics.py` | Evaluation and uncertainty methods |
| `src/health_model_report/report.py` | Standalone HTML export |
| `src/health_model_report/app.py` | Local HTTP API and static assets |
| `src/health_model_report/static/` | Browser interface |
| `tests/test_evaluation.py` | Statistical, validation, export, and API regression tests |

## Pull requests

- Explain the user-visible problem and the resulting behavior.
- Add meaningful regression coverage when changing validation or statistical calculations. Use a hand-calculated example or authoritative reference value.
- Explain any statistical assumptions; preserve N/A for undefined metrics.
- Include before/after screenshots for interface changes. Check a narrow screen and keyboard navigation.
- Use synthetic data in examples, issues, tests, and screenshots. Do not submit patient records, private datasets, credentials, or clinical identifiers.
- Keep exports self-contained and preserve local data processing.
- Run `python -m pytest` and `python -m build`.

## Working together

Be respectful, explain your reasoning, and critique ideas without attacking people. Make room for contributors with different backgrounds in engineering, statistics, medicine, and design. Harassment and discriminatory behavior are unwelcome. Maintainers may remove harmful content and close contributions that violate these expectations.
