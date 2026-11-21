# Lặn, nhặt đồ và animation

Người dùng đã yêu cầu làm lại ảnh lặn và xác nhận tích hợp luôn vào game.

Thiết kế: giữ điều khiển WASD, Space bắt cá, E tương tác. Bổ sung luật oxy/hái/bắt cá đang TODO theo tuning hiện tại. Đồ nhặt đáy sông là phần sáng tạo chỉ bật trong LiveGatherSim, đọc từ dữ liệu riêng, không sửa contract hoặc schema kho. Đồ trang trí có kho sưu tập riêng, không xuất vào kho nguyên liệu.

Kế hoạch thực hiện trực tiếp trong checkout hiện tại:
- Viết và chạy test cho oxy, bắt cá, nhặt đồ dưới nước, sức chứa, restart và tắt phần mở rộng ở Session/headless.
- Hoàn thiện GatherSim; thêm LiveGatherSim cùng dữ liệu JSON; nối ở LiveGame, phục vụ PNG an toàn qua danh sách cho phép.
- Tạo atlas 4x4: lặn, bơi chìm, nhặt, nổi; render theo tick, vận tốc và sự kiện. Cảnh sông lấy ảnh đã tạo, căn mặt nước với độ sâu sim.
- Chạy unittest và ghi bằng chứng, hướng dẫn thao tác. Atlas chỉ có 4 frame/mỗi trạng thái, chất lượng phụ thuộc độ nhất quán ảnh sinh.

Lý do sửa starter live.py và web/index.html: phục vụ asset và bật riêng phần sáng tạo trong live; headless vẫn dùng GatherSim.
