# Credits
Liệt kê asset ngoài (nguồn, giấy phép CC0/CC-BY/MIT) và công cụ AI đã dùng.

## Bộ hình & âm thanh 2026-11-21
- `assets/art-pack/01..09.png`: 9 ảnh/bảng hình được tạo bằng công cụ built-in `image_gen` theo yêu cầu nhóm. Khuôn mặt tham chiếu từ ảnh do thành viên cung cấp; không gán giấy phép CC0 cho ảnh tham chiếu. Prompt và ghi chú tích hợp nằm trong `assets/art-pack/README.md`.
- `assets/art-pack/10-underwater-animation.png`: atlas lặn/bơi chìm/nhặt/nổi (4×4), tạo bằng built-in `image_gen`.
- `assets/art-pack/11-rain-pursuer.png`, `12-river-life.png`, `13-dining-cast.png`, `14-dishes.png`: các sprite sheet mở rộng cho bản live (Chú Áo Vàng, sinh vật sông, khách ăn/uống, món ăn), tạo bằng `image_gen`.
- `assets/art-pack/15-quan-cho-noi.jpg`: ảnh nền nhà bè quán ăn chợ nổi do thành viên nhóm cung cấp, tích hợp làm khung cảnh live mode `quan` (tắt ở headless).
- `assets/art-pack/16-seated-waiting.png`: sprite sheet 4×2 khách ngồi ghế gọi món và ngồi chờ bếp (Bà Sáu, Chú Ba, Anh Tư, Chị Mai), tạo bằng công cụ sinh ảnh AI đồng bộ từ `13-dining-cast.png`, tách nền trong suốt cho bản live `quan`.
- `assets/art-pack/17-kha-banh.png`, `18-cong-an.png`: sprite sheet sự kiện sáng tạo bản live (Khá Bảnh & Chú Công An), tạo bằng công cụ sinh ảnh AI (ghi chú thêm ở `assets/art-pack/README.md`).
- `assets/art-pack/chieu-troi-mua.mp3`: âm thanh hiệu ứng mưa cho bản live, tích hợp trong `chonoi/live.py` và `chonoi/web/index.html`.

## Công cụ AI đã dùng
- Antigravity / Gemini, Claude / Codex (chi tiết theo người và theo phase ghi trong `docs/ai-usage-log.md`).
