# Retro nhóm

## Phase 2 (nhanh)
- **Điều tốt:**
  - Cô lập rất sạch giữa **lõi headless** (`GatherSim`, `QuanSim`, `DaySim`, `game.contract.json`) và **mở rộng sáng tạo bản live** (`LiveGatherSim`, `LiveQuanSim`, `live_world.json`) — không lần nào mở rộng live làm vỡ tính tất định của headless.
  - Cả 4 thành viên đều đã có đóng góp thực tế vào cùng 1 repo chung `main` (`Basrot`, `daongochan`, `BFNGOC2`, `DucTai2804`); khi đồng đội đặt trùng số thứ tự asset `15–16` đã tự đổi sang `17–18` để tránh xung đột.
  - Bộ kiểm thử tự động mở rộng mạnh từ bộ smoke starter lên đầy đủ unit + black-box headless cho cả 3 mode `gather`, `quan`, `day` (chạy 1 ngày 22.200 tick dưới 1 giây, byte-identical).
- **Điều tệ:**
  - Nửa đầu Phase 1–2 bị đảo ưu tiên: dành nhiều thời gian cho đồ họa/tính năng live (P2) trong khi lõi headless `gather.py`, `--mode day`, `TEAM.md` và gắn tag `phase-1` bị chậm.
  - `TEAM.md` chưa được điền trong 15 phút kickoff nên `tools/check_team.py` vẫn fail tới cuối Phase 2; 2 thành viên mới có 2 commit nội dung (cần ≥ 3 commit/người).
- **1 hành động cho Phase 3 (có người nhận):**
  - **Người nhận:** Người 3 (PO/QA — Đào Ngọc Hân) cùng trưởng nhóm (Nam Nguyễn).
  - **Hành động:** Trước khi code bất kỳ tính năng Phase 3 nào, dành đúng **5 phút đầu Phase 3** để: (1) điền đủ 4 tên + GitHub handle thật vào `TEAM.md` và sửa `"team": "DoMiXi"` trong `game.contract.json` cho `tools/check_team.py` xanh, (2) áp quy tắc **"xong AC lõi headless + chạy 2 skill trong `.agents/skills/` xanh trước rồi mới mở thêm tính năng live"**.

## Phase 3 (nhanh — Change Request v1.2)
- **Điều tốt:**
  - Viết ADR + Impact Analysis (`docs/adr/0001-freshness-individual-inventory.md`) trước khi chạm code giúp phát hiện sớm ranh giới giữa `QuanSim` headless v1.2 và `LiveQuanSim` (dùng kho đếm + `freshness.py`), giữ toàn bộ test live xanh ngay lần chạy đầu tiên.
  - Dùng `fractions.Fraction` triệt tiêu hoàn toàn sai số dấu phẩy động ở ngưỡng ươn `30` và công thức `floor(giá × trung_bình_fresh / 100)`.
  - Gộp song song mượt mà nhiều nhánh tính năng live mới của đồng đội (`Ca Sĩ Jack`, `Reservations`, `equipment`, poster toàn cast) với lõi Contract v1.2, chỉ có 2 xung đột nhỏ và tất cả 104/104 test xanh.

## Phase 4 (cuối — tổng kết phát hành v1.0.0)
- **Rà lại hành động Phase 2 — đã làm chưa? vì sao?**
  - Phần (2) **"ưu tiên lõi headless + 2 skill xanh trước"** đã làm triệt để suốt Phase 3 và Phase 4: viết ADR 0001 trước khi chạm code v1.2, hoàn thiện `bench_cmd` + `soak_cmd` + test v1.3 xanh trước khi đóng gói phát hành.
  - Phần (1) **`TEAM.md` + `team` trong `game.contract.json`** bị chậm sang cuối Phase 3 do phải đối chiếu đúng 4 GitHub handle thật (`Basrot`, `BFNGOC2`, `daongochan`, `DucTai2804`) trên lịch sử commit GitHub — nay đã hoàn tất và `tools/check_team.py` trả `OK`.
- **Điều tốt / điều tệ:**
  - *Tốt:* 4/4 thành viên đều đạt ≥ 4 commit có nội dung và hoàn tất 4/4 phản tư cá nhân trong `docs/members/`; ranh giới headless vs live cực kỳ rõ ràng (`_live_mode` shim + `deepcopy` config riêng), **112/112 tests pass**, `soak` 10 ngày chạy trong ~11s (`crashes: 0`, lặp lại 100% giữa 2 lượt), `bench` 1280×720 đạt **`72.68 avg FPS`** và **`500.31 ms` load** sau khi tối ưu bỏ polygon stipple GDI trên Tk; đủ 3 cảnh báo chữ/biểu tượng + chế độ Tương phản cao (`H`), cùng nâng cấp giao diện HUD kính mờ & va chạm rào/bàn/bếp bản live.
  - *Tệ:* Thiếu kỷ luật gắn tag ngay cuối Phase 1–2; từng có commit đẩy nhầm 2 file log tạm (`live-server*.log`, đã dọn và thêm vào `.gitignore`); `p1_low_fps` của renderer `tkinter.Canvas` đạt `20.0 FPS` (dưới mốc báo cáo 30 FPS do GDI spike trên Windows).
- **Số liệu thật (tính đến mốc phát hành `v1.0.0` / `phase-4` trên `main`):**
  - Commit nội dung (không tính merge) theo người: `daongochan` (Đào Ngọc Hân): **15+**, `Basrot` (Nam Nguyễn): **12**, `BFNGOC2` (Thiều Thế Ngọc): **7**, `DucTai2804` (Trần Trọng Đức Tài): **4** (tổng ≥ 38 commit nhóm trên nền 9 commit starter).
  - Cách đọc code của nhau: rà diff trực tiếp khi tích hợp vào `main` và chạy trọn bộ `python tools/test_windows.py` + 2 skill `.agents/skills/` sau mỗi lần gộp.
  - Token ước tính ghi theo từng phase & thành viên tại [`docs/ai-usage-log.md`](ai-usage-log.md) (~405k token tổng hợp từ các lượt đã ghi log).
- **Một lần AI sai và cách nhóm phát hiện:**
  - *Phase 3:* Khi nâng cấp `write_inventory` sang schema v1.2, AI giữ nguyên `LiveGatherSim.inventory_items()` trả dict đếm để tránh vỡ test live cũ nhưng bỏ sót nhánh `chonoi.live --mode gather --inventory-out`. Nhóm phát hiện nhờ viết kịch bản audit end-to-end giả lập đủ mọi cờ CLI (`TypeError: string indices must be integers`), sau đó sửa xuất v1.2 trực tiếp từ `fresh_items` và khóa bằng test hồi quy trong `tests/test_live.py`.
  - *Phase 4:* Ở lần viết đầu của `chonoi/bench.py`, AI vẽ 5 tia nắng bằng `create_polygon(..., stipple="gray12")` khiến Windows Tk GDI tụt xuống `50.75 avg FPS` / `16.26 p1_low_fps`. Nhóm phát hiện ngay từ lần đo 30 giây thật, thay sang nét mảnh `create_line` và bỏ cập nhật thừa các nút tĩnh giúp tăng lên **`72.68 avg FPS`** và **`500.31 ms` load**.
- **Hành động tiếp theo (nếu làm tiếp sau v1.0.0):**
  - Chuyển renderer của `bench_cmd` sang backend tăng tốc phần cứng (hoặc WebGL/Canvas đo qua CDP) để đẩy `p1_low_fps` vượt mốc 30 FPS ổn định trên mọi hệ điều hành; khóa `TEAM.md` + `.gitignore` ngay 10 phút đầu và gắn tag đều cuối mỗi phase.
