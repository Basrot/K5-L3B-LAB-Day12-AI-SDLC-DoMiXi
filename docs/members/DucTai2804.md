# DucTai2804 (Trần Trọng Đức Tài) — phản tư cá nhân

- **Tôi đã làm (kèm link commit):**
  - Quản lý và hoàn thiện Lát 4 Quán (`sim/quan`): logic bếp, bưng bê, phục vụ, đóng ca, cộng tip theo tỉ lệ kiên nhẫn (`8c601ea`).
  - Tích hợp và kiểm thử Contract v1.2 trong quán: tiêu thụ kho cá thể theo ID, tính tươi chính xác `Fraction` và chốt giá theo tươi.
  - Sáng tạo tính năng Live: Nhân vật Khá Bảnh vào thu bảo kê 50k, Chú Công An tuần tra can thiệp giải cứu (`c1c1b21`), Ca sĩ Jack J97 hát *Thiên Lý Ơi* biểu diễn sân khấu giúp tăng tip và tặng fan donation (`1148250`).
- **Tôi đã review:**
  - Rà soát kiểm thử liên thông kho 2 tiến trình, luồng campaign, và đồng bộ giải quyết xung đột merge với `origin/main` (`9020554`, `ca81209`, `6774666`).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - AI ban đầu tính hao độ tươi bằng số thực float dẫn đến sai số làm tròn khi so sánh ngưỡng ươn 30; tôi phát hiện qua test ranh giới và chuẩn hóa sang `Fraction`.
  - AI để nhân vật Khá Bảnh đi lang thang vô hạn trong quán; tôi yêu cầu điều chỉnh kịch bản có thời điểm vào/ra và phối hợp phản xạ cùng Công An.
- **Điều tôi học được:**
  - Kỹ năng chia module độc lập trong kiến trúc SDLC: cô lập triệt để phần sáng tạo live khỏi luật headless để luôn bảo đảm tính tất định 100%.
