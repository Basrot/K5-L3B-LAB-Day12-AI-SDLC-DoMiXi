# daongochan — phản tư cá nhân

- **Tôi đã làm (commit trên `main`):**
  - P1: Lát 3 Quán (`quan_orders.py`, `scenario.py`, 12 test `test_quan_orders.py`, QA/clarify: `749f020`, `0a1b848`, `dd512bf`).
  - P2: Lõi Contract v1.1 (`QuanSim`, `GatherSim` cá bơi/Cá Sấu, `--mode day`/Shop/`pause`), 2 skill `.agents/skills/`, giao diện nhà bè & khách vào/ra bản live (`611cb86`, `c75481f`).
  - P3: ADR `0001`, lõi Contract v1.2 (`freshness_v12.py` bằng `Fraction`, kho cá thể, `spoiled`, chốt giá theo tươi), `CHANGELOG.md`, 10 test biên, sửa `--inventory-out` live & nâng cấp UI (`d817dbc`, `ddcb31d`, `748a451`).
  - P4: Contract v1.3 (`bench.py` 1280×720, `soak.py` 10 ngày), 3 cảnh báo + Tương phản cao (`H`), `LICENSE`, đóng gói `v1.0.0`.
- **Hỗ trợ & review:** Rà diff và tích hợp nhánh live của `Basrot`, `BFNGOC2`, `DucTai2804`, giữ 111/111 test xanh và cô lập headless.
- **AI sai ở đâu:** P1 bỏ qua `"reserved": null`; P3 vỡ `--inventory-out` live; P4 polygon stipple Tk chỉ đạt 50.75 FPS. Phát hiện bằng audit CLI và đo thật 30s (tối ưu lên 72.68 FPS).
- **Bài học:** ADR + kiểm chứng hộp đen và đo chạy thật giúp nâng cấp hợp đồng an toàn.
