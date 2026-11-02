# Evaluation: đo khoảng cách tới PA = 1

Đây là protocol cho solver tương lai. Utility hiện tại chỉ tổng hợp verdict do upstream evaluator cung cấp; chưa có evaluator BTC hoặc kết quả DataMate.

## Metric chính và accounting

Với N=C+W+A:

- PA=(C−W)/N.
- Gap=1−PA=(2W+A)/N.
- Coverage=(C+W)/N.
- Selective accuracy=C/(C+W), không xác định khi không trả lời.
- PA=1 chỉ khi C=N, W=A=0. Correct-unanswerable nằm trong C; false-unanswerable nằm trong W.

Wrong→correct cải thiện numerator2; wrong→abstain cải thiện1; abstain→correct cải thiện1. Vì vậy abstention giúp expected PA khi p thấp, nhưng không giải quyết toàn bộ mục tiêu perfect.

Với candidate có xác suất đúng **toàn bộ typed output** p, utility=2p−1; abstain=0. Giữa value và unanswerable, so utility của từng action rồi chọn action dương tốt nhất. p phải được calibration; model tự nói “90% tự tin” không đủ. Missing data không đồng nhất với model uncertainty.

## Authority của evaluator

Giai đoạn M0 phải lấy actual evaluator và sample schema từ tab Data đã xác thực, rồi tạo adapter riêng. Không thay exact typed matching bằng semantic similarity hay LLM-as-judge. Chưa xác định JSON sentinel của unanswerable/abstain hoặc mọi null/rounding edge case, nên repo không cung cấp scorer giả.

Adapter tương lai phải:

1. Đọc input IDs chính thức và predictions, phát hiện duplicate/unknown IDs.
2. Áp đúng reference aliases, types, rounding, ordering và abstention semantics từ BTC.
3. Xuất verdict cho toàn bộ input universe, gồm missing→abstain.
4. Ghi input/prediction/evaluator/code/config hashes và split/source role ở private run manifest.
5. So golden conformance fixtures với actual evaluator, không kiểm vòng tròn bằng code đang tối ưu.

Utility summarize hiện không biết danh sách ID thật; --expected-total giữ denominator nhưng **không kiểm tra membership/verdicthood**. Đây là giới hạn có chủ ý, phải do official adapter đảm nhiệm.

## Tách bốn vai dữ liệu

Chỉ dùng official training được phép:

| Partition | Được dùng làm gì | Không được dùng làm gì |
| --- | --- | --- |
| train | Feedback traces, labels, curriculum, prompt/logic edits | Tự gọi là bằng chứng generalization |
| dev | Repeated champion/challenger selection | Gọi là blind test; đưa labels/content vào optimizer khi đang giữ selection-only boundary |
| calibration | Fit thresholds của champion đã chọn | Sửa candidate code hoặc tìm prompt mới |
| lockbox | Một lần audit sau khi code/threshold khóa | Repeated peek hoặc sửa rồi tiếp tục gọi untouched |

Split utility giữ business chung một partition. Parent/child synthetic, export variants và template families cần lineage grouping bổ sung; utility hiện chưa phát hiện duplicates giữa business IDs khác nhau. Tỷ lệ60/20/10/10 là mặc định hash assignment, không bảo đảm cân bằng hoặc nonempty trên bộ nhỏ. Sau khi biết size/domain, quyết định grouped folds và lockbox khả thi trước tuning.

Business ID quyết định membership cùng seed; content hash phục vụ audit, không được khiến một business chuyển nhóm khi sửa/thêm câu hỏi. Mọi thay đổi manifest là version mới, không overwrite; không thử nhiều seed rồi chọn split dễ.

Public/private test không dùng để học, thu answers, tạo lessons hay reverse-engineer labels qua scoreboard. Per-business profiling khi inference là đọc input của frozen program, không phải quyền cập nhật model/playbook xuyên test.

## Oracle ladder trên development

| Tầng | Diagnostic | Khoảng lỗi được đo |
| --- | --- | --- |
| 0 | Official output/schema conformance | Lỗi I/O, type, missing/duplicate IDs |
| 1 | Gold normalized facts nếu có hoặc synthetic independent oracle | Ingest/layout, locale/date/unit parsing |
| 2 | Gold entities/time/rule/join/plan trên training-only diagnostic subset | Hiểu câu hỏi và business semantics |
| 3 | Gold executable program trên ingested facts | Executor/numeric/serializer |
| 4 | Candidate oracle@K/pass@K | Correct candidate có xuất hiện không |
| 5 | Actual selected top1 | Verifier/selector regret |
| 6 | Final three-way decision | PA/coverage/answerability/calibration |

Nếu BTC không cung cấp gold plans, chỉ annotate training subset hợp lệ hoặc dùng synthetic có chương trình known. Không tạo oracle cho test questions. Pass@K=100% không có nghĩa top1/PA=1; selector không thể chọn đáp án đúng vốn không có trong pool.

## Failure ledger

Mỗi W/A cần một nhãn có evidence: ingest/header; entity; decimal/unit; time/calendar; business rule/scope; join/grain; code/execution; candidate selection; evidence/answerability; output/type; budget/runtime. Gom theo business và query family, không fix theo ID.

So sánh parent/child paired trên cùng businesses: wrong→right, right→wrong, wrong→abstain, abstain→right. Track false-unanswerable và fabricated values on true-unanswerable riêng. Chỉ có execution success, completion hoặc đồng thuận nhiều SQL là chưa đủ.

## Ablation được ưu tiên

A0: one-model CodeAct/full-schema baseline.
A1: +catalog/value retrieval với dependency closure.
A2: +raw provenance/cache/semantic primitives.
A3: +typed contract và exact serializer.
A4: +evidence/semantic verification.
A5: +bounded candidate search/calibration.
A6: +offline RSI-selected prompt/playbook.
A7: optional RLM depth0 vs depth1 hoặc LoRA.

Giữ model và budget so sánh; nếu thay model phải báo thành experiment khác. Báo oracle@K, actual@1, PA và toàn pipeline runtime, không chỉ token speed.

## Scale và release gates

Size BTC chưa biết. Stress grid đề xuất, dùng synthetic và không gọi là scale của đề: 10³/10⁵/10⁶ rows;10/100/1000 columns; một sheet/multi-sheet/linked files; cold catalog vs warm reuse. Đo bytes scanned, spill, exact results, dependency recall, peak RAM/VRAM, tokens và p50/p95/max latency. Broad fallback khi schema pruning không đủ bằng chứng.

T_load+ΣT_catalog+ΣT_question+T_output≤21,600 giây; internal target17,280. Pin evaluator/model/config/input/software/hardware; cold Docker network-disabled đúng guide và hai lần replay. Byte-identical output là target mạnh hơn ngưỡng PA tolerance; không mặc định seed bảo đảm deterministic GPU.

Một score statement hợp lệ phải có split rõ, artifact hashes, evaluator, N/C/W/A, runtime/compute, cách dùng labels và những giới hạn còn lại. Public PA=1 nếu đạt chỉ chứng minh submission đó trên public, không chứng minh private perfect.
