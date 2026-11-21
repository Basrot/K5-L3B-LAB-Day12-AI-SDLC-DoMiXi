# Retro nhóm

## Phase 2 (nhanh)
- **Điều tốt:**
  - Cô lập rất sạch giữa **lõi headless** (`GatherSim`, `QuanSim`, `DaySim`, `game.contract.json`) và **mở rộng sáng tạo bản live** (`LiveGatherSim`, `LiveQuanSim`, `live_world.json`) — không lần nào mở rộng live làm vỡ tính tất định của headless.
  - Cả 4 thành viên đều đã có đóng góp thực tế vào cùng 1 repo chung `main` (`Nam Nguyễn`, `Đào Ngọc Hân`, `BFNGOC`, `Tran Trong Duc Tai`); khi đồng đội đặt trùng số thứ tự asset `15–16` đã tự đổi sang `17–18` để tránh xung đột.
  - Bộ kiểm thử tự động mở rộng mạnh từ bộ smoke starter lên đầy đủ unit + black-box headless cho cả 3 mode `gather`, `quan`, `day` (chạy 1 ngày 22.200 tick dưới 1 giây, byte-identical).
- **Điều tệ:**
  - Nửa đầu Phase 1–2 bị đảo ưu tiên: dành nhiều thời gian cho đồ họa/tính năng live (P2) trong khi lõi headless `gather.py`, `--mode day`, `TEAM.md` và gắn tag `phase-1` bị chậm.
  - `TEAM.md` chưa được điền trong 15 phút kickoff nên `tools/check_team.py` vẫn fail tới cuối Phase 2; 2 thành viên mới có 2 commit nội dung (cần ≥ 3 commit/người).
- **1 hành động cho Phase 3 (có người nhận):**
  - **Người nhận:** Người 3 (PO/QA — Đào Ngọc Hân) cùng trưởng nhóm (Nam Nguyễn).
  - **Hành động:** Trước khi code bất kỳ tính năng Phase 3 nào, dành đúng **5 phút đầu Phase 3** để: (1) điền đủ 4 tên + GitHub handle thật vào `TEAM.md` và sửa `"team": "DoMiXi"` trong `game.contract.json` cho `tools/check_team.py` xanh, (2) áp quy tắc **"xong AC lõi headless + chạy 2 skill trong `.agents/skills/` xanh trước rồi mới mở thêm tính năng live"**.

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
