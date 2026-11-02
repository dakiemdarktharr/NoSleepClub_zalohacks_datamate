# Baseline tính toán trực tiếp v1

Baseline đầu tiên dùng Python trên dữ liệu được phát hành, không có inference model hoặc API suy luận. Mục đích là có một lượt chạy có thể tái lập và đo điểm đầu tiên. Kiến trúc agent, backbone và RSI trong roadmap vẫn là việc tiếp theo.

## Đầu vào và thực thi

`baseline_data.load_business` đọc riêng thư mục business. Bộ đọc hỗ trợ CSV, XLSX qua openpyxl và SQLite read-only; dùng tên cột và mô tả trong README để tạo các dòng bán, đơn, sản phẩm và provenance. Có xử lý một số cách ghi ngày, số, dòng trùng cùng đơn, metadata để trống trong nhóm và trả hàng toàn đơn. Đây là các heuristic có kiểm thử, chưa phải bộ đọc mọi định dạng.

`baseline_query.solve_question` nhận câu hỏi, dữ liệu business và policy lấy từ rulebook của chính split. Chỉ một fragment của ngôn ngữ và nghiệp vụ được hỗ trợ. Xem [phạm vi chi tiết](BASELINE_QUERY_V1.md). Diễn giải chưa nhận diện, ngày/trạng thái không chắc chắn hoặc dữ liệu không phù hợp dẫn tới abstain. Unanswerable chỉ dùng khi có cơ sở về khoảng phủ được khai báo; không coi parser thất bại là chứng minh dữ liệu thiếu.

Runner không đọc reference answers. Nó xử lý từng business rồi giải phóng bộ nhớ, giữ thứ tự câu hỏi ban đầu trong file kết quả. Nó yêu cầu tập ID đầu ra bằng tập ID đầu vào, kiểm tra kiểu JSON cơ bản, từ chối ghi đè run cũ, xuất `submission.jsonl`, `logs/questions.jsonl` và `manifest.json`. Manifest ghi hash của questions, rulebook, calendar, business files, các module Python và kết quả. Nó từ chối finalize nếu code thay đổi trong lúc chạy. Logs có ID, final answer, thời gian và loại lỗi; chưa có semantic proof đầy đủ cho mỗi phép tính.

~~~powershell
python -m pip install .
python -m nosleepclub_datamate.baseline_run PATH_TO_SPLIT --output-dir PATH_TO_NEW_PRIVATE_RUN
~~~

Không lưu input hoặc các artifacts này trong GitHub public. Runner không có resume, không tính correctness và không tự submit lên portal.

## Đo ở local

`baseline_eval` chỉ nhận source-split train, chia theo business bằng hash có seed cố định và đóng băng membership trước điểm đo. Nó so prediction với nhãn train theo một proxy có kiểu, aliases, ordered list và unordered table, rồi xuất C/W/A/PA theo mẫu số đầy đủ. Proxy không có quyền quyết định điểm chính thức. Dữ liệu dev phục vụ phát triển; kết quả trên đó không phải bảo đảm tổng quát hoá.

~~~powershell
python -m nosleepclub_datamate.baseline_eval --train-dir PATH_TO_TRAIN --source-split train --output-dir PATH_TO_NEW_PRIVATE_EVAL
~~~

Fixtures trong tests do dự án tạo. Test ingestion/query không thay cho xác minh nghiệp vụ trên toàn bộ dữ liệu. Hiện chưa có GPU model, Docker thi, full-data agent, verifier độc lập hoặc calibrated confidence. Baseline có coverage thấp theo thiết kế và có thể vẫn trả lời sai.

## Đo bản đầu ngày 02/11/2026

Với seed `nosleepclub-baseline-v1`, nhóm DEV gồm 513 câu thuộc 5 business trong dữ liệu train. Bản query/data đã cố định đạt **92 đúng, 25 sai, 396 abstain** theo local proxy: PA **0,130604**, coverage **22,81%**, accuracy trên câu đã trả lời **78,63%**. Không có lỗi load hoặc solver. Thời gian DEV 89,375 giây trên máy phát triển; không dùng nó làm số đo GPU hay ước lượng chắc chắn cho private.

Không dùng các lỗi DEV cụ thể để sửa bản query sau lần đo này. Lượt đo phần TRAIN còn lại đã dừng để nhường RAM cho inference public; không có kết quả TRAIN đầy đủ cho bản cuối. Thay đổi runner sau validation chỉ giới hạn bộ nhớ theo business; có integration test kiểm tra giải phóng dữ liệu, bảo toàn thứ tự và không đọc nhãn. Tổng suite local: **80 tests pass** trên Python 3.11 với openpyxl 3.1.5.

Các con số trên là validation bằng nhãn train, **không phải điểm BTC**. Public inference chạy với query/data cố định và rulebook public làm input; không dùng test questions để tạo prompt lessons hoặc chỉnh thuật toán.

## Kết quả public baseline v1

Ngày 02/11/2026, entry `732b3761-a0b0-4183-b5be-207337b39e34.jsonl` được portal chấm **Public Score 0,01900**. Artifact từ commit `cff2357a9102000d7d97cc9c05a14954be130b1f`, chạy 248,009 giây trên máy phát triển, 1.000 records gồm 41 đáp án/959 abstain, không có lỗi thực thi trong log. SHA256 `99a42e7f3fcca6974b9c3b0ebe79eea14916cd8b199155b4d65bfe259f8bb03b`. Điểm chính thức chỉ áp dụng cho artifact này; [audit v0.2.1](AUDIT_2026-11-02.md) có các sửa lỗi sau khi artifact đã được tạo.
