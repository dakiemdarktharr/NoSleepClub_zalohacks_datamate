# NoSleepClub_zalohacks_datamate

Nghiên cứu và nền phát triển data agent tiếng Việt cho **Zalo AI Challenge 2026 — DataMate**.

**Mục tiêu:** tối đa hóa Penalty Accuracy, hướng tới PA = 1 bằng cơ chế có thể kiểm chứng. Chưa có kết quả DataMate chính thức; đây là repo khởi tạo gồm roadmap, kiến trúc và utilities cho harness, chưa phải solver thi hoàn chỉnh.

## Thiết kế đã chọn

- Một backbone đủ điều kiện, dùng chung cho planner, code generator và critic.
- Giữ bảng lớn ngoài context: catalog + truy xuất bằng chứng, SQL/Python tính trên toàn phần dữ liệu liên quan.
- Contract có kiểu cho nghiệp vụ Việt, grain, entity, đơn vị, thời gian và output.
- Phân biệt dữ liệu thiếu với số 0/tập rỗng; quyết định value / unanswerable / abstain theo bằng chứng.
- RSI **trước freeze**: GEPA-style prompt search, ACE-style lessons có phạm vi, trace và regression gate. Inference cuối dùng artifact cố định.
- RLM chỉ là ablation có giới hạn cho tài liệu/context dài, chưa chọn làm đường chạy mặc định.

## Đọc theo thứ tự

1. [Roadmap đến freeze 16/11](docs/ROADMAP.md)
2. [Kiến trúc, stack và lựa chọn model](docs/ARCHITECTURE.md)
3. [Backlog tính năng và trạng thái](docs/FEATURES.md)
4. [Đánh giá và lộ trình tới PA = 1](docs/EVALUATION.md)
5. [RSI protocol](docs/RSI_PROTOCOL.md)
6. [Nghiên cứu và paper](docs/RESEARCH_REPORT.md)
7. [Ràng buộc cuộc thi và phần chưa xác minh](docs/CONSTRAINTS.md)
8. [Release checklist](docs/RELEASE.md)

## Chạy phần đã có

Python 3.11+, runtime hiện không có dependency bên ngoài. Từ thư mục repo, PowerShell:

~~~powershell
$env:PYTHONPATH = "src"
python -m nosleepclub_datamate --help
python -m unittest discover -s tests -v
python -m nosleepclub_datamate summarize examples/verdicts.synthetic.jsonl --expected-total 5
python -m nosleepclub_datamate validate-models configs/model_manifest.empty.json
~~~

Linux/macOS đặt PYTHONPATH=src cho các lệnh tương ứng. Có thể cài package editable bằng python -m pip install -e . để bỏ bước đặt PYTHONPATH.

Lệnh summarize nhận **verdict đã được evaluator quyết định**, không tự so prediction với gold và không thay thế evaluator BTC. Ví dụ công khai là dữ liệu tổng hợp do dự án tạo; điểm ví dụ không phải điểm thi.

Lệnh validate-models kiểm tra khai báo tham số, ngày phát hành, hash và license, không tự xác minh quyền sử dụng hay tính đúng của khai báo. Manifest rỗng chỉ mô tả trạng thái chưa chọn model; chưa có inference model được tải/cấu hình.

Chia training theo business trước tuning:

~~~powershell
python -m nosleepclub_datamate split PATH_TO_TRAIN_QUESTIONS.jsonl --source-split train --output-dir artifacts/splits --seed nosleepclub-v1
~~~

Đường dẫn trên là đầu vào local của người chạy. Chỉ dùng training được phép; không dùng public/private test để sinh dữ liệu học, thu đáp án hoặc tối ưu prompt.

## Trạng thái

| Hạng mục | Hiện tại |
| --- | --- |
| Research, roadmap, architecture | Đã có tài liệu và nguồn đọc |
| PA summary, model manifest validator, business-grouped split | Utilities nền, có kiểm thử synthetic |
| Ingest CSV/XLSX/SQLite, agent, rule compiler, official scorer adapter | Chưa triển khai; xem backlog |
| Official data/rulebook/calendar/devkit/evaluator | Chưa truy cập được qua phiên nghiên cứu; Data yêu cầu đăng nhập |
| Điểm public/private, inference GPU, Docker thi | Chưa chạy, chưa có số đo |

Theo [portal chính thức](https://challenge.zalo.ai/portal/datamate/), inference offline, tổng mọi model ≤15B, weights công khai trước 01/10/2026, toàn private ≤6 giờ. Freeze Docker **16/11/2026 23:59 GMT+7**. Xác minh lại cập nhật BTC khi triển khai.

Repo chỉ chứa tài liệu/code gốc và fixtures tổng hợp; giữ dữ liệu BTC, weights, kết quả và traces ở local. Điều kiện công khai code thi qua forum chính thức được ghi tại [CONSTRAINTS](docs/CONSTRAINTS.md). Không có quan hệ tài trợ hoặc bảo đảm kết quả từ BTC.
