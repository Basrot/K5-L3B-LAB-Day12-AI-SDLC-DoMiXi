# Kế hoạch Phase 4 — TICKET-04: Phát hành v1.0.0 (Test Contract v1.3)

- **Mục tiêu:** Đo hiệu năng cảnh buổi sáng 1280×720 (`bench_cmd`), chuẩn bị kiểm thử bền bỉ 10 Ngày headless (`soak_cmd`), bổ sung 3 cảnh báo dễ nhận biết + chế độ tương phản cao trên giao diện, đóng gói bản chạy được từ clone sạch (≤ 3 lệnh), tổng kết retro + phản tư cá nhân, gắn tag `phase-4` và phát hành GitHub Release `v1.0.0` trước **15:00 (3:00)**.
- **Phạm vi (nhóm 4 người — DoMiXi):** Tập trung 100% mục **Lõi (1)**, **Soak headless (2)**, **Quy trình nhóm & Retro (4)** và giữ nguyên mục **Sáng tạo của nhóm** cô lập ở bản live (`extensions: []` trong `game.contract.json`).

## Phân công vai trò Phase 4

| Vai (TICKET-04) | Thành viên đảm nhận | Hạng mục cụ thể |
|---|---|---|
| **Bench / QA** | Đào Ngọc Hân (`daongochan`) | Viết `chonoi/bench.py` (1280×720, làm nóng 3s, đo 30s, 5 trường JSON), `chonoi/soak.py` (10 ngày tất định, lặp D1–D5 ở D6–D10), nâng cấp `DaySim` & `game.contract.json` v1.3, viết `tests/test_v13_bench_soak.py`, chạy đo thật lưu `docs/proof/phase-4/`, lập `docs/verification/phase-4.md`. |
| **Giao diện & Cảnh báo** | BFNGOC (`BFNGOC2`) + Đào Ngọc Hân (`daongochan`) | Bổ sung 3 cảnh báo có biểu tượng & chữ rõ ràng (Thủy quái gần, Oxy sắp hết, Khách sắp giận) và chế độ **Tương phản cao** (nút góc dưới phải + phím `H`) trên `chonoi/web/index.html`; kiểm thử cả 3 cảnh báo ở chế độ tương phản cao. |
| **Đóng gói & Release / Integrator** | Nam Nguyễn (`Basrot`) + Đào Ngọc Hân (`daongochan`) | Rà `README.md` (≤ 3 lệnh từ clone sạch trên macOS/Linux), `LICENSE`, `CREDITS.md`, `CHANGELOG.md` theo từng phase, viết Release notes `docs/release/v1.0.0.md`, kiểm thử clone sạch, đóng gói `quan-an-cho-noi-v1.0.0.zip`, gắn tag `phase-4` & `v1.0.0`, công bố GitHub Release `v1.0.0`. |
| **Điều phối Retro & Phản tư** | Trần Trọng Đức Tài (`DucTai2804`) + Cả 4 thành viên | Rà hành động đã chốt ở Retro P2 trong `docs/retro.md`, cập nhật `docs/clarify.md` & `docs/ai-usage-log.md`, từng thành viên hoàn thiện phản tư cá nhân ≤ 200 từ tại `docs/members/<handle>.md`. |

## Tiêu chí nghiệm thu (AC-P4)

| Mã AC | Yêu cầu | Kiểm chứng |
|---|---|---|
| `AC-P4-01` | `game.contract.json` đặt `contract_version: "1.3"`, khai `bench_cmd` và `soak_cmd` ở gốc; gameplay/tuning/kho/JSONL giữ chuẩn v1.2 | `tests/test_v13_bench_soak.py` + `tests/test_quan_v11.py` |
| `AC-P4-02` | `<bench_cmd> --seed 42 --duration 30 --out bench.json` render cảnh sáng lõi 1280×720 (làm nóng 3s, đo 30s), xuất đúng 5 trường JSON với công thức `avg_fps` và `p1_low_fps` chính xác | Chạy thật `docs/proof/phase-4/bench.json` + unit test công thức |
| `AC-P4-03` | `<soak_cmd> --seed 7 --days 10 --out soak.json` chạy 10 Ngày liên tục trong 1 tiến trình (D6–D10 lặp kế hoạch D1–D5), `days_completed == 10`, `crashes == 0`, kết quả gameplay lặp lại 100% giữa 2 lượt chạy | Chạy thật `docs/proof/phase-4/soak.json` + `soak-determinism.txt` |
| `AC-P4-04` | Ba cảnh báo dễ nhận biết bằng chữ + biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) + chế độ Tương phản cao (`H` / nút bật tắt) hoạt động ổn định, không lỗi JS | `tests/test_v13_bench_soak.py` + `node --check` + kiểm live |
| `AC-P4-05` | Clone sạch chạy được bản giao diện trong ≤ 3 lệnh; đủ `README.md`, `CHANGELOG.md`, `LICENSE`, `CREDITS.md`, `docs/release/v1.0.0.md` và gói phát hành `v1.0.0` | `docs/proof/phase-4/clean-clone.txt` + bản nén release |
| `AC-P4-06` | Regression P1–P3 + test v1.3 đạt 100%; `tools/check_team.py` xanh; `docs/retro.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/verification/phase-4.md` cập nhật khớp commit gắn tag `phase-4` & `v1.0.0` | `docs/proof/phase-4/test-v13-full.txt` |
