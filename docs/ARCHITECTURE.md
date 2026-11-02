# Kiến trúc đích

**Trạng thái:** thiết kế chưa triển khai solver. Foundation utilities đã có; xem [FEATURES](FEATURES.md).

## Runtime: một model, dữ liệu ngoài context

~~~mermaid
flowchart LR
    R["CSV / XLSX / SQLite + README"] --> I["Ingest giữ raw và provenance"]
    I --> C["Catalog + keys + units + lexical index"]
    Q["Câu hỏi + as_of_date"] --> P["Planner dùng shared model"]
    C --> P
    B["Rulebook + solar/lunar mapping"] --> S["Semantic/calendar primitives"]
    S --> P
    P --> T["Typed query contract"]
    T --> X["SQL / Python trên dữ liệu đầy đủ"]
    X --> V["Checks: grain, rules, evidence, output"]
    V --> D["Value / unanswerable / abstain"]
    D --> O["Durable JSONL writer"]
    V -->|"lỗi cụ thể, còn budget"| P
~~~

Prompt nhận catalog và evidence slices; không serialize toàn bảng vào token context. Preview để hiểu layout/schema, **không dùng sample để tính final aggregate**. Số dòng/cột BTC hiện chưa biết; benchmark scale là kiểm chứng thiết kế, không phải mô tả bộ đề.

## Các tầng và giao diện

| Tầng | Trách nhiệm / đầu ra | Điều kiện quan trọng |
| --- | --- | --- |
| Ingest | Layout-aware readers; raw cells, parsed values, parse errors, source coordinates | Không silently drop rows/columns, không tự cho missing=0; phân biệt subtotal với giao dịch |
| Canonical storage | Typed views/Parquet trên scratch, read-only input | Chuẩn hóa có thể truy ngược, invalidate cache theo nội dung |
| Catalog | Schema, keys, grain, units, time range, null/error counts, value aliases | Không coi sample profile là chứng minh completeness |
| Evidence retrieval | Lexical index + exact values + có thể character n-grams; giữ join-key/dependency closure | Thiếu bằng chứng thì broaden schema; tránh pruning mất bảng nối |
| Semantic layer | Entity codes, rule clauses, time intervals, status/returns/cost/debt operators | Precedence README/rulebook phải lấy từ tài liệu thật; conflict không tự override |
| Planner | Contract có kiểu và trạng thái unresolved | Không bù định nghĩa nghiệp vụ thiếu bằng world knowledge |
| Execution | Bounded SQL/Python, materialized intermediate handles, structured errors | Tính trên toàn query scope; time/memory limits và scratch riêng |
| Verification | Type/grain/unit checks, alternate derivations, independent recomputation/witnesses | SQL và Python cùng kết quả chưa chứng minh cùng hiểu đúng |
| Decision | Value / verified-unanswerable / epistemic-abstain | Empty/zero có thể đúng; parser disagreement không phải unanswerable |
| Output | Schema theo official sample; flush từng record, input/config-bound resume | Không đoán omitted-vs-null ở special types; chờ evaluator/devkit |

Typed contract tối thiểu: answer type; metric; population/scope; entity codes; join path và cardinality; observation grain; time interval + calendar; predicates/status rules; aggregation/ranking; units/rounding; evidence dependencies; ordering; unresolved fields.

Cache key gồm raw-content, reader/version, rule/calendar, relevant configuration và model/prompt version nếu artifact phụ thuộc model. Không cache đáp án định sẵn bằng question/business IDs. ID được dùng cho mapping output và chia validation group, không làm quy tắc trả lời.

## Stack và quyết định

- Python là orchestration và semantic kernel. Utilities hiện dùng stdlib; dependencies runtime solver sẽ được pin sau M0.
- DuckDB là ứng viên query engine cho CSV/Parquet và analytical SQL; SQLite giữ read-only adapter. Query pushdown tránh đưa bảng lớn vào model.
- openpyxl read-only là ứng viên ingest XLSX. Ghi rõ formula và cached value: data_only đọc giá trị Excel lưu lần trước, không tự recalculation. Worksheet dimensions có thể sai, cần kiểm tra. [Tài liệu chính thức](https://openpyxl.readthedocs.io/en/stable/optimized.html), [load_workbook](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html).
- In-process local model engine là lựa chọn đầu khi Docker tắt network. Không mặc định cần loopback HTTP server. Đọc guide BTC trước khi chốt vLLM/PyTorch/CUDA build.
- Context và intermediate tables được lưu ngoài prompt; code trả handles, schema/counts và slice liên quan. Full-data query kết thúc ở executor.
- Không thêm neural embedding/reranker khi lexical retrieval đủ. Mỗi learned component đều tính vào cap.

Đánh đổi: modular monolith dễ profiling/reproduce trong hai tuần; không xây microservices, vector DB hoặc UI nếu không tăng điểm. Python generic code linh hoạt nhưng khó kiểm soát hơn typed primitives; ưu tiên primitives thường dùng, code route cho phần thực sự cần.

## Model: lựa chọn thay thế, chưa chọn winner

| Ứng viên | Bằng chứng đang có | Vai trò thử nghiệm |
| --- | --- | --- |
| Qwen/Qwen3-8B | Model card ghi 8.2B tổng, Apache-2.0 | Baseline nhanh để đo whole pipeline |
| Qwen/Qwen3-14B | Model card ghi 14.8B tổng, Apache-2.0 | Challenger quality/latency, dùng duy nhất checkpoint này |
| mit-oasys/rlm-qwen3-8b-v0.1 | Card MIT, trained với scaffold cố định của RLM | Nhánh RLM riêng nếu context dài thật sự là bottleneck |

Nguồn: [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B), [Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B), [MIT OASYS RLM](https://huggingface.co/mit-oasys/rlm-qwen3-8b-v0.1).

Đây là candidate shortlist, chưa audit checkpoint-level release timestamp/hash, chưa tải và chưa benchmark. Thời điểm paper không thay cho bằng chứng weights public trước cutoff. Count chính xác từ checkpoint trước freeze; con số model-card làm shortlist. Hai model 8.2B cộng lại đã vượt 15B; không dùng ensemble hai checkpoint này. Quantization giảm bộ nhớ, không đổi số tham số. Adapter/auxiliary components phải khai báo bảo thủ.

Shared weights phục vụ nhiều vai; compare thinking/non-thinking và bounded tokens bằng actual PA/runtime. Không mặc định greedy decoding là đúng cho mọi checkpoint. Pin decoding/seed và đo reproducibility theo engine/hardware.

## Compute policy

Một route rẻ trước: catalog → một plan → execution → deterministic checks. Chỉ mở candidate khác khi có tín hiệu cụ thể như alias conflict, join path, date boundary hay failed check. Hard caps cho tool calls, repairs, generated tokens và global wall time được đặt sau profiling thực.

RLM depth-zero là baseline bắt buộc; depth-one là ablation. Không scan từng hàng bằng semantic subcalls để thay SQL SUM/COUNT. Recursive state phải dùng cùng model hợp lệ, giữ source locations, giới hạn depth/calls và dừng khi không thêm bằng chứng. [RLM paper](https://arxiv.org/abs/2512.24601).

T_load + tổng T_catalog(business) + tổng T_question + T_output ≤21,600 giây. Mục tiêu nội bộ 17,280 giây tạo 20% headroom; chưa có N/B và phần cứng thực để ước lượng throughput.

## ADR ngắn

- **Accepted:** one-backbone, data-outside-context, deterministic arithmetic/calendar, official evaluator as authority.
- **Accepted:** development-time RSI; frozen runtime strategy.
- **Proposed:** DuckDB/openpyxl adapters, typed primitive DSL, risk-triggered multi-candidate search.
- **Experimental:** RLM route, LoRA, interval/top-k sufficiency certificates.
- **Deferred:** model portfolio, broad RL/self-training, open-ended harness self-modification, product UI.

Các cơ chế CodeAct/catalog/DSL/verification có prior art. Contribution cần đo là composition theo nghiệp vụ Việt, evidence sufficiency và gain under constraints, không phải tên agent mới.
