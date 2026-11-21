# BFNGOC2 (BFNGOC) — phản tư cá nhân

- **Tôi đã làm (kèm link commit):**
  - Đảm nhiệm module `client/ui`: cập nhật các hiệu ứng ban ngày, hiệu ứng nước và ánh sáng (`4599006`).
  - Tích hợp âm thanh hiệu ứng cho các hành động trong game (`07987e8`).
  - Hỗ trợ hiển thị UI độ tươi nguyên liệu cho bản live (`45adb43`).
  - Sửa lỗi làm mới sảnh (lobby refresh) và reset intro khi bắt đầu hành trình mới (`d1ee89e`).
- **Tôi đã review:**
  - Kiểm tra đồng bộ giao diện nhà bè, bảng HUD, âm thanh nền với `main` (`de88988`, `43e6648`, `2ceb34b`).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - AI khởi tạo trạng thái âm thanh và hiệu ứng particle đôi khi không dọn dẹp sạch khi chuyển giữa các màn sảnh/ngày/đêm, làm chồng chéo âm thanh; tôi phát hiện qua chạy thử UI và bổ sung cơ chế reset.
- **Điều tôi học được:**
  - Tầm quan trọng của việc quản lý vòng đời tài nguyên âm thanh/hình ảnh trên giao diện web và quy trình phối hợp gộp nhánh liên tục.
