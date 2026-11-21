# Ma trận kiểm chứng Phase 4 — Phát hành v1.0.0 (Test Contract v1.3)

- **Nhóm:** DoMiXi (`Basrot`, `BFNGOC2`, `daongochan`, `DucTai2804`)
- **Hợp đồng:** Test Contract **v1.3** (`game.contract.json`: `contract_version: "1.3"`, `bench_cmd`, `soak_cmd`; gameplay, tuning, kho cá thể và JSONL giữ nguyên v1.2).
- **Lệnh kiểm thử chạy thật trên Windows:** `python tools/test_windows.py` (**111/111 tests OK**), `python tools/check_team.py` (**OK: 4 thành viên**).

## 1. Ma trận truy vết AC-P4 → Bằng chứng → Kết quả

| Mã AC | Yêu cầu (TICKET-04) | Bằng chứng thật | Kết quả |
|---|---|---|---|
| `AC-P4-01` | `game.contract.json` khai `contract_version: "1.3"`, `bench_cmd` và `soak_cmd` ở gốc; gameplay/tuning/kho/JSONL theo v1.2 | `game.contract.json`, `chonoi/__init__.py`, `tests/test_v13_bench_soak.py`, `tests/test_quan_v11.py`, [`docs/proof/phase-4/test-v13-full.txt`](../proof/phase-4/test-v13-full.txt) | **Đạt** |
| `AC-P4-02` | `<bench_cmd> --seed 42 --duration 30 --out bench.json` render cảnh buổi sáng lõi `1280×720` (độ tươi, cá bơi, Cá Sấu Năm Chèo, Út Sen đứng yên ở bến; làm nóng 3 s, đo 30 s) và xuất đúng 5 trường JSON theo công thức | `chonoi/bench.py`, [`docs/proof/phase-4/bench.json`](../proof/phase-4/bench.json) (`avg_fps: 72.68`, `p1_low_fps: 20.0`, `frames: 2181`, `measured_s: 30.009`, `load_ms: 500.31`) | **Đạt** *(báo cáo mốc tham khảo: avg ≥ 60 FPS đạt `72.68`, load ≤ 10 s đạt `0.50 s`, 1% low `20.0 FPS` do Tk GDI spike trên Windows)* |
| `AC-P4-03` | `<soak_cmd> --seed 7 --days 10 --out soak.json` chạy 10 Ngày liên tục trong 1 tiến trình (D6–D10 lặp kế hoạch D1–D5), giữ xuyên suốt tiền/tổng thu/uy tín/nâng cấp/id; `days_completed == 10`, `crashes == 0`, lặp lại tuyệt đối ở các trường gameplay | `chonoi/soak.py`, `chonoi/sim/day.py`, [`docs/proof/phase-4/soak.json`](../proof/phase-4/soak.json), [`docs/proof/phase-4/soak-determinism.txt`](../proof/phase-4/soak-determinism.txt) (`days_completed: 10`, `crashes: 0`, Day 10: `earned=258, reputation=4.2, score=658`, 2 lượt giống nhau `True`) | **Đạt** |
| `AC-P4-04` | Ba cảnh báo dễ nhận biết bằng chữ + biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) + chế độ **Tương phản cao** (`H` / nút góc dưới phải) hoạt động ở cả 3 cảnh báo | `chonoi/web/index.html`, `tests/test_v13_bench_soak.py::test_ui_has_three_clear_warnings_and_high_contrast_mode`, kiểm cú pháp JS `node --check` (`exit 0`) | **Đạt** |
| `AC-P4-05` | Từ clone sạch chạy được bản có giao diện trong ≤ 3 lệnh theo `README.md`; đầy đủ `CHANGELOG.md`, `LICENSE`, `CREDITS.md`, Release notes `docs/release/v1.0.0.md` và bản đóng gói phát hành `v1.0.0` | `README.md`, `CHANGELOG.md`, `LICENSE`, `CREDITS.md`, [`docs/release/v1.0.0.md`](../release/v1.0.0.md), [`docs/proof/phase-4/clean-clone.txt`](../proof/phase-4/clean-clone.txt) | **Đạt** |
| `AC-P4-06` | Regression P1–P3 + v1.3 xanh toàn bộ; `tools/check_team.py` xanh; cập nhật `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md` (rà hành động P2), `docs/members/<handle>.md`; tag `phase-4` & `v1.0.0` cùng trỏ tới commit bàn giao trên `main` | [`docs/proof/phase-4/test-v13-full.txt`](../proof/phase-4/test-v13-full.txt) (`112/112 OK`, `check_team.py OK`), `docs/retro.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/members/` (đầy đủ 4/4 thành viên: `Basrot.md`, `BFNGOC2.md`, `daongochan.md`, `DucTai2804.md`) | **Đạt** |

## 2. Chi tiết số liệu đo thật (Phase 4)

### 2.1 Benchmark render `1280×720` (`docs/proof/phase-4/bench.json`)
- **Lệnh chạy thật:** `python -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` (cửa sổ `tkinter.Canvas` thật `1280×720`, làm nóng 3 s + đo 30 s, tối ưu bỏ polygon stipple GDI từ 50.75 FPS lên 72.68 FPS).
- **Kết quả JSON nguyên văn:**
  ```json
  {"avg_fps":72.68,"p1_low_fps":20.0,"frames":2181,"measured_s":30.009,"load_ms":500.31}
  ```
- **Đối chiếu mốc báo cáo:**
  - `avg_fps`: **72.68 FPS** (mốc báo cáo ≥ 60 FPS — **Đạt**)
  - `load_ms`: **500.31 ms** = **0.50 s** (mốc báo cáo ≤ 10 s — **Đạt**)
  - `p1_low_fps`: **20.0 FPS** (mốc báo cáo ≥ 30 FPS — thấp hơn do GDI flush cục bộ của `tkinter.Canvas` trên Windows; đã tối ưu gỡ stipple nâng `p1_low_fps` từ `16.26` lên `20.0` và ghi nhận trung thực trong Release notes `v1.0.0`).

### 2.2 Soak headless 10 Ngày (`docs/proof/phase-4/soak.json`)
- **Lệnh chạy thật:** `python -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json`
- **Kết quả:** `days: 10`, `days_completed: 10`, `crashes: 0`, `duration_s: 11.213` (lượt 2: `7.499 s`).
- **Tính lặp lại giữa 2 lượt chạy:** `days`, `days_completed`, `crashes` và toàn bộ mảng `results[0..9]` giống nhau 100% (`True`, xem [`soak-determinism.txt`](../proof/phase-4/soak-determinism.txt)).
- **Tiến triển Ngày 1 → Ngày 10:** `earned: 43 → 258`, `reputation: 3.2 → 4.2`, `score: 343 → 658` (D6–D10 lặp đúng `day_plan` D1–D5).

### 2.3 Kiểm thử hồi quy P1–P3 + v1.3 & Cô lập sáng tạo
- `python tools/test_windows.py`: **111/111 tests OK** (gồm toàn bộ smoke P1, đơn hàng/giữ chỗ, v1.1 `gather`/`quan`/`day`, v1.2 độ tươi `Fraction`, v1.3 `bench`/`soak`/cảnh báo, chiến dịch & sự kiện live).
- `python tools/check_team.py`: `OK: 4 thành viên: Basrot, BFNGOC2, daongochan, DucTai2804`.
- Clone sạch từ commit `HEAD` vào thư mục tạm: kiểm chạy kiểm thử, `check_team.py`, headless và khởi chạy HTTP server `chonoi.live` đều hoạt động trực tiếp bằng thư viện chuẩn Python (xem [`docs/proof/phase-4/clean-clone.txt`](../proof/phase-4/clean-clone.txt)).
