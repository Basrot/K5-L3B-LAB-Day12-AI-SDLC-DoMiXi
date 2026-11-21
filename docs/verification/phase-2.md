# Ma trận truy vết Phase 2 (TICKET-02 — Test Contract v1.1)

> Kết quả đo thật trên nhánh `main` sau khi hoàn thiện toàn bộ lõi Contract v1.1 (`gather`, `quan`, `day`, `Shop`, `pause`) và gói Harness AI / QA.
> Nhóm 4 người không bắt buộc mục 3 (Mở rộng); toàn bộ phần mở rộng sáng tạo live cô lập hoàn toàn khỏi headless.

| AC / Hạng mục (TICKET-02) | Cách kiểm chứng | Bằng chứng (`docs/proof/phase-2/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| **AC-P2-01:** `contract_version: "1.1"`, số chuẩn, đủ 6 nguyên liệu (`+ ca_keo, keo_neo`), 6 nút `N1..N6`, 6 món, `day_plan` D1–D5, `shop` | `python tools/test_windows.py` (`test_quan_v11.QuanV11ManifestAndMenu`, `contract.py`) | [test-v11-full.txt](../proof/phase-2/test-v11-full.txt) | **Đạt** |
| **AC-P2-02:** Gather sửa đủ payload §E (`gather.amount`, `fish_caught.yield`, `hold_full`, `oxygen_empty`, `faint` LIFO), cá bơi `1.5 m/s` phản xạ mép, đổi hướng 120 tick, sinh 360 tick | `python tools/test_windows.py` (`test_v11_core.GatherV11PayloadsFishAndMonsters`) | [test-v11-full.txt](../proof/phase-2/test-v11-full.txt) | **Đạt** |
| **AC-P2-03:** Cá Sấu Năm Chèo `M1` (D1) & `M2` (D3): `patrol`/`chase`/`recoil`, `monster_hit` (-1 HP, rớt `floor(giỏ/2)` LIFO, bất tử 90 tick), `faint(cause="monster")` | `python tools/test_windows.py` (`test_crocodile_patrol_chase_hit_lifo_loss_recoil_and_monster_faint`) | [test-v11-full.txt](../proof/phase-2/test-v11-full.txt) | **Đạt** |
| **AC-P2-04:** Quán v1.1: 2 bếp `B1`–`B2`, 4 bàn `T1`–`T4`, 6 món, lọc `day_plan` trong `day`, trọn vòng bếp→phục vụ→boa `floor`→`paid`→`closing` & kiểm fixture mã `2` | `python tools/test_windows.py` (`test_quan_orders.py`, `test_quan_v11.py`) | [test-v11-full.txt](../proof/phase-2/test-v11-full.txt) | **Đạt** |
| **AC-P2-05:** Smoke tích hợp liên thông kho 2 tiến trình (`gather --inventory-out` → `quan --inventory`) với nguyên liệu mới `ca_keo`, `keo_neo` & món `lau_mam` | Skill `smoke-inventory-handoff` + `test_v11_two_process_inventory_with_new_kinds_and_lau_mam` | [integration.txt](../proof/phase-2/integration.txt), [test-v11-full.txt](../proof/phase-2/test-v11-full.txt) | **Đạt** (`catch.json` khớp chính xác, quán gọi `lau_mam`) |
| **AC-P2-06:** `--mode day` (`--days 1..5`), `day_start`/`day_plan`/`phase_start`, `Shop` nâng cấp `oxygen`/`hp` (áp từ Ngày kế qua `active_upgrades`), `buy_failed`, `pause`/`resumed` | `python tools/test_windows.py` (`test_v11_core.DayModeShopAndPauseV11`) | [test-v11-full.txt](../proof/phase-2/test-v11-full.txt), [determinism-and-day.txt](../proof/phase-2/determinism-and-day.txt) | **Đạt** |
| **AC-P2-07:** Tính tất định byte-từng-byte trên cả 3 mode (`gather`, `quan`, `day`) & hiệu năng 1 ngày không pause (22.200 tick ≤ 20 s) | Skill `check-determinism-and-contract` | [determinism-and-day.txt](../proof/phase-2/determinism-and-day.txt) | **Đạt** (`BYTE_IDENTICAL=True` cả 3 mode; 1 ngày chạy `1.057 s` ≪ 20 s) |
| **AC-P2-08:** Regression test Phase 1 còn hiệu lực & cô lập phần sáng tạo live khỏi headless/contract | `python tools/test_windows.py` (**80/80 tests OK**) | [test-v11-full.txt](../proof/phase-2/test-v11-full.txt) | **Đạt** |
| **AC-P2-09:** Harness AI & hồ sơ Phase 2 (`AGENTS.md`, ≥ 2 skill `.agents/skills/`, `docs/plan/phase-2.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `README.md`, `CREDITS.md`) | Kiểm tra file & chạy trực tiếp 2 skill | `.agents/skills/*`, [determinism-and-day.txt](../proof/phase-2/determinism-and-day.txt) | **Đạt** |
| **AC-P2-10:** Menu/Pause/DayIntro/Summary trực quan trên UI bản chơi thử trình duyệt (`chonoi/web/index.html`) | Kiểm tra thực tế bản live | Bản live hiện chơi được `gather`/`quan` có HUD, nút chuyển cảnh, âm thanh, ảnh nền & hoạt ảnh; chưa làm màn hình Menu chính / DayIntro / Shop UI trên trình duyệt | **Chưa đạt** (đã chạy đủ ở headless `--mode day`, phần màn hình chuyển cảnh UI live cần làm tiếp) |
| **AC-P2-11:** `TEAM.md` đủ 4 thành viên thật + `team` trong `game.contract.json` + mỗi thành viên ≥ 3 commit + đẩy tag `phase-2` | `python tools/check_team.py` | Chờ xác nhận đủ 4 GitHub handle thật (`check_team.py` đang báo thiếu tên/handle) | **Chưa đạt** (cần chốt ngay trước khi gắn tag) |

## Danh sách test cũ đã cập nhật vì đổi luật Contract v1.0 → v1.1 (ghi rõ lý do)
1. `tests/test_smoke_p1.py` (`test_gather_snapshot_has_gather_fields`): đọc số đàn ban đầu động theo `tuning.gather.fish_initial` (`8` ở v1.1 thay vì hard-code `6` của v1.0).
2. `tests/test_smoke_p1.py` (`test_con_03_old_and_future_modes_rejected`): `--mode day` đã hợp lệ ở Contract v1.1 (mã `0`), chỉ còn `--mode river` bị từ chối (mã `2`).
3. `tests/test_diving.py` (`test_catch_underwater_and_cooldown`): khai fixture cá cố định tại `[15, 5]` vì v1.1 sinh 8 đàn ngẫu nhiên theo seed trên 30 điểm hình học thay vì cố định `F1` tại `[15, 5]`.
4. `tests/test_quan_orders.py` (`test_n3_01_full_tables_skip_without_no_dish`): lấp đủ toàn bộ bàn trong `tuning.quan.tables` (4 bàn ở v1.1 thay vì 1 bàn ở v1.0).
5. `tests/test_live_world.py` (`test_mode_switch_transfers_gather_stock`): bản live dùng đúng 3 bàn gỗ khớp nền ảnh `15-quan-cho-noi.jpg` (headless vẫn giữ đủ 4 bàn `T1`–`T4` theo Contract v1.1).

## Đánh giá ngắn
- **Đã đạt:** Toàn bộ **lõi headless Test Contract v1.1** (`gather`, `quan`, `day`, `Shop`, `pause`, 6 nguyên liệu, 6 món, 2 bếp/4 bàn, cá bơi/sinh, Cá Sấu `M1`/`M2`) đạt **80/80 tests xanh**, tất định từng byte, hiệu năng `1.057 s / ngày`, kèm 2 skill kiểm chứng thực thi được và đầy đủ bằng chứng thật trong `docs/proof/phase-2/`.
- **Chưa đạt / việc cần chốt ngay với nhóm:**
  1. Điền đủ 4 tên + GitHub handle thật vào `TEAM.md` và sửa `"team"` trong `game.contract.json` để `python tools/check_team.py` xanh.
  2. `BFNGOC` và `Trần Trọng Đức Tài` thêm ≥ 1 commit có nội dung (đủ ≥ 3 commit/người).
  3. Bổ sung màn hình Menu / DayIntro / Shop / Pause trên giao diện trình duyệt (`chonoi/web/index.html`) nếu kịp trước khi bàn giao.
