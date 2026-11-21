# Changelog

Tất cả thay đổi đáng chú ý của dự án **Quán Ăn Chợ Nổi (Nhóm DoMiXi)** được ghi nhận tại đây.

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
