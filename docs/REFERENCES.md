# Annotated references

35 selected primary papers/reports. Reviewed 2026-11-02; quality and read limits below. These are architectural precedents, not measured DataMate gains. The technical review is targeted, not exhaustive.

## R01 — CHESS: Contextual Harnessing for Efficient SQL Synthesis

- [Primary source](https://arxiv.org/html/2405.16755v3) · DOI 10.48550/arXiv.2405.16755
- Venue/status: arXiv; authors' lab lists ICML 2025 MAS workshop; preprint v3 reviewed; workshop listing verified at authors' lab, not labeled ICML main conference
- Read: CoChat abstract_only; Firecrawl retrieved public arXiv v3 HTML (119482 chars); sections 3.1-3.3, 4.2.3, limitations and A.1-A.3 read
- Supports: Entity/catalog retrieval, key-preserving schema filtering, one-candidate low-compute configuration and amortized value indexing reduce context work. Large-schema experiment combines databases.
- Limits: Original open-model configuration includes Llama3-70B and neural embeddings, not a legal <=15B graph. Empty-output-repair heuristic is inappropriate for DataMate. Natural-language unit tests are not a proof of semantic correctness.
- Transfer: per-business value/catalog index; keys and dependency closure retained during schema pruning; one-candidate baseline plus bounded revisions; adaptive omission of expensive tester

## R02 — Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows

- [Primary source](https://openreview.net/pdf?id=XmProj9cPs) · DOI 10.48550/arXiv.2411.07763
- Venue/status: ICLR 2025; peer-reviewed; v2 arXiv 2025-03-17 reviewed
- Read: CoChat abstract_only/analysis-only status; public primary v2 HTML retrieved through Firecrawl; task/evaluation/results/error analysis and C.1 harness read; official ICLR PDF venue cross-check
- Supports: Enterprise QA needs metadata/document grounding and iterative execution; schema linking, analysis planning and joins remain substantial failure categories. Explicit tool actions separate catalog inspection from execution.
- Limits: Broader cloud/DBT workloads than DataMate. Main/appendix decoding settings differ. Does not prove scores or hardware performance under DataMate constraints.
- Transfer: separate schema/sample/document/execution tools; multi-file and document-dependent stress cases; execution-based exact task outcome; explicit stopping/repetition/runtime budgets

## R03 — SheetCopilot: Bringing Software Productivity to the Next Level through Large Language Models

- [Primary source](https://proceedings.neurips.cc/paper_files/paper/2023/hash/0ff30c4bf31db0119a6219e0d250e037-Abstract-Conference.html)
- Venue/status: NeurIPS 2023 Main Conference; peer-reviewed conference
- Read: CoChat full_text truncated at ~50k characters; primary NeurIPS page verified
- Supports: Spreadsheet API abstraction plus state-machine observation/planning/revision is prior art; 221 tasks cover sheet manipulation rather than only QA.
- Limits: GUI/software control output differs from DataMate typed answers; atomic actions do not by themselves solve business semantics.

## R04 — Data Interpreter: An LLM Agent For Data Science

- [Primary source](https://aclanthology.org/2025.findings-acl.1016/) · DOI 10.18653/v1/2025.findings-acl.1016
- Venue/status: Findings of ACL 2025; peer-reviewed conference proceedings
- Read: CoChat full_text of arXiv v4 (truncated); official ACL 2025 record/PDF abstract verified; version differences noted
- Supports: Hierarchical task/action graphs with progressive execution, verification and replanning are established prior art. Intermediate step verification and context management are stronger foundations than free-form multi-agent discussion.
- Limits: Benefits depend on model/context capacity: arXiv table reports degradation for GPT-4-0613 but improvement for GPT-4o. Data-science benchmarks do not certify DataMate gains.

## R05 — ReAcTable: Enhancing ReAct for Table Question Answering

- [Primary source](https://www.vldb.org/pvldb/vol17/p1981-zhang.pdf) · DOI 10.14778/3659437.3659452
- Venue/status: PVLDB 17(8):1981-1994, 2024; peer-reviewed journal/conference
- Read: CoChat full_text truncated at ~50k characters; final PVLDB paper metadata verified
- Supports: Iterative SQL/Python transformations, intermediate table representations and execution-based selection already exist for table QA; reported WikiTQ result is 68.0%.
- Limits: Paper formulation focuses single-table TQA and mostly public benchmark tables; multi-file joins and missing-evidence refusal remain gaps.

## R06 — EntSQL: A Benchmark for Grounding Text-to-SQL in Long-Context Enterprise Knowledge

- [Primary source](https://arxiv.org/abs/2606.03363) · DOI 10.48550/arxiv.2606.03363
- Venue/status: arXiv 2026 v3 (14 July); preprint; peer review not confirmed
- Read: CoChat full_text complete; primary arXiv metadata verified
- Supports: 1,066 bilingual enterprise examples test long business-document grounding. Localized evidence performs better than full documents, but substantial rule-composition failure remains. Error analysis of one model identifies filters/scope as major failures.
- Limits: Single enterprise, five domains; English-translated main evaluation; one-model failure taxonomy; no Vietnamese results. Do not transfer benchmark numbers to DataMate.

## R07 — ProSPy: A Profiling-Driven SQL-Python Agentic Framework for Enterprise Text-to-SQL

- [Primary source](https://arxiv.org/abs/2606.05836) · DOI 10.48550/arxiv.2606.05836
- Venue/status: arXiv 2026 v1 (4 June); preprint; peer review not confirmed
- Read: CoChat full_text complete; primary arXiv metadata verified
- Supports: Profiling once per database, progressive schema pruning, dimensions/metrics/conditions DSL, SQL views and Python analysis are existing architecture. Reported ablations support profiling/DSL/Python on a small Spider2-Snow subset.
- Limits: Intermediate-view errors propagate; cloud/enterprise schemas differ from messy files. Long schema-linking latency means direct adoption may miss competition budget.

## R08 — Binding Language Models in Symbolic Languages

- [Primary source](https://openreview.net/forum?id=lH1PV42cbF) · DOI 10.48550/arXiv.2210.02875
- Venue/status: ICLR 2023; peer-reviewed conference
- Read: CoChat full_text truncated; official OpenReview PDF verified
- Supports: Training-free neuro-symbolic executable programs and binding LM functions into SQL/Python already exist; explicit programs aid debugging.
- Limits: LM-returned semantic values are not guaranteed correct and may use outside knowledge. In DataMate, use only authorized data/rulebook; do not infer missing business facts.

## R09 — TrustSQL: Benchmarking Text-to-SQL Reliability with Penalty-Based Scoring

- [Primary source](https://arxiv.org/abs/2403.15879) · DOI 10.48550/arXiv.2403.15879
- Venue/status: arXiv; preprint; arXiv v6 under review; CoChat search non-preprint flag not accepted
- Read: CoChat full_text truncated at 50000 chars; primary arXiv v6 cross-check
- Supports: Reliable text-to-SQL combines feasibility detection, SQL-error detection and abstention; penalty-based scoring makes confident errors expensive.
- Limits: Not Vietnamese messy workbook QA; does not establish DataMate performance. Older title in CoChat search differs from v6.

## R10 — Reliable Text-to-SQL with Adaptive Abstention

- [Primary source](https://doi.org/10.1145/3709719) · DOI 10.1145/3709719
- Venue/status: Proceedings of the ACM on Management of Data / SIGMOD 2025; peer-reviewed; fetched author preprint/working draft
- Read: CoChat full_text truncated; DOI publisher abstract cross-check
- Supports: Schema-linking uncertainty and conformal branching can trigger abstention or human intervention.
- Limits: Human interaction and hidden-layer access are not automatically available/allowed in DataMate; guarantees do not transfer under domain shift.

## R11 — Semantic Evaluation for Text-to-SQL with Distilled Test Suites

- [Primary source](https://aclanthology.org/2020.emnlp-main.29/) · DOI 10.18653/v1/2020.emnlp-main.29
- Venue/status: EMNLP 2020; peer-reviewed
- Read: CoChat full_text truncated; ACL Anthology cross-check
- Supports: Single-database denotation agreement can be a false positive; distilled diverse database suites approximate semantic equivalence.
- Limits: Evaluation uses gold SQL, unavailable for private inference. Does not remove need for independent semantic oracle.

## R12 — Dr.Spider: A Diagnostic Evaluation Benchmark towards Text-to-SQL Robustness

- [Primary source](https://openreview.net/pdf?id=Wc5bmZZU9cy) · DOI 10.48550/arXiv.2301.08881
- Venue/status: ICLR 2023; peer-reviewed
- Read: CoChat full_text; official ICLR/OpenReview PDF identified
- Supports: Schema/content/question perturbations expose robustness failures obscured by standard development accuracy.
- Limits: Older model generations; does not directly predict effect sizes for the chosen legal 14B model.

## R13 — TrustDABench: Benchmarking Reliability and Robustness of LLMs for Structured Data Analysis

- [Primary source](https://arxiv.org/abs/2608.24145) · DOI 10.48550/arXiv.2608.24145
- Venue/status: arXiv; preprint, 2026-08-25
- Read: CoChat full_text truncated; primary HTML abstract/methods cross-check
- Supports: CSV/spreadsheet agents fail at missing/conflicting evidence and representation changes; 7 reliability plus 12 robustness operators provide useful stress-test families.
- Limits: Single recent benchmark; LLM-assisted construction and judging; different tasks/languages/models; no independent replication found.

## R14 — PremiseSQL: Evaluating Premise Critique and Abstention in Text-to-SQL Systems

- [Primary source](https://arxiv.org/abs/2610.22158) · DOI 10.48550/arXiv.2610.22158
- Venue/status: arXiv; preprint, 2026-10-15
- Read: CoChat full_text truncated; primary HTML taxonomy/methods cross-check
- Supports: Critique prompts can increase detection of flawed premises while falsely rejecting valid paired originals.
- Limits: Benchmark taxonomy includes SQL-expressibility limits that do not apply to SQL+Python DataMate agents; not an unanswerability oracle.

## R15 — DPC: Training-Free Text-to-SQL Candidate Selection via Dual-Paradigm Consistency

- [Primary source](https://aclanthology.org/2026.acl-long.313/) · DOI 10.18653/v1/2026.acl-long.313
- Venue/status: ACL 2026; peer-reviewed
- Read: CoChat full_text truncated; ACL primary page cross-check
- Supports: Minimal Distinguishing Databases via SLICER/TESTER agents plus SQL/Python consistency already implement much of the generic witness-verifier idea.
- Limits: Python is a proxy reference and can share semantic bias. Gains cannot be transferred to DataMate or <=15B offline models without experiment.

## R16 — Automated Validating and Fixing of Text-to-SQL Translation with Execution Consistency

- [Primary source](https://doi.org/10.1145/3725271) · DOI 10.1145/3725271
- Venue/status: Proceedings of the ACM on Management of Data / SIGMOD 2025; peer-reviewed
- Read: CoChat abstract_only; primary author-PDF search excerpts retrieved (including unrealistic counterexamples), direct PDF open timed out; no complete PDF read claimed
- Supports: SQLDriller generates candidate SQLs and obtains counterexample DBs with an equivalence checker, then validates NL/SQL consistency; unrealistic fixtures are a documented concern.
- Limits: Training-dataset validation focus; no gold correctness proof from a candidate disagreement alone; no DataMate gain claim.

## R17 — SPOTIT+: Verification-based Text-to-SQL Evaluation with Database Constraints

- [Primary source](https://arxiv.org/abs/2603.04334) · DOI 10.48550/arXiv.2603.04334
- Venue/status: arXiv; preprint v3, 2026-05-11; unverified venue template in PDF not treated as publication evidence
- Read: CoChat full_text untruncated; primary arXiv metadata cross-check
- Supports: Bounded equivalence checking can use mined/validated domain constraints to produce realistic counterexamples; constraint extraction is best-effort.
- Limits: Requires gold/reference query for evaluation; bounded verification is not global SQL equivalence; broad SQL equivalence is undecidable.

## R18 — SQL's Three-Valued Logic and Certain Answers

- [Primary source](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICDT.2015.94) · DOI 10.4230/LIPIcs.ICDT.2015.94
- Venue/status: ICDT 2015; expanded journal version TODS 2016 DOI 10.1145/2877206; peer-reviewed
- Read: CoChat full_text untruncated but returned ICDT 2015 precursor when queried by TODS DOI; canonicalized to actually read version
- Supports: Certain answers are invariant over admitted completions; SQL's handling of unknown/false can yield false positives; tractable sound approximations require explicit semantics.
- Limits: Cannot claim an all-SQL all-worlds solver. Aggregates, ambiguity and data completeness require separately stated fragments and assumptions.

## R19 — Trajectory-Derived Confidence for Reliable, Resource-Aware Clinical Text-to-SQL Agents

- [Primary source](https://arxiv.org/abs/2610.04156) · DOI 10.48550/arXiv.2610.04156
- Venue/status: arXiv; manuscript states NeurIPS 2026 resource-aware agentic AI workshop; preprint, 2026-10-02; workshop acceptance not independently established here
- Read: CoChat full_text truncated; arXiv primary abstract cross-check
- Supports: Sentinel monitors answerability and correctness at pre-run, mid-run and delivery gates, uses Chow's rule and can reduce wasted trajectories.
- Limits: Clinical EHRSQL domain and label-trained classifiers; correctness/answerability gates are existing art. Extra neural classifier would count toward DataMate's aggregate parameter cap.

## R20 — Never the Number: Structural Abstention for AI Systems Whose Answers Are Consumed as Fact

- [Primary source](https://arxiv.org/abs/2608.13926) · DOI 10.48550/arXiv.2608.13926
- Venue/status: arXiv technical report; preprint / conceptual architecture report
- Read: CoChat full_text truncated; primary arXiv disclosure cross-check
- Supports: Trusted deterministic kernel plus generative shell and structural abstention are explicitly proposed; bounded question coverage trades off reliability.
- Limits: Report explicitly excludes code, real schemas, datasets and quantitative performance metrics; human confirmation assumption does not fit non-interactive evaluation.

## R21 — What Predicts Correctness in Text-to-SQL? A Selective-Prediction Study

- [Primary source](https://arxiv.org/abs/2607.06799) · DOI 10.48550/arXiv.2607.06799
- Venue/status: arXiv; preprint; downweighted from headline evidence
- Read: CoChat full_text untruncated; primary arXiv cross-check
- Supports: In its experiments, statistical self-consistency is weaker than reasoning verifiers and small trained verifiers transfer poorly across schemas.
- Limits: Limited datasets/generators; placeholder affiliation and an incorrect RTS author citation in references. Not independently replicated; do not build a quantitative promise on this paper.

## R22 — A Pilot Study of Text-to-SQL Semantic Parsing for Vietnamese

- [Primary source](https://aclanthology.org/2020.findings-emnlp.364/) · DOI 10.18653/v1/2020.findings-emnlp.364
- Venue/status: Findings of EMNLP 2020; peer-reviewed conference proceedings
- Read: CoChat full_text available; task construction, methods, results and selected error analysis read
- Supports: ViText2SQL translates clean Spider questions and schema into Vietnamese; schema/value linking and segmentation affect historical parsers. The clean benchmark does not directly represent DataMate's raw files, colloquial questions and rulebook.
- Limits: 2020 recurrent parsers and translated clean databases; cannot extrapolate gains to modern LLM agents.

## R23 — VLSP 2025 Shared Task: Vietnamese Temporal Question Answering (TemporalQA)

- [Primary source](https://jcsce.vnu.edu.vn/index.php/jcsce/article/view/6505) · DOI 10.25073/2588-1086/vnucsce.6505
- Venue/status: VNU Journal of Science: Computer Science and Communication Engineering 42(3):34–53; peer-reviewed journal; accepted 2026-08-19
- Read: CoChat full_text returned, truncated; introduction, task definitions, evaluation and data construction read
- Supports: Vietnamese date arithmetic and contextual duration are distinct tasks; parsing reference dates and mixed-unit intervals needs separate validation.
- Limits: Controlled date-arithmetic and contextual duration tasks, not proof of messy-file, Vietnamese lunar-calendar or business-calendar correctness. Semantic Scholar unavailable on the discovery query.

## R24 — GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning

- [Primary source](https://arxiv.org/abs/2507.19457) · DOI 10.48550/arXiv.2507.19457
- Venue/status: undefined; ICLR 2026 Oral; primary arXiv accepted-paper version read
- Read: CoChat indexed full text truncated to ~50,000 characters; actual methods/evaluation and limitations read, primary arXiv HTML/metadata cross-checked
- Supports: Reflective mutation optimizes frozen-model system prompts using execution/evaluation traces, minibatch screening and instance-wise Pareto candidate selection. Includes Qwen3-8B experiments with train/selection/test separation.
- Limits: Not a proof of unbounded recursive improvement; performance is task/model-dependent and merge can hurt. Repeated selection validation still invites adaptive overfit. Published gains are not DataMate PA gains.
- Transfer: Use development-time prompt optimization on train-derived feedback with a fixed execution model, official typed-answer reward, separate candidate-selection businesses and an untouched audit set. No test-derived prompt updates.

## R25 — Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models

- [Primary source](https://arxiv.org/abs/2510.04618) · DOI 10.48550/arXiv.2510.04618
- Venue/status: undefined; ICLR 2026; primary arXiv accepted-paper version read
- Read: CoChat indexed full text truncated to ~50,000 characters; actual methods/evaluation and limitations read, primary arXiv HTML/metadata cross-checked
- Supports: Generator/Reflector/Curator roles maintain itemized context bullets with local delta updates, useful/harmful counters and deterministic merges; avoids monolithic context collapse.
- Limits: Main backend is DeepSeek-V3.1-671B, far above DataMate cap; other reported transfer models are also large. Poor feedback can pollute the playbook; longer context adds latency and does not help every task.
- Transfer: Maintain offline rule-grounded lessons with scope, evidence, preconditions and regression cases; retrieve a bounded subset. Freeze learned playbook before test; deterministic lexical dedup/retrieval avoids extra inference models.

## R26 — AFlow: Automating Agentic Workflow Generation

- [Primary source](https://arxiv.org/abs/2410.10762) · DOI 10.48550/arXiv.2410.10762
- Venue/status: undefined; ICLR 2025 conference paper; official OpenReview PDF verified
- Read: CoChat abstract_only; primary arXiv HTML Sections 3-5 and algorithm/evaluation read; official OpenReview PDF venue verified
- Supports: Searches code-represented workflows using a MCTS variant over prompts/edges and fixed operators, with repeated execution feedback. Actual search fixes model, temperature and format to reduce the space.
- Limits: Uses Claude-3.5-Sonnet optimizer and API-based executors; metrics mix solve-rate/pass@1/F1 and differ from PA. Candidate evaluation is costly; workflows are model-dependent. Do not copy the paper's large search directly.
- Transfer: Search a very small approved workflow grammar offline: profile/plan/execute/verify/decide with capped retries. Lock model and total budget; compare against simpler manual routing.

## R27 — Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents

- [Primary source](https://arxiv.org/abs/2505.22954) · DOI 10.48550/arXiv.2505.22954
- Venue/status: undefined; ICLR 2026 Poster listed in official OpenReview author search; primary arXiv manuscript used
- Read: CoChat indexed full text truncated to ~50,000 characters; actual methods/evaluation and limitations read, primary arXiv HTML/metadata cross-checked
- Supports: Frozen-model coding agents self-modify their own harness repositories, with an archive enabling diverse stepping-stone lineages and staged empirical benchmark evaluation. The outer archive/selection mechanism itself remains fixed.
- Limits: Empirical benchmark improvement replaces formal proof. Full runs use Claude-3.5-Sonnet/o3-mini and 80 iterations; coding-benchmark gains do not establish tabular-QA gains or unlimited RSI.
- Transfer: Keep parented candidate snapshots and a few diverse low-cost/high-accuracy variants as development artifacts. Restrict editable surfaces; promote only after independent evaluator gates; freeze one selected harness for inference.

## R28 — AlphaEvolve: A coding agent for scientific and algorithmic discovery

- [Primary source](https://arxiv.org/abs/2506.13131) · DOI 10.48550/arXiv.2506.13131
- Venue/status: undefined; Google DeepMind white paper / arXiv preprint; peer-reviewed status not established here
- Read: CoChat indexed full text truncated to ~50,000 characters; actual methods/evaluation and limitations read, primary arXiv HTML/metadata cross-checked
- Supports: Evolutionary code search uses a user-provided automatic evaluator, explicit editable blocks, candidate database, evaluation cascades and asynchronous proposal/evaluation. Algorithms must be machine-gradeable.
- Limits: Relies on Gemini Flash/Pro and potentially substantial parallel compute. Correctness guarantees in some mathematical applications come from task-specific validators, not from evolution itself. An incomplete QA oracle remains incomplete.
- Transfer: Borrow cheap-to-expensive evaluation cascades and immutable exact scorers. Evolve bounded parser/serializer/tool components offline; final business answers always come from original supplied files.

## R29 — Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses

- [Primary source](https://arxiv.org/abs/2604.25850) · DOI 10.48550/arXiv.2604.25850
- Venue/status: undefined; arXiv preprint; peer review not confirmed
- Read: CoChat indexed full text truncated to ~50,000 characters; actual methods/evaluation and limitations read, primary arXiv HTML/metadata cross-checked
- Supports: Makes harness components file-editable, traces navigable in layered reports, and edits falsifiable through change manifests. Immutable verifier/model configuration constrain search; evaluated frozen transfer and component ablations.
- Limits: One ten-iteration campaign uses GPT-5.4 and ~32 hours. Components interact non-additively; prompt-only swap regresses and self-predicted regression recall is low. Cross-benchmark gain is modest and some repositories regress.
- Transfer: Use per-change hypothesis manifests, source evidence links, immutable scorer/config, full regression checks and rollback. Trust measured outcomes over an editing agent's self-attribution.

## R30 — Reflexion: language agents with verbal reinforcement learning

- [Primary source](https://arxiv.org/abs/2303.11366) · DOI 10.48550/arXiv.2303.11366
- Venue/status: undefined; NeurIPS 2023 proceedings record found through CoChat; primary arXiv methods/evaluation read
- Read: CoChat indexed full text truncated to ~50,000 characters; actual methods/evaluation and limitations read, primary arXiv HTML/metadata cross-checked
- Supports: Actor/evaluator/reflection roles store textual lessons across attempts without weight updates. Programming analysis shows wrong self-generated tests can falsely certify wrong code or reject correct code; external feedback matters.
- Limits: Improvement depends on evaluator quality and search diversity; reflection can get stuck. Historical coding scores are not DataMate results. Self-generated tests do not establish semantic correctness.
- Transfer: Permit one bounded retry after a concrete execution, type, rule, provenance or witness failure. Store only validated development lessons; never equate self-confidence or test agreement with a business-answer oracle.

## R31 — Recursive Language Models

- [Primary source](https://arxiv.org/abs/2512.24601) · DOI 10.48550/arXiv.2512.24601
- Venue/status: arXiv, v3 revised 2026-05-11; preprint version reviewed; no proceedings publication assumed from author-blog acceptance claim
- Read: CoChat full_text truncated near 50000 chars; actual v3 methods/evaluation and small-model training passages read; primary v3 HTML/abstract cross-check
- Supports: Externalize the input in a persistent REPL and use programmatic inspections/semantic subcalls. Depth-zero sometimes beats recursive variants; small-model training matters.
- Limits: Benchmarks are not Vietnamese CSV/XLSX/SQLite QA. Main frontier model configurations cannot meet <=15B. Comparable token cost is not a six-hour wall-clock guarantee. Small checkpoint release/quality requires separate audit.
- Transfer: external business/document state; source-addressable bounded semantic subcalls; intermediate result handles; depth-zero and depth-one ablation

## R32 — Executable Code Actions Elicit Better LLM Agents

- [Primary source](https://proceedings.mlr.press/v235/wang24h.html) · DOI 10.48550/arXiv.2402.01030
- Venue/status: ICML 2024, PMLR 235, 50208-50232; peer-reviewed
- Read: CoChat indexed full_text truncated at 50000 chars; methods/atomic-versus-composed tool evaluations/training read; PMLR primary page cross-check
- Supports: Executable code composes control/data flow and supports execution-feedback repair; tool composition was compared across 17 models.
- Limits: API/tool success and completion are not exact business-answer correctness. No DataMate-specific result. Code flexibility does not resolve missing data or semantic assumptions.
- Transfer: persistent program environment; multi-operation code action; structured error observations; bounded repair with executed result handles

## R33 — Text-to-SQL Empowered by Large Language Models: A Benchmark Evaluation

- [Primary source](https://doi.org/10.14778/3641204.3641221) · DOI 10.14778/3641204.3641221
- Venue/status: Proceedings of the VLDB Endowment 17(5), 1132-1145; peer-reviewed
- Read: CoChat indexed full_text truncated near 50000 chars; DAIL selection/organization, representation, self-consistency cost and SFT discussion read; PVLDB primary PDF/DOI cross-check
- Supports: DAIL combines domain-masked question similarity and preliminary SQL structure when selecting compact question-SQL examples; added self-consistency has a substantial cost trade-off.
- Limits: Embedding/preliminary-model components cannot be copied without parameter-budget audit. Historical Spider accuracy is not DataMate PA. Incorrect preliminary SQL can mislead example retrieval.
- Transfer: training-only operation/example library; compact question-to-program demonstrations; token-aware schema representation; cost-controlled comparison against extra sampling

## R34 — DA-Code: Agent Data Science Code Generation Benchmark for Large Language Models

- [Primary source](https://aclanthology.org/2024.emnlp-main.748/) · DOI 10.18653/v1/2024.emnlp-main.748
- Venue/status: EMNLP 2024, 13487-13521; peer-reviewed
- Read: CoChat full_text truncated near 50000 chars; task/environment/action-space/evaluation setup/results read; primary ACL PDF/page identified
- Supports: Wrangling/EDA/ML tasks use an action-observation environment with Python/SQL/Bash; completion and executable-code rates can be much higher than correct-result scores.
- Limits: Artifact-scoring tasks and historical large/proprietary models differ from strict typed DataMate QA. Bounded-history truncation can erase necessary semantic context. No direct <=15B performance evidence.
- Transfer: replayable action-observation trace; combined edit-and-execute action; per-task output validation; separate completion/execution/correctness metrics

## R35 — Question Answering over Tabular Data with DataBench: A Large-Scale Empirical Evaluation of LLMs

- [Primary source](https://aclanthology.org/2024.lrec-main.1179/)
- Venue/status: LREC-COLING 2024, 13471-13488; peer-reviewed; DOI supplied by CoChat metadata, canonical ACL page has blank DOI field
- Read: CoChat full_text truncated near 50000 chars; data collection/full-vs-lite versions, code-vs-context prompting, evaluation and relaxed matching read; primary ACL page cross-check
- Supports: Code-based prompting uses schema instead of the full table; 65 datasets/1300 questions are supplied, but main reported experiments use first-20-row DataBench_lite and relaxed matching.
- Limits: Do not cite main comparison as full-data scalability evidence or strict serialization accuracy. English datasets and historical models differ from DataMate.
- Transfer: schema-to-code interface; answer-type stratification; explicit full-data versus sampled-data evaluation separation; typed direct serialization
