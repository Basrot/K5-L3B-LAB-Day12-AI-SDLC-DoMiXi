# ADR-0001 — Chuyển đổi schema kho đếm (v1.1) sang kho cá thể có độ tươi (v1.2)

- **Ngày:** 2026-11-21 (Phase 3 — TICKET-03 "Mùa Nước Nổi")
- **Trạng thái:** Đã chốt & triển khai
- **Người quyết định:** Người 3 (PO/QA — Đào Ngọc Hân) cùng cả nhóm DoMiXi

## 1. Bối cảnh & Yêu cầu thay đổi
Khách hàng yêu cầu theo dõi độ tươi (`fresh ∈ [0, 100]`) cho **từng cá thể nguyên liệu** từ lúc Út Sen hái/bắt ở buổi sáng đến lúc tiêu vào bếp buổi tối:
- **Breaking change schema kho:** đổi từ `{"items": {"ca_loc": 1}}` (v1.0/v1.1) sang `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}]}` (v1.2). Ở v1.2, file kho đếm trả mã thoát `2`.
- **Hao tươi chính xác:** `gather` giảm `0.5/s` (`1/120` mỗi tick), `quan` giảm `0.25/s` (`1/240` mỗi tick), ươn khi `fresh < 30` (so ngưỡng trước làm tròn), phát `spoiled` đúng 1 lần theo `id`.
- **Giữ chỗ theo ID & giữ lại khi ươn:** `customers[].reserved` là mảng ID cá thể; ưu tiên cá thể tươi nhất (hòa theo `id`); nếu cá thể giữ vừa ươn, nhả toàn bộ phần giữ của đơn và thử giữ lại đúng 1 lần theo `(order_tick, id_key(table_id))`, không đủ thì chuyển `unfulfillable`.
- **Giá theo độ tươi:** `base_price = floor(giá_niêm_yết × avg_fresh / 100)`, sau đó mới tính boa `floor(base_price × 0.2)`.

## 2. Quyết định kỹ thuật
1. **Số học hữu tỉ chính xác (`fractions.Fraction`) trong `chonoi/freshness_v12.py`:**
   - Tránh hoàn toàn sai số dấu phẩy động IEEE-754 tại ngưỡng `30` (1/120 và 1/240 biểu diễn chính xác tuyệt đối) và tại phép `floor` khi chốt giá.
   - Khi xuất file kho (`write_inventory`) và snapshot JSONL, làm tròn 3 chữ số (khớp `jsonl._clean`) nhưng giữ chặt bất đẳng thức `< 30` (nếu `fresh < 30` mà làm tròn thành `30.0` thì kẹp `29.999`) để file kho và tick-0 snapshot quán trùng khớp chính xác và không bao giờ nhảy nhánh khi đọc lại.
2. **Cô lập bản live khỏi breaking change:**
   - Lõi headless (`GatherSim`, `QuanSim`, `DaySim`, `inventory.py`, `scenario.py`) chuyển 100% sang Contract v1.2.
   - Bản live (`LiveGatherSim`, `LiveQuanSim`) giữ tương thích ngược với lớp `freshness.py` / HUD hiện có của đồng đội (`BFNGOC`, `Nam`, `Tài`) để không làm vỡ 17 test bản live.

## 3. Phân tích tác động (Impact Analysis)

| Module | File cần đổi | Test bị ảnh hưởng | Người phụ trách |
|---|---|---|---|
| **Manifest & Freshness Engine** | `game.contract.json`, `chonoi/__init__.py`, `chonoi/contract.py`, `chonoi/freshness_v12.py` (mới) | `test_quan_v11.py` (đổi kiểm `contract_version == "1.2"`), thêm `test_v12_freshness.py` | Người 3 (Đào Ngọc Hân) |
| **Adapter Kho & Scenario** | `chonoi/inventory.py`, `chonoi/scenario.py` | `test_smoke_p1.py` (chuyển fixture kho/hold sang mảng cá thể v1.2, thêm kiểm kho đếm → mã 2) | Người 3 + Người 2 |
| **Buổi sáng (`gather`)** | `chonoi/sim/gather.py` | `test_diving.py`, `test_v11_core.py`, `test_smoke_p1.py` (hold/lost là mảng cá thể, hao tươi bước 1) | Người 3 hỗ trợ Người 1–2 |
| **Buổi tối (`quan`)** | `chonoi/sim/quan_orders.py`, `chonoi/sim/quan.py` | `test_quan_orders.py`, `test_quan_v11.py` (stock/reserved/items theo cá thể, chốt giá theo fresh, giữ lại khi ươn) | Người 3 + Người 4 |
| **Vòng ngày (`day` & `Shop`)** | `chonoi/sim/day.py` | `test_v11_core.py`, `test_v12_freshness.py` (bàn giao mảng cá thể không hao thêm, cấp ID mới Ngày kế) | Người 3 + Người 4 |
| **Bản live & HUD** | `chonoi/sim/live_gather.py`, `chonoi/sim/live_quan.py`, `chonoi/web/index.html` (đã có HUD độ tươi từ `45adb43`) | `test_live_world.py`, `test_live.py` (giữ xanh 100%, không hồi quy) | `BFNGOC`, `Nam`, `Tài`, `Hân` |
| **Tài liệu & QA** | `CHANGELOG.md`, `docs/plan/phase-3.md`, `docs/verification/phase-3.md`, `docs/proof/phase-3/`, `docs/clarify.md`, `docs/ai-usage-log.md`, `.agents/skills/*` | Chạy lại 2 skill smoke & determinism trên v1.2 | Người 3 (QA lead) |

## 4. Thứ tự tích hợp giữ `main` luôn chạy được
1. Thêm `chonoi/freshness_v12.py`, cập nhật `game.contract.json` (`1.2`), `contract.py`, `inventory.py`, `scenario.py`.
2. Cập nhật đồng bộ `gather.py` + `quan_orders.py` + `quan.py` + `day.py` (cả hai đầu bàn giao chuyển sang mảng cá thể cùng lúc) và giữ tương thích lớp live (`live_gather.py`, `live_quan.py`).
3. Cập nhật test hồi quy P1–P2 (ghi rõ lý do từng test đổi) + thêm bộ test đầy đủ `tests/test_v12_freshness.py`.
4. Chạy full suite `python tools/test_windows.py` + smoke 2 tiến trình + `--mode day` + determinism 3 mode → lưu bằng chứng thật vào `docs/proof/phase-3/` trước khi đẩy lên `main`.
