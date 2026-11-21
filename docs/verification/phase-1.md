# Ma trận truy vết Phase 1

> Ghi nhận trạng thái thật trên nhánh `feature/quan-orders` (dựa trên `main@894f611` + Lát 3 `749f020`, `0a1b848`).
> Cần chạy lại và cập nhật sau khi ghép đủ Lát 1–4 lên `main` trước khi gắn tag `phase-1`.

| AC / Hạng mục (PRD-0) | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| Test Contract B–C: CLI headless, `ticks=0`, tất định cùng seed, lỗi đầu vào mã thoát `2` trước khi ghi file | `python tools/test_windows.py` (`test_smoke_p1.Contract`, `test_python_starter_units`) | [test-lat3.txt](../proof/phase-1/test-lat3.txt) | **Đạt** |
| Gather di chuyển, ramp đảo hướng, chặn biên, cập bến (`docked`), hết giờ (`time`) | `python tools/test_windows.py` (`test_smoke_p1.Movement`, `test_diving.py`) | [test-lat3.txt](../proof/phase-1/test-lat3.txt) | **Đạt** |
| Gather sinh tồn & thu hoạch đủ payload PRD-0 §E (`oxygen_empty`, `faint.lost` LIFO, `gather.amount`, `fish_caught.yield`, `hold_full.{action,id,required,free}`) | Soi code `chonoi/sim/gather.py` đối chiếu PRD-0 §E | *(Chờ Người 1–2 chuẩn hóa payload & bổ sung test)* | **Chưa đạt** (`gather.py` hiện dùng `count` và payload rỗng cho `oxygen_empty`/`faint`/`hold_full`) |
| Hợp đồng file kho liên thông 2 tiến trình (`gather --inventory-out` → `quan --inventory`) | Chạy 2 tiến trình headless theo ví dụ PRD-0 mục G (`seed=42`) + `test_smoke_p1.Integration` | [smoke-two-process.txt](../proof/phase-1/smoke-two-process.txt), [test-lat3.txt](../proof/phase-1/test-lat3.txt) | **Đạt** (`catch.json={"items":{"bong_sung":2,"ca_loc":1}}`, quán nạp đúng và sinh khách ở tick 120) |
| Quán Lát 3 (N3-01..N3-03): sinh khách theo `phase_tick`, chọn bàn id nhỏ nhất, kho khả dụng & giữ chỗ không trùng, `no_dish`, kiên nhẫn, rời bàn `patience`/`closing` & dọn liên kết | `python tools/test_windows.py` (`test_quan_orders.py`: 10 unit/headless tests) | [test-lat3.txt](../proof/phase-1/test-lat3.txt), [smoke-two-process.txt](../proof/phase-1/smoke-two-process.txt) | **Đạt** |
| Quán Lát 3 (N3-04): dựng fixture 4 trạng thái đơn & từ chối mọi mâu thuẫn mức luật mã `2` trước khi ghi JSONL | `python tools/test_windows.py` (`QuanFixtureValidation`: 4 fixture hợp lệ + 25 case lỗi hộp đen) | [test-lat3.txt](../proof/phase-1/test-lat3.txt) | **Đạt** |
| Quán Lát 4 (N4-01..N4-07): bếp nấu/chín/nhấc món, tương tác ưu tiên bếp trước bàn, phục vụ, boa `floor`, `paid`, uy tín boa, thanh toán khách đang ăn lúc `closing` | Rà `chonoi/sim/quan.py` (headless) | *(Chờ Người 4 ghép vào `TODO(Người 4)` trong `quan.py`)* | **Chưa đạt** (mới có ở `LiveQuanSim` cho live, chưa đưa vào `QuanSim` headless) |
| Cô lập phần sáng tạo live (`LiveGatherSim`, `LiveQuanSim`, `live_world.json`) khỏi headless & contract | `python tools/test_windows.py` (`test_diving.py`, `test_live_world.py`) | [test-lat3.txt](../proof/phase-1/test-lat3.txt) | **Đạt** |
| Quy trình nhóm & hồ sơ: `TEAM.md`, `team_size`, đủ commit 4 người, `.agents/skills/` (≥ 2 skill) | `python tools/check_team.py` | *(Chưa đạt — `TEAM.md` chưa điền tên/GitHub handle 4 thành viên)* | **Chưa đạt** |

## Đánh giá ngắn
- **Đã đạt:** Khung Test Contract headless, kiểm chứng liên thông kho 2 tiến trình, toàn bộ Lát 3 (`quan_orders.py`, `scenario.py`, nối `quan.py`) với **58/58 tests xanh**, và cô lập phần mở rộng live.
- **Chưa đạt (cần chốt ngay trước tag `phase-1`):**
  1. Người 4 ghép Lát 4 (bếp, bưng, phục vụ, tiền/boa, đóng ca cho khách đang ăn) vào `chonoi/sim/quan.py`.
  2. Người 1–2 rà và chuẩn hóa payload sự kiện `chonoi/sim/gather.py` theo PRD-0 §E.
  3. Cả nhóm điền đủ 4 thành viên thật vào `TEAM.md` + `team` trong `game.contract.json`, thêm ≥ 2 skill vào `.agents/skills/`, chạy lại kiểm chứng trên `main` rồi mới gắn tag `phase-1`.
- **Điều cần chỉnh cho phase sau:** Luôn hoàn thiện lõi headless (P0) và khóa danh sách `TEAM.md` trước khi phát triển phần mở rộng đồ họa/live (P2).
