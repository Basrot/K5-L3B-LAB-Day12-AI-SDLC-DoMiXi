# DucTai2804 (Trần Trọng Đức Tài) — phản tư cá nhân

- **Tôi đã làm (kèm commit):**
  - Hoàn thiện & rà Lát 4 Quán (`sim/quan`): logic bếp, bưng bê, phục vụ, đóng ca, tip theo kiên nhẫn (`8c601ea`).
  - Kiểm thử Contract v1.2 trong quán (kho cá thể, `Fraction`, chốt giá theo tươi) và cập nhật phản tư/tài liệu cuối phase (`ec6dd2a`).
  - Sáng tạo bản Live: Khá Bảnh thu bảo kê 50k, Chú Công An tuần tra bắt giữ (`c1c1b21`), Ca sĩ Jack hát *Thiên Lý Ơi* tăng tip và fan donation (`1148250`).
- **Tôi đã review:** Kiểm thử liên thông kho 2 tiến trình, luồng campaign và xử lý gộp nhánh trên `main` (`9020554`, `ca81209`, `6774666`).
- **AI sai ở đâu & cách phát hiện:**
  - AI ban đầu tính hao tươi bằng `float` gây sai số ngưỡng 30; phát hiện qua test biên và đổi sang `Fraction`.
  - AI để Khá Bảnh đi lang thang vô hạn; tôi chỉnh lại chu kỳ vào/ra và phối hợp cùng Công An.
- **Bài học:** Tách module rõ ràng và cô lập sáng tạo live khỏi lõi headless giúp bảo đảm tính tất định 100%.
