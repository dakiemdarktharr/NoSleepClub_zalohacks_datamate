# Competition contract và phần chưa biết

Đọc ngày 02/11/2026 từ [portal DataMate](https://challenge.zalo.ai/portal/datamate/) và [thể lệ chung](https://dl-challenge.zalo.ai/zalo-ai-challenge-regulations-en.pdf). Luật có thể cập nhật; xác minh lại trước release.

- Reward +1 đúng, −1 sai, 0 abstain/missing; PA=(C−W)/N. Unanswerable là prediction có thể đúng/sai, khác abstain.
- Inference offline Docker, network disabled, không human-in-loop hoặc hardcode đáp án theo IDs.
- Tổng mọi inference model ≤15B, gồm auxiliaries và models loaded luân phiên; MoE total. Weights công khai trước 01/10/2026; license phù hợp; quantization được phép.
- Máy chấm 2×RTX5090 32GB, RAM512GB; toàn private ≤6h gồm load. CUDA≥12.8 và build tương thích theo guide BTC.
- Input /data read-only; output /result/submission.jsonl. Rerun Docker của BTC quyết định điểm; |PA uploaded−rerun|≤0.03 là ngưỡng tái lập công bố.
- Training được dùng provided train, dữ liệu tự tổng hợp và public resources hợp lệ; không train/thu answers từ public/private test.
- Freeze Docker 16/11/2026 23:59 GMT+7; private results 23/11 23:59. Public tối đa5 submissions/ngày; Docker tối đa2 lần, chỉ lần cuối tính.
- Private release 20/11: portal guidance/PDF ghi09:00, homepage ghi11:00. Bất nhất chưa giải quyết.

## Data access và evaluator còn thiếu

Data tab đã yêu cầu đăng nhập trong phiên nghiên cứu. Chưa có dataset/devkit/rulebook/calendar/evaluator/Docker guide ở repo; chưa xác minh business/question counts, sizes, actual split isolation, unanswerable ratio, special-type JSON sentinel, null/duplicate/rounding edge cases hoặc base image/log format.

Không thay phần thiếu bằng phỏng đoán. Business-grouped split và budgets trong repo là design choices, không phải mô tả phân phối chính thức. Không có điểm DataMate đã đo.

## Public repository

Repo public theo yêu cầu chủ dự án, chứa tài liệu/code gốc và synthetic examples. Không redistribute data/labels/READMEs/rulebook/calendar/evaluator của BTC, weights, private traces, submissions hoặc paper full text.

Thể lệ8.2 quy định công khai code thi trong thời gian cuộc thi qua forum chính thức để mọi thí sinh truy cập. Khi phát hành code thi thực tế cần đáp ứng kênh đó hoặc làm rõ với BTC; GitHub public riêng không tự chứng minh đã đáp ứng. Chưa gửi forum/email trên danh nghĩa chủ dự án.

Giấy phép MIT trong repo áp dụng nội dung gốc của repo, không cấp lại quyền trên tài liệu, dữ liệu và model của bên thứ ba.
