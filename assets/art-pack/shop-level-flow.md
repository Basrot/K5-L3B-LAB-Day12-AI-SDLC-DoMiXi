# Luồng màn chơi và cửa hàng (định hướng hình ảnh)

## Vòng chơi

1. Chọn màn. Mỗi màn có một ca lặn và một ca phục vụ quán.
2. Lặn để lấy nguyên liệu, cá và vật phẩm. Màn cao hơn mở vùng sông sâu hơn và nhiều loại đồ hơn.
3. Lên bờ, chế biến và phục vụ khách. Màn cao hơn có nhiều khách hơn và yêu cầu đa dạng hơn.
4. Kết màn: hiện **xu kiếm được trong màn**, **độ uy tín**, **số sao** và các vật phẩm đã lấy. Sao được tính từ kết quả phục vụ và doanh thu theo ngưỡng trong dữ liệu màn; chưa chốt ngưỡng số.
5. Dùng xu trong cửa hàng để nâng cấp đồ lặn, rồi vào màn tiếp theo. Điều kiện mở màn và giá đều đọc từ dữ liệu, chờ nhóm thống nhất.

## Trạng thái cửa hàng

- Màn cửa hàng chính: chọn Bình khí, Mũ lặn, Chân vịt hoặc Đèn lặn.
- Mỗi món có màn riêng với cấp 1, 2, 3. Chỉ cấp kế tiếp được mua.
- Ban đầu: cấp 1 **Đã có**; cấp 2 **Nâng cấp** khi đủ xu; cấp 3 **Khóa**.
- Mua cấp 2: trừ giá cấp 2, cập nhật chỉ số, cấp 2 thành **Đã có**, cấp 3 sáng lên và có nút **Nâng cấp** nếu đủ xu.
- Mua cấp 3: trừ giá cấp 3, cập nhật chỉ số, cấp 3 thành **Đã có**.
- Khi thiếu xu, nút của cấp kế tiếp ở trạng thái không bấm được và hiện số xu còn thiếu.
- Giá, xu, chỉ số, cấp hiện tại và trạng thái khóa là chữ/UI động. **Không lấy số in trên ảnh concept 18–21 làm dữ liệu game.**

## Ảnh sử dụng

- `16-upgrade-shop.png`: màn chọn món, ô xu và cấp để trống cho UI động.
- `22-upgrade-detail-template.png`: khung màn nâng cấp dùng chung cho cả bốn món; tên món, biểu tượng vật phẩm, chỉ số, giá và nút do game hiển thị.
- `23-upgrade-level3-unlocked.png`: ví dụ trực quan sau khi mua Bình khí cấp 2; cấp 3 sáng lên.
- `18-upgrade-tank.png` đến `21-upgrade-lamp.png`: ảnh concept cũ để tham khảo thiết kế vật phẩm; giá và trạng thái trên ảnh chỉ là minh họa.
- `24-title-screen.png`: màn chào; hai nút trống để game vẽ tên và xử lý bấm.
- `25-level-select.png`: bản đồ chọn màn; năm ô địa điểm là bố cục minh họa, số màn thực tế lấy từ dữ liệu. Tên màn, số sao và trạng thái mở khóa do game vẽ.
- `26-day-to-night.png`: cảnh chiều tối để đặt dưới hiệu ứng tối dần khi chuyển từ ca lặn sang ca quán.
- `27-level-results.png`: nền tổng kết; ba sao và các ô vật phẩm, khách, xu, uy tín để game điền kết quả.

Đây là đặc tả hình ảnh và luồng chơi cho nhóm triển khai, chưa phải giao diện tương tác.
