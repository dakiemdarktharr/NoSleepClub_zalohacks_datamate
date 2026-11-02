# Project working agreement

Read README.md, docs/CONSTRAINTS.md and docs/FEATURES.md before changing the system.

- Current implementation includes foundation utilities and a conservative deterministic baseline, not the complete planned agent. Distinguish implemented, tested, proposed and blocked work.
- Keep organizer data, labels, predictions, model weights, private traces and copied source dumps out of commits. Public fixtures must be wholly synthetic.
- The supplied evaluator, rulebook/calendar, data partitions and budget are outside the automatic RSI editor's authority.
- Public/private test data cannot guide training, synthetic curricula, identifier-keyed logic or prompt lessons.
- Preserve raw data and explicit unknowns. Empty results and zero are not automatically unanswerable. Parser disagreement is uncertainty, not proof of missing data.
- Reuse a single eligible checkpoint for roles; count every inference model conservatively, including auxiliaries and swapped models.
- No official score claims until the named artifact/split was evaluated by the actual official evaluator.
- Source citations must be checked against primary papers; do not copy benchmark scores as expected DataMate gains.
- Run meaningful tests for logic changes: PYTHONPATH=src python -m unittest discover -s tests -v.
- Record scope, measured result and limitations in docs/FEATURES.md and the relevant design document.
