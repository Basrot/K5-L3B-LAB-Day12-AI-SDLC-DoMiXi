# Mở rộng live: mưa, truy đuổi, sông và quán

Yêu cầu người dùng: nhân vật áo vàng theo ảnh, xuất hiện khi mưa và đuổi theo khi lặn; chạm mất 1 HP, có thể chạy thoát; sông rộng và nhiều loại cá/vật phẩm có ảnh; bàn có tên, khách ăn/uống đa dạng.

Thiết kế thực hiện: dữ liệu mở rộng nằm trong JSON riêng, chỉ LiveGame dùng bản tuning deepcopy. Headless và game.contract.json giữ nguyên. Mưa theo lịch tick, có cảnh báo và thời gian còn lại. Người đuổi chậm hơn nhân vật, có miễn nhiễm và đẩy lùi sau va chạm; ngừng đuổi khi lên mặt nước hoặc hết mưa. Chỉ 1 HP mỗi va chạm hợp lệ.

Quán live có bốn bàn đặt tên, hai bếp, khách đa dạng, vòng đời chờ/nấu/phục vụ/ăn-uống/thanh toán. Có nút chuyển cảnh; nguyên liệu thu hoạch chuyển sang quán trong bộ nhớ, vật phẩm sưu tập riêng. Khi mở quan độc lập dùng kho mẫu để chơi thử, ghi rõ trên UI. Kho xuất ra file vẫn chỉ có bốn loại contract.

Kế hoạch:
1. Test fail cho thời tiết/va chạm/miễn nhiễm, vùng sông mở rộng, cô lập headless và kho chuẩn; quán giữ nguyên liệu, phục vụ/thanh toán và khách thiếu món.
2. Thêm cấu hình live_world.json; nâng LiveGatherSim; thêm LiveQuanSim; nối vào LiveGame và API chuyển chế độ.
3. Tạo ba atlas bằng image_gen; phục vụ qua whitelist; render camera, mưa/truy đuổi, cá có tên, khách ăn/uống, bảng bàn và món.
4. Chạy test trên Windows, kiểm tra trình duyệt, review độc lập và ghi bằng chứng.
