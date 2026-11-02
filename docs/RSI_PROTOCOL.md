# RSI protocol: cải tiến có giới hạn trước freeze

RSI được hiểu là recursive self-improvement của **hệ thống phát triển**: proposer tạo thay đổi, evaluator kiểm tra, giữ champion tốt hơn rồi lặp. Không tuyên bố intelligence tăng vô hạn; runtime test không tự sửa model, global prompts, playbook hay threshold.

## Cơ chế chọn từ paper

- [GEPA](https://arxiv.org/abs/2507.19457): reflective prompt search từ trace, screening rẻ và giữ candidate đa dạng.
- [ACE](https://arxiv.org/abs/2510.04618): lessons dạng item, scope/preconditions, cập nhật delta thay rewrite làm mất ngữ nghĩa.
- [AHE](https://arxiv.org/abs/2604.25850): manifests có dự đoán fix/regression, traces có thể truy nguồn; đo outcome thay tin self-justification.
- [DGM](https://arxiv.org/abs/2505.22954): parented archive và rollback.
- [AlphaEvolve](https://arxiv.org/abs/2506.13131): cheap-to-expensive evaluation cascade.
- [AFlow](https://arxiv.org/abs/2410.10762): search grammar workflow nhỏ thay graph tùy ý.
- [Reflexion](https://arxiv.org/abs/2303.11366): repair khi có feedback đáng tin; self-generated tests có thể sai.

Đây là adaptation theo DataMate, chưa tái hiện benchmark của paper. Không dùng headline gains từ frontier models để dự đoán gain của ≤15B.

## Trust boundary

**Read-only với optimizer:** scorer/labels, rulebook/calendar, partitions, model eligibility/config, resource caps, final output contract và promotion policy.

**Editable ban đầu:** planner/verifier prompts; scoped validated lessons; bounded routing; deterministic parser/tool wrapper sau canary tests. Thay trọng số hoặc sửa optimizer là campaign riêng có review, không cho tự đổi reward để “tăng điểm”.

Không cho candidate bỏ ví dụ lỗi, kéo dài budget, sửa reference, thêm model vượt cap hay ghi câu trả lời theo IDs. Evaluator chạy ở boundary độc lập với candidate.

## Campaign tối thiểu

~~~mermaid
flowchart TD
    B["Freeze baseline + evaluator + splits"] --> E["Chọn lỗi từ feedback train"]
    E --> P["Đề xuất một patch + hypothesis"]
    P --> S["Static/resource checks"]
    S --> T["Independent deterministic canaries"]
    T --> M["Paired feedback minibatch"]
    M --> V["Selection dev businesses"]
    V -->|"gain thật, không regression"| A["Parented archive / champion"]
    V -->|"không đạt"| R["Reject + rollback record"]
    A --> E
    A --> C["Chọn finalist, khóa harness"]
    C --> K["Calibration riêng"]
    K --> L["Blind audit một lần"]
    L --> F["Cold offline replay + freeze"]
~~~

Ngân sách khởi điểm8–12 edits, một thay đổi có thể quy nguyên nhân mỗi lần. Đây là design choice cần điều chỉnh theo compute, không phải optimum được paper chứng minh. Mỗi campaign dừng theo thời gian/độ cải thiện đã đặt trước; không tìm vô hạn đến khi lockbox tình cờ pass.

Không để reflective editor đọc raw selection/calibration/lockbox answers. Selection metric vẫn có adaptive overfit khi được query nhiều; cap query count và giữ audit thật sự riêng.

## Manifest cho mỗi thay đổi

- Hypothesis và expected error slice.
- Parent/child code, prompt, model, rules, split, scorer và budget hashes.
- Editable files/fields, patch digest, source-paper rationale.
- Expected fixes, possible regressions và canaries.
- N/C/W/A, PA/gap/coverage; paired transitions và per-business slices.
- Load-inclusive runtime, tool/token/retry counts, peak memory.
- Evaluator verdict, promotion/rejection reason và rollback reference.

Private traces chứa question/data không đi lên GitHub. Public docs chỉ ghi aggregate được phép và methodology.

## Lesson schema

Lesson có ID/version, query classes, preconditions, controlling rule/tool contract, action/check, training evidence refs, positive/negative canaries, helpful/harmful counts, token cost và supersedes/conflicts. Không dùng “luôn bỏ dòng trùng” nếu chưa có quy tắc xác nhận duplicate identity.

Lesson là hypothesis có phạm vi, không được override authoritative rulebook. Retrieve số item hữu ích có giới hạn bằng lexical index trước; không thêm neural embedding chỉ vì paper dùng nó. Freeze playbook toàn cục trước test; business profile mới trong inference chỉ mô tả input đang xử lý.

## Promotion gates

1. Phải qua static/schema/resource và independent correctness canaries.
2. Paired comparison cùng model/input/budget, không đổi metric giữa hai candidate.
3. Net dev PA tăng có evidence; không có critical rule/time/answerability regressions.
4. False repair/false refusal được tính vào damage, không giấu dưới average gain.
5. Runtime còn trong release budget; repeat nếu kết quả không ổn định.
6. Lưu cả thất bại để tránh lặp hypothesis đã bị bác bỏ.

Sau campaign, chọn một champion, calibrate rồi audit. Nếu sửa từ blind audit thì nó thành dev evidence; không tiếp tục gọi kết quả sau sửa là untouched audit.

## Những phần cố ý không làm trước freeze

Không triển khai full open-ended DGM/AlphaEvolve, weight-RSI online, Agent0/SEAL-style self-training chưa có reward/compute đáng tin, hoặc tích lũy test-derived memory. CodeAct loop có thể repair lỗi runtime cụ thể trong giới hạn cố định, nhưng không thay đổi hệ thống đã nộp dựa trên private data.

[Evaluation](EVALUATION.md) xác định authority và leakage boundary; [Roadmap](ROADMAP.md) quyết định lúc cắt campaign.
