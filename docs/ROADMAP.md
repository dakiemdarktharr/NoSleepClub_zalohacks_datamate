# Roadmap phát triển đến freeze

Cập nhật 02/11/2026, GMT+7. Đây là kế hoạch thực thi, không phải các milestone đã hoàn thành. Tình trạng implementation xem [FEATURES](FEATURES.md).

## Mục tiêu và đường đi

PA = (C − W)/N = 1 − (2W + A)/N. Mục tiêu PA = 1 đòi C = N, W = A = 0, kể cả nhận đúng lớp unanswerable. Giảm câu sai trước, sau đó nâng coverage bằng khả năng mới đã kiểm chứng. Không ép trả lời khi bằng chứng không đủ để làm đẹp coverage.

Đường găng: **official data/evaluator → ingest đúng → semantic baseline → error analysis → cải tiến có kiểm chứng → cold offline Docker → freeze**. RSI, nhiều candidate và RLM chỉ được giữ khi tăng PA trong cùng ngân sách.

## Các mốc 02–16/11/2026

| Ngày | Deliverable | Điều kiện hoàn tất | Phụ thuộc / fallback |
| --- | --- | --- | --- |
| 02/11 | M0: repo, nghiên cứu, access register | Repo public chỉ có code/tài liệu gốc; đọc Data/devkit/evaluator/Docker guide, khóa schema và phiên bản | Repo và foundation đã có. Official artifacts chưa truy cập; tiếp tục synthetic, không công bố điểm thi |
| 03–04/11 | M1: nền dữ liệu | CSV/XLSX/SQLite ingest có provenance; profile layout, dates, decimals, units, keys; rule/calendar primitives có fixtures | Cần file/rulebook thật. Thu hẹp theo format thực tế, không xây ETL tổng quát |
| 05–06/11 | M2: baseline end-to-end | Một checkpoint hợp lệ; typed plan → SQL/Python → output; adapter chạy evaluator BTC; C/W/A và trace lỗi đầu tiên; chạy lặp tái lập | Không có official scorer thì chỉ báo synthetic. Bỏ fine-tuning khỏi đường găng |
| 07–08/11 | M3: semantics và verification | Kiểm tra entity, kỳ thời gian, rule, join/grain; answerability; verifier phát hiện lỗi SQL chạy được nhưng sai | So ablation cùng model/budget. Giữ check rẻ có net gain; bỏ false rejection |
| 09–10/11 | M4: cải tiến có giới hạn | Error curriculum trên training, prompt/playbook search, 2–3 candidate khi cần; từng thay đổi có hypothesis và regression report | 8–12 candidate edits là ngân sách khởi điểm. Cắt nhánh sau 24–36h không có tiến bộ đáng tin; optional LoRA/RLM không được chặn release |
| 11/11 | M5: calibration và budget | Chọn một champion, khóa routing/budget; fit threshold trên nhóm calibration độc lập; PA–coverage curve; profile end-to-end | Nếu calibration không giúp, giữ policy đơn giản. Không đoán độ tin cậy từ lời model tự khai |
| 12/11 | M6: blind audit | Một lần trên lockbox business chưa dùng để sửa; ghi C/W/A, slices, config/model/code hashes | Nếu sửa từ lỗi lockbox, set đó không còn untouched. Dùng nhóm mới nếu còn; báo giới hạn nếu không |
| 13–14/11 | M7: rehearsal | Docker đúng guide, network disabled, data read-only; cold run hai lần; output count/schema; target nội bộ ≤4h48 trên máy tương đương | Limit chính thức 6h gồm load. Tắt optional search khi quá ngân sách rồi đánh giá lại |
| 15/11 | M8: release candidate + dự phòng | Source/model/prompt/calibrator/image bound bằng hash; checksum, downloadability, README, giấy phép; nộp candidate sớm nếu được | Tối đa hai lần nộp Docker. Giữ champion đã pass thay vì thêm feature mới |
| 16/11 trước 23:59 | M9: freeze | Artifact cuối đủ train/infer/resources/docs; checksum và receipt local; exact configuration khóa | Không thay đổi chưa kiểm thử phút cuối. Chừa thời gian upload và kiểm tra BTC tải được |

Mốc freeze và giới hạn lấy từ [portal](https://challenge.zalo.ai/portal/datamate/) và [thể lệ](https://dl-challenge.zalo.ai/zalo-ai-challenge-regulations-en.pdf). Giờ mở private 20/11 đang có bất nhất 09:00/11:00 giữa các trang; xem [CONSTRAINTS](CONSTRAINTS.md).

## Phân vai và bàn giao

| Vai | Trách nhiệm | Artifact bàn giao |
| --- | --- | --- |
| Data/Rule Steward | Ingest, provenance, entity/rule/calendar, phát hiện unknown | Catalog, contract, fixtures, coverage report |
| Agent Engineer | Shared backbone, planner/executor, bounded repair | Runnable baseline, typed plans, latency breakdown |
| Harness/RSI Engineer | Trace, candidate archive, prompt/lesson proposals | Parent/child manifests, expected fixes, rollback |
| Evaluator/Reality Checker | Immutable scorer, grouped evaluation, independent checks | C/W/A, slices, regression/selection regret, promotion verdict |
| Release Owner | GPU/Docker, reproducibility, freeze/submission | Image/checksums, exact runbook, receipt |

Đây là các vai công việc, không bắt buộc năm người hoặc năm model. Một người có thể thực hiện tuần tự; mọi vai inference dùng chung checkpoint đủ điều kiện.

## Gate để một feature được giữ

1. Không vi phạm input/rule semantics, offline/model budget hay giới hạn thời gian.
2. Không làm hỏng canary quyết định được bằng tính toán độc lập.
3. So parent/child trên cùng dev businesses và ngân sách; đo wrong→right, right→wrong và wrong→abstain.
4. Tăng PA phải đi cùng slices và ước lượng bất định theo business nếu đủ mẫu. Lợi ích quá nhỏ/nhiễu được ghi provisional.
5. Không có critical regression về answerability, calendar, grain hoặc output.
6. Cold-run budget còn headroom. Feature không giúp thì rollback; không giữ vì tên công nghệ hấp dẫn.

## Ba lựa chọn triển khai

| Lựa chọn | Ưu tiên | Cut rule |
| --- | --- | --- |
| CodeAct + catalog + deterministic semantic operators | Must | Giữ baseline đơn giản nhất chạy đúng |
| Verifier/evidence sufficiency + calibrated routing | Must bản hẹp, Should bản sâu | Giảm scope nếu false reject xóa gain |
| GEPA/ACE-style RSI, RLM, LoRA | Should | Chỉ giữ khi có measured dev gain và nằm trong hạn |

Sau freeze, chạy hệ thống đã nộp và lưu bằng chứng; không thêm lessons, sửa threshold hoặc train theo private questions. Sau cuộc thi mới mở lại nhánh nghiên cứu lớn, theo quyền sử dụng dữ liệu.
