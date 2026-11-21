# Standup giữa phase (mỗi người một dòng, 2–3 phút)

| Phase | Người | Đã xong | Sắp làm | Vướng gì |
|---|---|---|---|---|
| Phase 1 | Nam Nguyễn (`Basrot`) | Lập bảng phân công 4 người (`67a1987`), dựng sông mở rộng, thời tiết mưa & bản live quán (`894f611`, `1d5d548`) | Hoàn thiện luồng campaign và tích hợp live | Chưa có |
| Phase 1 | BFNGOC (`BFNGOC2`) | Hoàn thiện hiệu ứng ban ngày, âm thanh, độ tươi nguyên liệu live (`4599006`, `07987e8`, `45adb43`) | Nối HUD độ tươi và kiểm thử live | Tránh đụng `game.contract.json` |
| Phase 1 | Đào Ngọc Hân (`daongochan`) | Xong Lát 3 Quán (`quan_orders.py`, kiểm mâu thuẫn `scenario.py`, 12 test `test_quan_orders.py`, bằng chứng P1 `dd512bf`) | Ghép Lát 4 và chuẩn bị nâng cấp Contract v1.1 | Cần thống nhất `base_price`/`tip` lúc `waiting` (đã ghi `docs/clarify.md`) |
| Phase 1 | Tran Trong Duc Tai (`DucTai2804`) | Rà soát & cập nhật ma trận kiểm chứng + nhật ký AI cho Lát 4 (`8c601ea`) | Bổ sung tính năng sáng tạo bản live cho quán | Đảm bảo không làm sai headless |
| Phase 2 | Nam Nguyễn (`Basrot`) | Dựng luồng `--mode campaign`, kinh tế nhiều màn, nhạc sảnh, nút về quán sớm và sửa console `cp1252` (`5f2f1a8`, `54dc031`, `cce0738`, `b25c4f9`) | Hoàn thiện poster toàn dàn nhân vật | Tránh lệch `fish_initial=8` với `live_world.py` |
| Phase 2 | BFNGOC (`BFNGOC2`) | Bổ sung màn hình trang bị `equipment`, đặt bàn trước live (`reservations.py`), `test_campaign_flow.py` (`12cfb70`, `d1ee89e`) | Kiểm hồi quy luồng lobby/intro | Đã thêm test `test_lobby_resume_and_replay_intro_preserve_session` |
| Phase 2 | Đào Ngọc Hân (`daongochan`) | Nâng Contract v1.1, hoàn thiện lõi `QuanSim`, `GatherSim` (cá bơi/sinh, Cá Sấu M1/M2), `--mode day`/Shop/`pause`, 2 AI skill và bằng chứng P2 (`611cb86`, `c75481f`) | Chuẩn bị nhận TICKET-03 v1.2 | `TEAM.md` chưa điền đủ handle thật |
| Phase 2 | Tran Trong Duc Tai (`DucTai2804`) | Hoàn thiện sự kiện live Khá Bảnh, Chú Công An & Ca Sĩ Jack (J97) + test `test_live_world.py` (`c1c1b21`, `1148250`) | Rà thử trải nghiệm live quán | Tên file mp3 tiếng Việt có dấu đã tạo alias `thien-ly-oi.mp3` |
| Phase 3 | Đào Ngọc Hân (`daongochan`) | ADR 0001, nâng cấp trọn lõi Contract v1.2 (`freshness_v12.py`, kho cá thể, `spoiled`, giữ chỗ theo id, giá theo tươi), `CHANGELOG.md`, 10 test v1.2 (`d817dbc`, `ddcb31d`), sửa lỗi `--inventory-out` live & nâng cấp UI quán/sông | Hoàn thiện `TEAM.md`, bằng chứng tổng, đồng bộ `7bd5c45` và gắn tag `phase-3` | Không còn vướng kỹ thuật (104/104 test xanh) |
| Phase 3 | Nam Nguyễn (`Basrot`) | Tạo poster đầy đủ dàn nhân vật `34-game-poster-full-cast.png` (`7bd5c45`) và kiểm 103 test xanh | Hỗ trợ kiểm tra cuối trước Phase 4 & Release | Không có |
