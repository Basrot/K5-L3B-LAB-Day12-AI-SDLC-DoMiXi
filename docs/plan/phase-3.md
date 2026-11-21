# Kế hoạch Phase 3 — Change Request “Mùa Nước Nổi” (TICKET-03, Contract v1.2)

## 1. Mục tiêu (35 phút)
- Triển khai trọn vẹn **lõi Contract v1.2** (nhóm 4 người không bắt buộc mục 2 Mở rộng `current` / `reservations`):
  - Chuyển schema kho đếm → **kho cá thể `{id, kind, fresh}`** (file kho đếm bị từ chối với mã thoát `2`).
  - Hao tươi chính xác (`gather` `-0.5/s`, `quan` `-0.25/s`, ươn `< 30`, phát `spoiled` 1 lần theo `id`, dừng khi `pause`, không hao khi đổi pha hay trong Shop).
  - Giữ chỗ theo ID cá thể (lấy tươi nhất, hòa theo `id`), nhả & thử giữ lại 1 lần khi cá thể giữ vừa ươn (theo `order_tick` rồi `id` bàn), không đủ thì `unfulfillable`.
  - Chốt giá theo độ tươi: `base_price = floor(giá_niêm_yết × avg_fresh / 100)`, sau đó mới tính boa.
  - Giữ xanh toàn bộ bản live (đã có HUD độ tươi từ commit `45adb43`) và regression P1–P2 còn hiệu lực.
- Ghi đầy đủ hồ sơ Change Request: ADR tác động ([0001-freshness-individual-inventory.md](../adr/0001-freshness-individual-inventory.md)), [CHANGELOG.md](../../CHANGELOG.md) breaking change, bằng chứng thật `docs/proof/phase-3/`, ma trận [docs/verification/phase-3.md](../verification/phase-3.md), cập nhật `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`.

## 2. Danh sách AC-P3 & Phân công

| Mã AC | Yêu cầu | File chính | Kiểm chứng |
|---|---|---|---|
| AC-P3-01 | `contract_version: "1.2"` & `tuning.freshness` (`100, 0.5, 0.25, 30`) | `game.contract.json`, `contract.py` | `test_v12_freshness.py` |
| AC-P3-02 | Schema kho cá thể `{"items":[{id,kind,fresh}]}`, từ chối kho đếm mã `2`, cấp ID `I1, I2…` tăng xuyên pha/Ngày | `freshness_v12.py`, `inventory.py`, `scenario.py` | `test_smoke_p1.py`, `test_v12_freshness.py` |
| AC-P3-03 | Hao tươi trong `gather`, ngưỡng đúng `30` → `spoiled(hold)` ở tick 1, `lost` LIFO là mảng cá thể | `chonoi/sim/gather.py` | `test_v12_freshness.py` |
| AC-P3-04 | Hao tươi trong `quan`, `spoiled(stock)` theo `id`, giữ chỗ theo ID tươi nhất, giữ lại 1 lần khi ươn → `unfulfillable` nếu thiếu | `quan_orders.py`, `quan.py` | `test_v12_freshness.py`, `test_quan_orders.py` |
| AC-P3-05 | Chốt `base_price = floor(price * avg_fresh / 100)`, `cook_started.items` là mảng cá thể sort `(kind, id)`, boa trên `base_price` đã chốt | `quan_orders.py`, `quan.py` | `test_v12_freshness.py`, `test_quan_v11.py` |
| AC-P3-06 | Bàn giao 2 tiến trình file kho v1.2 & bàn giao trong `--mode day` (không hao thêm, Ngày kế cấp ID mới, Shop không hao) | `day.py`, `inventory.py` | `docs/proof/phase-3/integration.txt`, `test_v12_freshness.py` |
| AC-P3-07 | Tài liệu Change Request: ADR, `CHANGELOG.md`, `verification/phase-3.md`, `proof/phase-3/`, cập nhật 2 skill v1.2 | `docs/*`, `CHANGELOG.md`, `.agents/skills/*` | Chạy thật 2 skill & full suite |
