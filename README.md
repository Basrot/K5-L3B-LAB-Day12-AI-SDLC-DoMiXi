# Day 12 — AI SDLC: Quán Ăn Chợ Nổi (Nhóm DoMiXi) — v1.0.0

> **Nhóm 4 người (`DoMiXi`)** · Xây game 2D qua **4 phase** theo **Test Contract v1.3** (gameplay, tuning, kho cá thể & độ tươi theo v1.2, bổ sung `bench_cmd` và `soak_cmd`): Út Sen lặn bắt cá, hái rau trên mặt nước, tối mở quán phục vụ khách và nâng cấp đồ nghề qua Shop theo vòng ngày.
> **Lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)**

## Yêu cầu môi trường
- **Python 3.10+** (chỉ dùng **thư viện chuẩn Python**, không cần `pip install` hay cài thư viện ngoài).
- Trình duyệt hiện đại (Chrome / Edge / Safari / Firefox) để chơi bản có giao diện (`chonoi.live`).
- `tkinter` (đi kèm Python trên macOS/Windows; trên Linux nếu không có X11/DISPLAY thì `chonoi.bench` tự chuyển sang bộ đệm RGB 1280×720 dự phòng).
- Hệ điều hành hỗ trợ: **macOS**, **Linux** và **Windows**.

## Chạy nhanh từ clone sạch (≤ 3 lệnh)

### macOS / Linux (3 lệnh)
```bash
git clone https://github.com/Basrot/K5-L3B-LAB-Day12-AI-SDLC-DoMiXi.git
cd K5-L3B-LAB-Day12-AI-SDLC-DoMiXi
python3 -m chonoi.live --mode campaign
```
*(Trình duyệt tự mở bản có giao diện tại `http://127.0.0.1:8080/` — hoặc mở thủ công địa chỉ in ra trên terminal. Có thể đổi cổng bằng `--port 8090`.)*

### Windows (PowerShell — 3 lệnh)
```powershell
git clone https://github.com/Basrot/K5-L3B-LAB-Day12-AI-SDLC-DoMiXi.git
cd K5-L3B-LAB-Day12-AI-SDLC-DoMiXi
python -X utf8 -m chonoi.live --mode campaign --port 8080
```

## Các lệnh kiểm thử, Headless, Benchmark & Soak (Contract v1.3)

### Chạy toàn bộ test & kiểm thành viên
```bash
# macOS / Linux
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 tools/check_team.py

# Windows (PowerShell — tránh alias python3 rỗng của MS Store)
python tools/test_windows.py
python tools/check_team.py
```

### Chạy Headless (Test Contract v1.2 / v1.3)
```bash
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out gather.jsonl --inventory-out catch.json
python3 -m chonoi.headless --mode quan   --seed 1 --inventory catch.json --ticks 600 --out quan.jsonl
python3 -m chonoi.headless --mode day    --days 1 --seed 1 --ticks 22200 --out day.jsonl
```

### Chạy Benchmark 1280×720 (`bench_cmd`) & Soak 10 Ngày (`soak_cmd`)
```bash
# Benchmark cảnh sáng lõi 1280×720 (làm nóng 3 s, đo 30 s, xuất 5 trường JSON)
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

# Soak 10 Ngày liên tục trong 1 tiến trình headless (D6–D10 lặp kế hoạch D1–D5)
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```

## Điều khiển, cảnh báo & khả năng tiếp cận
- **Di chuyển:** `WASD` hoặc phím mũi tên (lặn/nổi/bơi ở cảnh sông `gather`; đi lại phục vụ ở cảnh quán `quan`).
- **Tương tác & bắt cá:** `Space` bắt cá dưới nước; `E` hái rau / nhặt kho báu / cập bến về quán (sáng) hoặc nấu bếp / nhấc món chín / phục vụ khách / báo chú Công An (tối); `R` chơi lại ca hiện tại.
- **Chế độ Tương phản cao:** bấm nút **`◐ Tương phản cao (H)`** ở góc dưới phải hoặc nhấn phím **`H`** bất cứ lúc nào (lưu trạng thái tự động).
- **Ba cảnh báo rõ ràng bằng chữ + biểu tượng** (hoạt động ở cả chế độ thường và Tương phản cao):
  1. **Thủy quái / nguy hiểm gần (`gather`):** biểu ngữ **`⚠️ THỦY QUÁI GẦN: <tên> (<hướng> · <khoảng cách>) — TRÁNH NGAY!`** khi thủy quái, Chú Áo Vàng hoặc sứa/cá độc đến gần.
  2. **Oxy sắp hết (`gather`):** viền nhấp nháy độ tương phản cao kèm biểu ngữ **`🫧 ⚠️ SẮP HẾT OXY! NỔI LÊN NGAY!`** khi oxy ≤ 25% dưới nước.
  3. **Khách sắp giận (`quan`):** vòng cảnh báo nhấp nháy + nhãn **`💢 Sắp giận!`** trên bàn và biểu ngữ **`💢 KHÁCH SẮP GIẬN: <tên> (<bàn>) · còn <giây>s!`** khi kiên nhẫn ≤ 35%.
- **Tính điểm (Contract v1.2 / v1.3):** `score = earned + 100 × floor(reputation)` (tiền tính theo nghìn đồng; giá món chốt theo độ tươi `floor(giá_niêm_yết × trung_bình_fresh / 100)` bằng số hữu tỉ `Fraction` khi bắt đầu nấu; mua nâng cấp ở Shop trừ vào `money`, giữ nguyên `earned` và `score`).

## Giới hạn đã biết (v1.0.0)
- **Mở rộng Section 3 (nhóm 4 người không bắt buộc):** `extensions: []` trong `game.contract.json`; nhóm chưa triển khai bảng xếp hạng cục bộ (`leaderboard`) và phụ đề SFX riêng lẻ.
- **Bản live vs lõi headless:** Các nhân vật/sự kiện sáng tạo (thời tiết, bộ sưu tập dưới nước, Chú Áo Vàng, Khá Bảnh, Chú Công An, Ca Sĩ Jack, chiến dịch `--mode campaign`) chỉ chạy trong bản live và tắt hoàn toàn ở headless để bảo toàn tính tất định Contract v1.3.
- **Benchmark trên máy không có màn hình (CI/SSH Linux):** `chonoi.bench` tự động chuyển sang bộ đệm RGB 1280×720 (`_OffscreenRGBRenderer`) thay vì mở cửa sổ `tkinter`, vẫn xuất đủ 5 trường JSON theo đúng công thức.

---

## Sáng tạo của nhóm (chỉ bật ở bản live — tắt hoàn toàn ở headless)

Toàn bộ mở rộng sáng tạo nằm tách riêng trong `chonoi/sim/live_gather.py`, `chonoi/sim/live_quan.py`, `chonoi/sim/freshness.py`, `chonoi/progression.py`, `chonoi/progression.json`, `chonoi/live_gather.json`, `chonoi/live_world.json` và `chonoi/web/index.html` (nạp qua `deepcopy`, **không sửa `game.contract.json`** và **tắt hoàn toàn ở chế độ headless**):

1. **Chơi theo màn (`--mode campaign`), cốt truyện mở đầu & sảnh chờ:** Màn chào phát nhạc `assets/audio/lobby-music.mp3`; 4 cảnh intro, chọn màn, đi lặn sáng → mở quán tối → nhận sao/xu → cửa hàng nâng cấp bình oxy, mũ, chân vịt, đèn (`chonoi/progression.json`, `docs/plan/level-economy.md`). Tiến độ lưu cục bộ tại `.chonoi-save.json`.
2. **Lặn có animation, hiệu ứng sông nước & bộ sưu tập dưới nước:** Atlas 4×4 (`10-underwater-animation.png`), tia nắng xuyên nước, sóng lăn tăn, bèo lục bình, rong rêu đáy sông, bọt tung & chữ nổi; bộ sưu tập vỏ sò, ngọc trai, bùa cá, bình gốm tách khỏi kho nguyên liệu chuẩn.
3. **Sông mở rộng, thời tiết động & Chú Áo Vàng:** Thời tiết xoay vòng (nắng / mưa / tuyết / sương mù / gió đảo hướng / bong bóng oxy / mưa cá / cầu vồng), độ tươi nguyên liệu và Chú Áo Vàng (`11-rain-pursuer.png`) kèm nhạc `chieu-troi-mua.mp3`.
4. **Nhà bè quán ăn sống động:** Ảnh nền nhà bè (`15-quan-cho-noi.jpg`) căn khớp 2 bếp lò và 3 bàn gỗ ven sông; sprite khách ngồi gọi món & chờ bếp (`16-seated-waiting.png`) nối sang ăn & uống (`13-dining-cast.png`), hoạt ảnh đi bộ vào/ra cầu gỗ và đặt bàn trước.
5. **Sự kiện ngẫu nhiên buổi tối (live):** Khá Bảnh thu bảo kê (`17-kha-banh.png`), Chú Công An tuần tra bắt giữ (`18-cong-an.png`), Ca Sĩ Jack biểu diễn (`19-jack.png` + `thien-ly-oi.mp3`).

### Bằng chứng lõi headless vẫn đúng
- `tests/test_diving.py`, `tests/test_live_world.py`: xác nhận `Session("gather", ...)` và `headless` hoàn toàn cô lập khỏi bản live, không đột biến `game.contract.json`.
- `tests/test_smoke_p1.py`, `tests/test_quan_orders.py`, `tests/test_quan_v11.py`, `tests/test_v11_core.py`, `tests/test_v12_freshness.py`, `tests/test_v13_bench_soak.py` cùng bằng chứng chạy thật tại [`docs/verification/phase-4.md`](docs/verification/phase-4.md) và [`docs/proof/phase-4/`](docs/proof/phase-4/).

---

## Giấy phép, tài sản & tài liệu dự án
- Giấy phép mã nguồn: [`LICENSE`](LICENSE) (MIT); nguồn tài sản & công cụ AI: [`CREDITS.md`](CREDITS.md).
- Lịch sử thay đổi theo phase: [`CHANGELOG.md`](CHANGELOG.md); ghi chú phát hành: [`docs/release/v1.0.0.md`](docs/release/v1.0.0.md).
- Khung kỹ thuật: [`docs/STARTER.md`](docs/STARTER.md), quy ước AI: [`AGENTS.md`](AGENTS.md), phân công nhóm: [`TEAM.md`](TEAM.md), retro & nhật ký AI: [`docs/retro.md`](docs/retro.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md).
