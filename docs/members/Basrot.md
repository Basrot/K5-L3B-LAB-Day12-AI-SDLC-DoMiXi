# Basrot (Nguyễn Gia Nam) — phản tư cá nhân

- **Tôi đã làm:** Xây luồng chiến dịch gồm sảnh, intro, chọn màn, thưởng xu và nhạc sảnh (`5f2f1a8`); bổ sung trở về sảnh và xem lại intro (`54dc031`); sửa chuyển từ ban ngày sang buổi tối (`b25c4f9`); xử lý khởi động máy chủ trên Windows (`cce0738`); thiết kế poster toàn bộ nhân vật (`7bd5c45`). Tôi cũng lập bảng phân công nhóm (`67a1987`).
- **Tôi đã review/tích hợp:** Đồng bộ các thay đổi trên `main` qua những commit merge của mình; kiểm tra luồng chơi chiến dịch từ sảnh qua các màn.
- **AI sai ở đâu và tôi phát hiện thế nào:** Bản đầu của luồng chiến dịch chưa đáp ứng đủ việc quay lại sảnh và phát lại intro. Tôi phát hiện khi đi lại luồng trong game, rồi bổ sung chức năng này ở `54dc031`.
- **Điều tôi học được:** Cần thử luồng chơi từ đầu đến cuối, nhất là các điểm chuyển giữa intro, sảnh, buổi sáng và buổi tối; test từng chức năng riêng chưa đủ để phát hiện lỗi trải nghiệm.
