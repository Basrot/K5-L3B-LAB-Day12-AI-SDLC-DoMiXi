# Bằng chứng lặn và animation — 2026-11-21

- Test trước triển khai: 6 test mới, 3 fail và 2 error do oxy/bắt cá/ngất chưa có và chưa có collectible; test headless isolation đã qua.
- Sau triển khai: `python tools/test_windows.py` — 38 tests, OK. Bao gồm test hiện có không sửa, và 6 test oxy/refill, faint mất giỏ, bắt cá/cooldown, nhặt một lần/restart, sức chứa/khoảng cách, tắt extras ở headless.
- `node --check` trên script trích từ `chonoi/web/index.html` — exit 0.
- Browser thực: R, giữ D ~1,8 s, giữ S ~1,4 s: nhân vật ở x≈9,2, d≈5,7, hình bơi chìm và oxy giảm. Nhấn E: bộ sưu tập 0/8 → 1/8; hiện “Đang cất đồ” và event treasure_picked cho vỏ sò.
- Máy Windows có alias python3 lỗi WinError 1920; runner Windows chỉ thay launcher bằng sys.executable trong bộ nhớ. Test HTTP cần quyền localhost ngoài sandbox (trong sandbox bị WinError 10013).
- Không xác nhận toàn bộ PRD ẩn: repo chưa có nội dung PRD-0. Các luật cơ bản lấy từ TODO starter và tuning; payload event chi tiết cần đối chiếu Lab Board nếu có thêm quy định.
- Giới hạn mỹ thuật: 4 frame/trạng thái nên chuyển động có phong cách hoạt hình ngắn; một số frame có độ lệch nét/vị trí nhỏ. Cá và vật nhặt hiện dùng hình Canvas/emoji; không phải mọi asset trong art-pack đã được nối vào game.
