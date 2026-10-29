# Roadmap

The first release prioritizes binary, patient-level classification and a fast local CSV workflow. These are planned tasks, not implemented features.

## Small first contributions

- **Calibration table:** add a keyboard-accessible table of bin means, outcome rates, patient counts, and confidence intervals below the chart.
- **CSV examples:** add a synthetic single-class example and a short explanation of why AUROC is unavailable.
- **Confusion matrix descriptions:** improve screen-reader descriptions and add keyboard-focused usability notes.
- **Metric glossary:** add short, reviewed examples explaining precision, recall, and average precision.
- **Report print layout:** improve page breaks for long subgroup tables, with a before/after print preview.

## Next features

- Two-model comparison using the same held-out patients, with paired uncertainty estimates.
- A validation/test workflow for selecting and freezing an operating threshold.
- Intersectional subgroup analysis with explicit sample-size and multiple-comparison guidance.
- Cluster-aware bootstrap for repeated patient encounters; change the input contract before allowing repeated IDs.
- A visible ROC plot in the dashboard; the current HTML export already includes one.
- A real, openly licensed example dataset with documented access and redistribution terms.
- Optional adapter examples for PyHealth and scikit-learn pipelines.

## Release checklist

- [x] Choose a GitHub owner and confirm the repository/package name (`pemalama12/health-model-report`).
- [ ] Push source and run the configured CI matrix.
- [ ] Turn a few small roadmap items into `good first issue` tickets.
- [x] Add the actual GitHub repository URL to package metadata and README.
- [x] Review example reports and screenshots for the release.
- [ ] Publish a versioned GitHub release with a short demo.

PyPI publication and a hosted demo are separate future decisions. The current app runs locally.
