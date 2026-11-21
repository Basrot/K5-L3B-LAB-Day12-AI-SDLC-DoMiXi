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

## Phase 4 (cuối — tổng kết cập nhật)
- **Rà lại hành động Phase 2 — đã làm chưa? vì sao?**
  - Phần (2) **"ưu tiên lõi headless + 2 skill xanh trước"** đã làm triệt để ngay từ đầu Phase 3: viết ADR 0001, chốt toàn bộ lõi v1.2 & 10 test biên `test_v12_freshness.py` xanh trước khi quay lại sửa lỗi/nâng cấp bản live.
  - Phần (1) **`TEAM.md` + `team` trong `game.contract.json`** bị chậm sang cuối Phase 3 do phải đối chiếu đúng 4 GitHub handle thật (`Basrot`, `BFNGOC2`, `daongochan`, `DucTai2804`) trên lịch sử commit GitHub — nay đã hoàn tất và `tools/check_team.py` trả `OK`.
- **Điều tốt / điều tệ:**
  - *Tốt:* 4/4 thành viên đều đạt ≥ 3 commit có nội dung; ranh giới headless vs live cực kỳ rõ ràng (`_live_mode` shim + `deepcopy` config riêng), 104/104 tests pass, chạy 5 ngày headless (111.000 ticks) trong ~8s, tất định byte-từng-byte cả 3 mode; có 2 AI skill dùng thật và bộ audit phát hiện kịp crash `--inventory-out` ở bản live.
  - *Tệ:* Thiếu kỷ luật gắn tag ngay cuối Phase 1–2 và từng có commit đẩy nhầm 2 file log tạm (`live-server*.log`) lên `main` (đã dọn).
- **Số liệu thật (tính đến mốc bàn giao Phase 3 trên `main`):**
  - Commit nội dung (không tính merge) theo người: `daongochan` (Đào Ngọc Hân): **10+**, `Basrot` (Nam Nguyễn): **9**, `BFNGOC2` (BFNGOC): **6**, `DucTai2804` (Tran Trong Duc Tai): **3** (tổng ≥ 28 commit nhóm trên nền 9 commit starter).
  - Cách đọc code của nhau: rà diff trực tiếp khi tích hợp vào `main` và chạy trọn bộ `python tools/test_windows.py` + 2 skill `.agents/skills/` sau mỗi lần gộp.
  - Token ước tính ghi theo từng phase & thành viên tại [`docs/ai-usage-log.md`](ai-usage-log.md) (~350k token tổng hợp từ các lượt đã ghi log).
- **Một lần AI sai và cách nhóm phát hiện:**
  - Ở Phase 3, khi nâng cấp `write_inventory` sang schema v1.2, AI ban đầu giữ nguyên `LiveGatherSim.inventory_items()` trả dict đếm để không vỡ test live cũ nhưng bỏ sót nhánh `chonoi.live --mode gather --inventory-out` gọi lại `write_inventory`. Nhóm phát hiện nhờ viết kịch bản audit end-to-end giả lập đủ mọi cờ CLI (`TypeError: string indices must be integers`), sau đó sửa xuất v1.2 trực tiếp từ `fresh_items` và khóa bằng test hồi quy mới trong `tests/test_live.py`.
- **Nếu làm lại, đổi gì:**
  - Khóa `TEAM.md` + `tools/check_team.py` xanh ngay 10 phút đầu tiên, gắn tag đều đặn cuối mỗi phase, và thêm `.gitignore` cho các file log server tạm (`*.log`) ngay từ commit đầu.
