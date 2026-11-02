# Release và freeze checklist

Chỉ đánh dấu khi có artifact/bằng chứng thật. Chưa có Docker solver hoặc official run ở lần khởi tạo repo này.

## Trước chọn champion

- [ ] Đọc đầy đủ official Data, evaluator, rulebook, calendar, sample submission và Docker guide.
- [ ] Chốt release timestamps/license/exact parameter counts cho mọi checkpoint và adapter.
- [ ] Khóa train/dev/calibration/lockbox theo business/source lineage.
- [ ] Baseline có official C/W/A, per-slice error ledger, code/model/config hashes.
- [ ] Không dùng public/private test answers hoặc score-probing làm feedback.
- [ ] Optional RSI/RLM/LoRA đã qua equal-budget ablation; regressions có quyết định rõ.

## Rehearsal 13–14/11

- [ ] Network disabled, /data read-only, scratch đúng chỗ, output đúng path/schema BTC.
- [ ] Full cold run bao gồm model load, cataloging, tool/verifier/retry và I/O.
- [ ] Tổng ≤6h trên máy tham chiếu; target nội bộ ≤4h48; báo phần cứng nếu khác.
- [ ] Hai lần chạy output-identical hoặc có phân tích sai khác hợp lệ; không chỉ nhìn average PA.
- [ ] Unique IDs/output count; malformed/missing records được accounting.
- [ ] Interrupted run giữ kết quả đã flush; resume chỉ với exact input/config hash nếu guide cho phép.
- [ ] No network downloads/API dependencies; model/resources đã đóng gói.

## Freeze và nộp 15–16/11

- [ ] Source commit, prompts/playbook, routing, calibrator, model, environment và Docker image có hashes.
- [ ] Training/inference code, resources, method và run instructions đầy đủ.
- [ ] Checksum và link tải được BTC kiểm tra; portal receipt lưu private.
- [ ] Không quá2 lần nộp Docker; chỉ thay candidate khi bản mới qua cùng gates.
- [ ] Hoàn thành trước 16/11/2026 23:59 GMT+7, chừa upload buffer.

Sau freeze không sửa dựa trên private questions. Thay đổi hạ tầng ngoài protocol cần được BTC cho phép; permission trong dự án không thay luật thi.

## Công khai

- [ ] Chỉ publish code/tài liệu gốc, bibliography metadata và fixtures synthetic.
- [ ] Không có data/labels/predictions/traces/weights/credentials/source dumps trong current tree hoặc history.
- [ ] Actual contest-code release tuân thủ điều kiện forum chính thức.
- [ ] Mọi score statement ghi split, evaluator, hashes, C/W/A, runtime và giới hạn. Không gọi test utilities là perfect DataMate.

[Roadmap](ROADMAP.md) · [Evaluation](EVALUATION.md)
