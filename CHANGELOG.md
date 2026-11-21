# Changelog

Tất cả thay đổi đáng chú ý của dự án **Quán Ăn Chợ Nổi (Nhóm DoMiXi)** được ghi nhận tại đây.

## [v1.0.0] — Phase 4: Phát hành chính thức (Test Contract v1.3)

### Added
- `game.contract.json` & `chonoi/__init__.py`: nâng `contract_version` lên `"1.3"`, khai báo `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`) ở gốc hợp đồng; giữ nguyên toàn bộ gameplay, tuning, kho cá thể và JSONL theo Contract v1.2.
- `chonoi/bench.py`: công cụ đo hiệu năng có render 1280×720 cảnh buổi sáng lõi (độ tươi, cá bơi, Cá Sấu Năm Chèo, Út Sen đứng yên ở bến; làm nóng 3 giây, đo `--duration` giây; cửa sổ `tkinter.Canvas` thật kèm bộ đệm RGB 1280×720 dự phòng không cần X11), xuất nguyên tử 5 trường `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms`.
- `chonoi/soak.py`: công cụ kiểm thử bền bỉ headless nhiều ngày (`--seed 7 --days 10 --out soak.json`) bằng bot tất định hoàn toàn đi qua `gather → quan → shop` trong một tiến trình duy nhất; `DaySim` lặp kế hoạch `day_plan` D1–D5 ở Ngày 6–10 và bảo toàn tiền, tổng thu, uy tín, nâng cấp, số Ngày và `IdAllocator` xuyên suốt.
- `chonoi/web/index.html`: bổ sung **3 cảnh báo trực quan bằng chữ và biểu tượng** (Thủy quái gần có hướng & khoảng cách, Oxy sắp hết, Khách sắp giận kèm số giây còn lại), **chế độ Tương phản cao** (nút góc dưới phải + phím tắt `H`), HUD kính mờ + minimap sông 180 m + dải phím keycap + hiệu ứng đèn lồng/hơi bếp/chữ bay `+xu`.
- `chonoi/sim/live_quan.py` & `chonoi/live_world.json`: bổ sung biên hàng rào tre theo phối cảnh, va chạm trượt mép quanh quầy bếp/bàn ăn `T1–T3`/giỏ sen, hành lang vào bếp sau quầy cho Út Sen nấu tại `B1–B2`, và đường đi tránh bàn cho khách vào/ra quán (cô lập hoàn toàn khỏi headless).
- `LICENSE`, `docs/release/v1.0.0.md`, `docs/plan/phase-4.md`, `docs/verification/phase-4.md`, `docs/proof/phase-4/*`, `tests/test_v13_bench_soak.py`.

### Changed
- Cập nhật `README.md` (yêu cầu môi trường, ≤ 3 lệnh chạy từ clone sạch trên macOS/Linux & Windows, điều khiển `H`, lệnh test/headless/bench/soak và giới hạn đã biết), rà `CREDITS.md` và cập nhật `docs/retro.md`, `docs/clarify.md`, `docs/ai-usage-log.md`.
- `.gitignore`: bổ sung bỏ qua `dist/` và `*.log` để giữ repo sạch khi đóng gói phát hành.

## [v1.2.0] — Phase 3: Change Request "Mùa Nước Nổi" (Test Contract v1.2)

### BREAKING CHANGES (thay đổi phá vỡ tương thích ngược với v1.0 / v1.1)
1. **Kho đếm theo loại → kho cá thể có độ tươi:**
   - File kho (`--inventory` / `--inventory-out`) và `gather_end.data.inventory` đổi từ `{"items": {"ca_loc": 1}}` sang mảng cá thể `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}` (kho rỗng là `{"items": []}`).
   - `scenario.gather.hold` đổi từ `["ca_loc", ...]` sang `[{"id": "I1", "kind": "ca_loc", "fresh": 100}, ...]`.
   - `scenario.quan.stock`, snapshot `hold` (`gather`) và snapshot `stock` (`quan`, `shop`) đổi sang mảng cá thể `[{id, kind, fresh}]`.
   - `customers[].reserved` đổi từ object công thức `{"ca_loc": 1}` sang mảng id cá thể `["I1", ...]`.
   - `cook_started.data.items` đổi từ mảng tên loại sang mảng cá thể `{id, kind, fresh}` sắp theo `(kind, id)`.
   - `monster_hit.data.lost` và `faint.data.lost` đổi từ mảng tên loại sang mảng cá thể `{id, kind, fresh}` theo thứ tự bỏ LIFO.
   - Theo Contract v1.2, file kho đếm hoặc fixture kiểu v1.0/v1.1 trả mã thoát `2` trước khi ghi JSONL.
2. **Giá niêm yết → chốt giá theo độ tươi:**
   - Khi `cook_started`, `base_price = floor(giá_niêm_yết × trung_bình_fresh / 100)` tính bằng số hữu tỉ chính xác (`fractions.Fraction`).
   - Tiền boa vẫn tính `floor(base_price × 0.2)` trên `base_price` đã chốt.

### Added
- `game.contract.json`: nâng `contract_version` lên `"1.2"`, bổ sung `tuning.freshness` (`initial: 100`, `gather_decay_per_s: 0.5`, `quan_decay_per_s: 0.25`, `spoiled_below: 30`).
- `chonoi/freshness_v12.py`: mô-đun tính độ tươi bằng số hữu tỉ `Fraction` chính xác tại ngưỡng `30` và phép `floor`.
- Event mới `spoiled` (`{item_id, kind, location}`) phát đúng 1 lần theo thứ tự `id` khi đi từ `>= 30` xuống `< 30`.
- Cơ chế nhả toàn bộ phần giữ và thử giữ lại đúng 1 lần theo `(order_tick, id_key(table_id))` khi nguyên liệu đang giữ bị ươn trong `quan`; chuyển `unfulfillable` nếu không đủ hàng thay thế.
- Cấp id cá thể `I1, I2, ...` tăng liên tục xuyên pha và Ngày (`Day 1` giữ id trong `scenario.gather.hold`, `Day 2+` cấp id mới theo thứ tự mảng).
- `docs/adr/0001-freshness-individual-inventory.md`, `docs/plan/phase-3.md`, `docs/verification/phase-3.md`, `tests/test_v12_freshness.py`.

### Hướng dẫn nâng cấp fixture từ v1.1 → v1.2
- File kho cũ: `{"items": {"ca_loc": 1}}` → mới: `{"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}` (rỗng: `{"items": []}`).
- Scenario `gather.hold`: `["ca_loc"]` → `[{"id": "I1", "kind": "ca_loc", "fresh": 100}]`.
- Scenario `quan.stock`: `{"ca_loc": 1}` → `[{"id": "I1", "kind": "ca_loc", "fresh": 100}]`.
- Scenario `customers[].reserved`: `{"ca_loc": 1}` → `["I1"]` (hoặc bỏ khóa `reserved` để tự cấp từ hàng chưa ươn tươi nhất).

## [v1.1.0] — Phase 2 (Test Contract v1.1)
- Hoàn thiện lõi headless v1.1: `gather` (cá bơi 1.5 m/s, phản xạ mép, đổi hướng 120 tick, sinh cá 360 tick, Cá Sấu Năm Chèo `M1`/`M2`), `quan` (2 bếp `B1–B2`, 4 bàn `T1–T4`, 6 món, lọc `day_plan`), `--mode day --days 1..5`, `ShopSim`, `pause`/`resumed`.
- Bổ sung 2 AI skill tại `.agents/skills/` và gói sáng tạo bản live (cô lập hoàn toàn khỏi headless).

## [v1.0.0-p1] — Phase 1 (PRD-0, Test Contract v1.0)
- Dựng lõi Lát 1–3 (`gather` di chuyển/oxy/hái/bắt, `quan` đơn hàng/giữ chỗ/kiên nhẫn/kiểm fixture) và luồng chơi thử live trên trình duyệt.
