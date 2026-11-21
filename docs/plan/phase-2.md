# Kế hoạch Phase 2 — Một ngày ở chợ nổi (TICKET-02, Contract v1.1)

## 1. Mục tiêu
- Nâng cấp toàn bộ lõi headless từ **Test Contract v1.0** lên **Test Contract v1.1** với bộ số chuẩn (nhóm 4 người ưu tiên 100% Lõi, không bắt buộc mở rộng mục 3).
- Hoàn thiện đủ 4 lát lõi: (1) số chuẩn + 6 nguyên liệu + cá bơi/sinh, (2) Cá Sấu Năm Chèo `M1`/`M2` + rớt giỏ LIFO + ngất `monster`, (3) Quán 2 bếp `B1`–`B2` / 4 bàn `T1`–`T4` / 6 món / `day_plan` D1–D5, (4) `--mode day` (`--days 1..5`) + `Shop` nâng cấp `oxygen`/`hp` + `pause`/`resumed`.
- Hoàn thiện gói QA & Harness AI: 2 skill thực thi được trong `.agents/skills/`, bằng chứng thật `docs/proof/phase-2/`, ma trận truy vết `docs/verification/phase-2.md`, retro nhanh Phase 2 và chốt `TEAM.md` trước khi gắn tag `phase-2`.

## 2. Phân chia công việc & phụ thuộc

| Lát / Mã | Phạm vi & AC-P2 | Phụ trách | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| AC-P2-01 (Contract v1.1) | `game.contract.json` v1.1, 6 nguyên liệu (`+ ca_keo, keo_neo`), `contract.py`, `inventory.py`, `scenario.py` | Người 3 (Đào Ngọc Hân) + Integrator | Chốt số chuẩn TICKET-02 | Đã hoàn thành |
| AC-P2-02 (Gather cá & §E) | Sửa payload §E (`amount`/`yield`/`hold_full`/`oxygen_empty`/`faint` LIFO), cá bơi `1.5 m/s` phản xạ mép, đổi hướng 120 tick, sinh 360 tick | Người 3 hỗ trợ hoàn thiện lõi `gather.py` (cùng Người 1–2) | AC-P2-01 | Đã hoàn thành |
| AC-P2-03 (Cá Sấu Năm Chèo) | `M1` (D1), `M2` (D3), `patrol`/`chase`/`recoil`, `monster_hit` + rớt `floor(giỏ/2)` LIFO + bất tử 90 tick + `faint(monster)` | Người 3 hỗ trợ hoàn thiện lõi `gather.py` | AC-P2-02 | Đã hoàn thành |
| AC-P2-04 (Quán v1.1) | 2 bếp `B1`–`B2`, 4 bàn `T1`–`T4`, 6 món, lọc `day_plan`, trọn vòng bếp→phục vụ→boa `floor`→`paid`→`closing` | Người 3 (Đào Ngọc Hân) & Người 4 (`Trần Trọng Đức Tài`) | AC-P2-01 | Đã hoàn thành |
| AC-P2-05 (`--mode day`, Shop, pause) | `chonoi/sim/day.py`, `inputs.py` (`pause`, `shop_done`, `buy`), `runner.py`, `headless.py` (`--days 1..5`), `upgrades`/`active_upgrades` | Người 3 hoàn thiện lõi headless; cả nhóm kiểm chứng | AC-P2-02..04 | Đã hoàn thành |
| AC-P2-06 (Live sáng tạo) | Nền nhà bè + khách ngồi + khách đi vào/ra, thời tiết ban ngày, âm thanh, Khá Bảnh & Chú Công An (chỉ live, tắt ở headless) | Cả 4 thành viên (`Nam`, `BFNGOC`, `Hân`, `Tài`) | Cô lập khỏi headless | Đã hoàn thành |
| AC-P2-07 (QA & Harness AI) | 2 skill `.agents/skills/`, bằng chứng `docs/proof/phase-2/`, `docs/verification/phase-2.md`, `docs/retro.md`, `TEAM.md` | Người 3 (QA/PO) tổng hợp; cả 4 người xác nhận `TEAM.md` | AC-P2-05 | Đang hoàn thiện (`TEAM.md` chờ 4 handle thật) |

## 3. Rủi ro & biện pháp
- **Rủi ro #1 — Lệch ưu tiên P2 (sáng tạo live) trước P0 (lõi headless):** Khắc phục bằng việc ưu tiên hoàn thiện toàn bộ lõi Contract v1.1 (`gather.py`, `quan.py`, `day.py`, `runner.py`, `headless.py`) và chạy regression test xanh trên `main`.
- **Rủi ro #2 — `TEAM.md` trống và chưa gắn tag `phase-1`/`phase-2`:** Cần cả nhóm xác nhận ngay 4 GitHub handle thật để `python tools/check_team.py` xanh trước khi gắn tag.
- **Rủi ro #3 — Số commit cá nhân chưa đồng đều:** `BFNGOC` (2) và `Trần Trọng Đức Tài` (2) cần thêm ít nhất 1 commit có nội dung mỗi người (vd điền phản tư cá nhân `docs/members/<handle>.md`, cập nhật `TEAM.md` hoặc UI HUD).
