# daongochan — phản tư cá nhân

- **Tôi đã làm (kèm commit trên `main`):**
  - Phase 1: triển khai Lát 3 Quán (`chonoi/sim/quan_orders.py`, nối `quan.py`, kiểm mâu thuẫn fixture `scenario.py`, 12 test `test_quan_orders.py`) và gói QA/clarify (`749f020`, `0a1b848`, `dd512bf`).
  - Phase 2: nâng cấp Test Contract v1.1, hoàn thiện trọn lõi headless `QuanSim`, `GatherSim` (cá bơi/sinh, Cá Sấu M1/M2), `--mode day`/Shop/`pause`, 2 AI skill `.agents/skills/`, cùng giao diện nhà bè & khách ngồi/đi vào bản live (`8954d80`, `a84205f`, `1c60ad3`, `611cb86`, `c75481f`).
  - Phase 3: viết ADR `0001-freshness-individual-inventory.md`, triển khai trọn lõi Contract v1.2 (`freshness_v12.py` bằng `Fraction`, kho cá thể, `spoiled`, giữ chỗ theo id, chốt giá theo tươi), `CHANGELOG.md`, 10 test biên `test_v12_freshness.py`, sửa lỗi `--inventory-out` bản live và nâng cấp UI quán/sông (`d817dbc`, `ddcb31d`).
- **Tôi đã review:** rà và tích hợp diff live của `Basrot` (campaign, `cp1252`, poster), `BFNGOC2` (độ tươi/đặt bàn live, equipment) và `DucTai2804` (QA Lát 4, Khá Bảnh, Công An, Ca Sĩ Jack) để đảm bảo 104/104 test xanh và cô lập headless.
- **AI sai ở đâu và tôi phát hiện thế nào:** Ở Phase 1, AI bỏ qua `"reserved": null` thay vì trả mã `2`; ở Phase 3, việc sửa `index.html` bằng thay thế chuỗi ngắn `ctx.restore();` bị khớp 15 chỗ — đã phát hiện ngay qua thống kê tool output, hoàn tác sạch và kiểm lại bằng `node --check` + bộ test.
- **Điều tôi học được:** Viết ADR + chạy kiểm chứng hộp đen 2 tiến trình trước khi gộp giúp đổi schema phá vỡ (v1.1 → v1.2) trơn tru mà không làm gãy tính năng live của cả nhóm.
