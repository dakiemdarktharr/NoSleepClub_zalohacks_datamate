# Nghiên cứu arXiv và quyết định áp dụng

Cập nhật 02/11/2026. Lượt mở rộng đọc methods/evaluation của14 paper về data/context harness và RSI; CHESS/Spider2 được đọc lại sâu hơn. Gộp với nghiên cứu ban đầu thành35 nguồn duy nhất. [Metadata](references.json), [BibTeX](references.bib), [RIS](references.ris) và [annotated bibliography](REFERENCES.md) ghi trạng thái từng nguồn.

Đây là targeted engineering review, không phải systematic review đầy đủ hoặc proof of global novelty. Nguồn discovery CoChat đã được đối chiếu primary arXiv/Anthology/PMLR/OpenReview/proceedings. Nhiều full-text fetch bị cắt khoảng50k ký tự; khi chỉ có abstract đã đọc primary HTML bổ sung. Không tuyên bố đọc mọi phụ lục.

## Kết luận kiến trúc

**Core:** one-model program-executing agent, persistent business catalog, dependency-preserving evidence retrieval, full-data SQL/Python, deterministic semantic kernel và exact output.

**Development loop:** GEPA-style prompt proposals + ACE-style lessons + AHE-style manifests, independent evaluator, staged gates và rollback; freeze một champion.

**Ablation:** RLM bounded route cho context dài; LoRA/curriculum nếu baseline và compute cho thấy cần. Không mặc định recursion hoặc nhiều agent sẽ tăng PA.

## Data/context papers và giới hạn chuyển giao

| Paper | Đã học được gì | Áp dụng / giới hạn |
| --- | --- | --- |
| [Recursive Language Models](https://arxiv.org/abs/2512.24601) — arXiv v3, 2026 | Prompt lớn thành external REPL state, inspect/slice/subcalls; có small-model post-training | Offload state và source handles. Depth0 đôi khi hơn recursion; untrained small model vẫn khó. Không dùng LLM để SUM từng hàng; checkpoint eligibility cần audit riêng |
| [CodeAct](https://proceedings.mlr.press/v235/wang24h.html) — ICML2024 | Executable code compose control/data flow và nhận execution feedback | Bounded persistent tools/repair; tool success không phải semantic correctness |
| [CHESS](https://arxiv.org/abs/2405.16755) — preprint/workshop | Value/catalog retrieval, keys retained khi schema pruning, low-compute route | Lexical first và join dependency closure. Không copy heuristic sửa mọi empty result;0/[] có thể đúng |
| [DAIL-SQL](https://doi.org/10.14778/3641204.3641221) — PVLDB2024 | Compact question/program examples, representation và selection có trade-off token/cost | Training-only example library theo operators; auxiliary models của paper cần budget audit |
| [Spider2](https://arxiv.org/abs/2411.07763) — ICLR2025 | Metadata/documents và multi-step execution là phần của task | Toolset tách inspect schema/sample/doc/execute; enterprise cloud workload không phải DataMate |
| [DA-Code](https://aclanthology.org/2024.emnlp-main.748/) — EMNLP2024 | Replayable action-observation và artifact evaluation | Theo dõi completion, executable và correct riêng. Chạy hết không có nghĩa đúng |
| [DataBench](https://aclanthology.org/2024.lrec-main.1179/) — LREC-COLING2024 | Schema-to-code interface và answer-type coverage | Main comparison dùng bản lite20rows và relaxed matching; không lấy đó làm chứng cứ scale/full-data/exact-serialization |

## RSI/harness papers và quyết định

| Paper | Cơ chế đáng lấy | Điều không suy diễn |
| --- | --- | --- |
| [GEPA](https://arxiv.org/abs/2507.19457) — ICLR2026 | Reflective prompt evolution, trace feedback, staged selection; có nhánh Qwen3-8B | Kết quả benchmark không là forecast DataMate; repeated validation vẫn overfit |
| [ACE](https://arxiv.org/abs/2510.04618) — ICLR2026 | Itemized lessons, delta updates, Generator/Reflector/Curator | Headline experiments dùng model rất lớn; chỉ áp offline curated playbook, không online test learning |
| [AFlow](https://arxiv.org/abs/2410.10762) — ICLR2025 | Workflows-as-code, search trong operator grammar | Chỉ thử grammar nhỏ, cap retries; không chạy full MCTS/API pipeline mặc định |
| [Darwin Godel Machine](https://arxiv.org/abs/2505.22954) — ICLR2026 listing | Parented candidate archive, giữ stepping stones và rollback | Không phải proof tự cải tiến; coding benchmark khác nghiệp vụ Việt, full campaign quá nặng |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) — white paper | Evaluator tự động, editable blocks, cheap-to-expensive cascade | Exact mathematical validator không tự trở thành oracle cho business QA |
| [Agentic Harness Engineering](https://arxiv.org/abs/2604.25850) — preprint2026 | Layered traces, change manifests và falsifiable regression hypotheses | Editor có thể dự đoán sai regression; trust measured gates, không trust self-attribution |
| [Reflexion](https://arxiv.org/abs/2303.11366) — NeurIPS2023 | Bounded feedback-driven repair, validated development lessons | Self-generated tests có false positives; không dùng lời tự chấm làm authority |

Publication years trong bibliography có thể là first arXiv posting year; venue/status chỉ rõ bản hội nghị được xác minh. Metadata discovery không tự quyết định peer-reviewed status. DOI DataBench chưa được canonical page xác nhận nên không dùng.

## Các prior art quyết định novelty của DataMate

- [ProSPy](https://arxiv.org/abs/2606.05836) đã có profiling/DSL/SQL views/Python; [EntSQL](https://arxiv.org/abs/2606.03363) đã có business-document grounding. Vì vậy generic semantic layer không mới.
- [DPC](https://aclanthology.org/2026.acl-long.313/), [SQLDriller](https://doi.org/10.1145/3725271) và [TestSuiteEval](https://aclanthology.org/2020.emnlp-main.29/) đã có counterexample/test-database verification.
- [RTS](https://doi.org/10.1145/3709719), [TrustSQL](https://arxiv.org/abs/2403.15879) và [Sentinel](https://arxiv.org/abs/2610.04156) đã có reliability/abstention/gating.
- [Certain answers](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICDT.2015.94) là nền tảng lâu đời. Contribution tiềm năng là evidence sufficiency có phạm vi rõ qua raw-file normalization và luật Việt.
- [ViText2SQL](https://aclanthology.org/2020.findings-emnlp.364/) và [Vietnamese TemporalQA](https://jcsce.vnu.edu.vn/index.php/jcsce/article/view/6505) giúp chọn diagnostic tiếng Việt, không chứng minh model mới giải đúng dữ liệu lộn xộn/lịch âm của đề.

Mức mới và gain chưa được xác nhận trên DataMate. Thực nghiệm phải so matched-model/budget với closest baseline, tách generation gain khỏi selection gain và false-repair damage.

## Vì sao hướng này có cơ hội tiến tới điểm tối đa

Một câu sai có thể xuất phát từ nhiều tầng: ingest, schema/entity, business meaning, time, join/grain, program, verifier hoặc serialization. Thêm candidate không sửa được lỗi raw parser mà mọi candidate cùng dùng. Do đó ưu tiên error taxonomy + exact kernel + oracle ladder, rồi mới search.

PA=1 cần zero wrong và zero abstain. Pass@K hoặc successful execution chỉ đo tầng trung gian. [Evaluation protocol](EVALUATION.md) giữ denominator đầy đủ và tách correctness/coverage debt; [RSI protocol](RSI_PROTOCOL.md) buộc mọi thay đổi qua evaluator độc lập.

## Phạm vi tìm kiếm

Chủ đề chính: external-context data agents; schema/value retrieval; executable tool actions; large-table QA; test-time search; reflective prompt optimization; agentic context; automatic harness evolution. Phạm vi chính2023–02/11/2026, thêm nền tảng2015/2020.

Ví dụ queries: Recursive Language Models; Executable Code Actions Elicit Better LLM Agents; CHESS; DAIL-SQL; DA-Code; DataBench; GEPA reflective prompt evolution; ACE; AFlow; Darwin Godel Machine; AlphaEvolve; Agentic Harness Engineering; Reflexion.

Loại broad irrelevant hits và secondary summaries khỏi bằng chứng kỹ thuật. SEAL, Agent0 và Self-Refine được screen abstract cho follow-up, không tính vào14 bài đã đọc methods/eval. Một số database CoChat không trả lời; không khẳng định review exhaustive.

Chỉ bibliography/ghi chú tổng hợp được công khai. Không copy full-text PDFs, BTC data/rulebook/evaluator hoặc private reasoning traces. [Roadmap](ROADMAP.md) biến các kết luận này thành milestones cụ thể.
