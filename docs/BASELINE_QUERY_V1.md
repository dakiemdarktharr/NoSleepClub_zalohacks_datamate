# Baseline query interpreter v1

Implemented in src/nosleepclub_datamate/baseline_query.py for a first conservative, model-free entry. This is a narrow interpreter, not the proposed general research agent.

## Runtime interface
answer_question(question_record, business_data, policy) returns an official-shaped record with id/type and answer where required. solve_question is a compatibility alias. Load RulebookPolicy.from_text from the current split's actual rulebook; absent/unrecognized required semantics fail closed.

## Supported scope
- Single Gregorian day, inclusive explicit date range, month or quarter; relative today/yesterday, Monday weeks, current month to as_of_date, previous month, N recent days and year to date.
- Whole-shop or exactly grounded product revenue; an explicit supported payment-method or shift filter.
- Valid/cancelled order counts, cancellation percentage and supported order-revenue thresholds.
- Average order revenue, highest-revenue day, and top products by base quantity with identifier tie-breaking.
- A known order-only register can support counts/cancellation rate; ambiguous header totals are not promoted to line revenue.
- Exact required numeric/string/list/date formats, with Decimal money rounding.

Future-only periods, lunar/Tet semantics, multi-period comparisons, profit/debt/inventory, groups/channels, customer/employee rankings and newly defined popular/loyal/premium/busiest/cash-report concepts abstain. A residual-token whitelist prevents unknown product names, categories, weekday/hour filters or extra metrics from becoming a whole-shop total.

## Unknowns and boundaries
Unknown dates/statuses/amounts cause abstention rather than silently dropping records. Valid empty periods can yield zero. An explicit README coverage boundary may justify an outside-period unanswerable result; an observed first/last sale alone only justifies abstention. Explicit M/Y means the whole calendar month; relative periods use the provided as_of_date, never the machine clock.

## Verification and limits
Thirty wholly synthetic query/date regression tests cover status exclusion, grain, ties, timing, money, missingness, order-only registers and unsupported scopes. The complete repository suite passed 76 tests on 2026-11-02 with Python 3.11 and local optional workbook dependencies. These tests do not establish official competition accuracy or ingestion correctness for every layout.

Initial train-only distribution/pattern exploration occurred before the grouped diagnostic partition was frozen. No public questions or labels were read, no held-out-case error feedback was used to hand-code this module, and no question/business identifiers determine answers. Aggregate training diagnostics and the official portal result must be reported separately by the runner.

