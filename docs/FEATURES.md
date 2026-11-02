# Feature backlog và trạng thái

Cập nhật 02/11/2026. **Done** chỉ nghĩa chức năng đã triển khai/kiểm thử như mô tả, không suy ra hệ thống thi đã hoạt động.

Bản v0.2.1 đã sửa lỗi ingestion, scope/ngày/số tiền, JSONL và evaluator theo [báo cáo audit](AUDIT_2026-11-02.md). File baseline đầu vẫn gắn với source v0.2.0; chưa dùng điểm của file cũ để đánh giá các sửa lỗi mới.

| Ưu tiên | Feature | Trạng thái | Definition of done |
| --- | --- | --- | --- |
| P0 | PA verdict summary | Done | C/W/A, missing→abstain, denominator cố định, gap/coverage, reject duplicates/invalid records |
| P0 | Model declaration validator | Done | Positive integer count, total≤15B, cutoff date, hash/license declarations, duplicate checkpoint detection |
| P0 | Training-only grouped split | Done | Same business không tách partitions; deterministic hashes; source declaration; no-overwrite output |
| P0 | CLI + unit/integration tests | Done | Ba utilities chạy trên Python3.11, synthetic E2E và edge cases |
| P0 | Official artifact register | Partial | Train/public data, rulebook và calendar đã tải, hash private; chưa có evaluator BTC trong gói |
| P0 | Official evaluator adapter | Planned | Gọi evaluator BTC, xác nhận type/matching/sentinel semantics, xuất verdicts; không dùng proxy thay authority |
| P0 | CSV reader | Partial baseline | Có encoding/delimiter/header heuristics và row provenance; chưa đạt đầy đủ ledger/invariants |
| P0 | XLSX reader | Partial baseline | openpyxl đọc nhiều sheet, cached values; chưa xử lý mọi layout/formula/merged header |
| P0 | SQLite reader | Partial baseline | Kết nối read-only, đọc table/schema; chưa có join planner tổng quát |
| P0 | Raw provenance + catalog cache | Planned M1 | File/sheet/row/key→canonical; content invalidation; no ID-keyed answers |
| P0 | Vietnamese entities/aliases | Planned M1–M2 | Code-anchored names, pack/unit collisions checked, ambiguous matches preserved |
| P0 | Rule compiler | Planned M1–M3 | Actual definitions/status/returns/cost/debt thành tested primitives, source clause attached |
| P0 | Deterministic dates/lunar mapping | Planned M1–M3 | as_of_date only; actual rulebook week/period definitions; boundary fixtures |
| P0 | Typed plan + full-data executor | Planned M2 | SQL/Python on full scope; validated contract; structured observations and bounded scratch |
| P0 | Join/grain/unit invariants | Planned M3 | Key multiplicity/cardinality and amount/unit checks catch wrong-but-executable plans |
| P0 | All official output types | Planned M2 | Exact schema confirmed, ordered list, dates, percent scale/sign, Unicode/diacritics |
| P0 | Evidence/answerability policy | Planned M3 | Zero/empty≠missing; alternate derivations; unanswerable≠model uncertainty |
| P0 | Checkpoint writer/resume | Planned M2 | Durable unique records; resume binds input/config; partial output handled by actual guide |
| P0 | Reproducible baseline/error ledger | Planned M2 | Official dev C/W/A by business/type/root cause, repeated run and hashes |
| P0 | Offline Docker/cold-run | Planned M7 | Guide-compliant image, no network, input read-only, two full replays, load-inclusive time |
| P1 | Semantic verifier | Planned M3 | Independent critical recomputation catches scope/rule errors; false accepts/rejects measured |
| P1 | Rule-grounded metamorphic tests | Planned M3–M4 | Declared applicability and independent expected relation; ingest→answer lineage |
| P1 | Bounded candidate search | Planned M4 | Distinct plan hypotheses, pass@k vs top1, net PA/second gain |
| P1 | Calibration + adaptive budget | Planned M5 | Separate groups, exact-output correctness, PA–coverage curve, runtime headroom |
| P1 | GEPA-style prompt optimization | Planned M4 | Immutable evaluator, one edit/manifest, bounded campaign, champion/challenger rollback |
| P1 | ACE-style scoped lessons | Planned M4 | Preconditions/rule source/canaries/token cost; no test-derived memory |
| P1 | Training-only synthetic curriculum | Planned M4 | Known independent oracle, lineage grouped by source/template, no leakage |
| P2 | RLM route for long context | Experimental | Beats depth-zero/code route on relevant dev slice within global budget |
| P2 | Restricted interval/top-k certificate | Experimental | Sound assumptions in explicit query fragment, no invented finite bound |
| P2 | LoRA/distillation | Optional | Legal train data/weights, held-out gain, full parameter/license audit |
| Later | Broad RL, open-ended RSI, product UI | Deferred | Reconsider after competition; not a freeze dependency |

Có baseline giới hạn ở [BASELINE_QUERY_V1](BASELINE_QUERY_V1.md) và [BASELINE_RUN](BASELINE_RUN.md): query interpreter có điều kiện, runner gắn hash/input và local matching proxy. Đây chưa hoàn thành các mục rule compiler, full-data executor hay agent tổng quát trong backlog. Các kiểm thử dùng fixtures synthetic; train validation dùng dữ liệu private. Tests không chứng minh điểm thi hoặc performance GPU.
