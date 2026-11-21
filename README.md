# Day 12 — AI SDLC: Quán Ăn Chợ Nổi (Nhóm DoMiXi)

> **Làm theo nhóm 4 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước, tối mở quán phục vụ khách và nâng cấp đồ nghề qua Shop theo vòng ngày (Test Contract **v1.1**).
> **Lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)**

## Bắt đầu nhanh (≤ 3 lệnh từ clone sạch)

### macOS / Linux
```bash
git clone https://github.com/Basrot/K5-L3B-LAB-Day12-AI-SDLC-DoMiXi.git && cd K5-L3B-LAB-Day12-AI-SDLC-DoMiXi
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v        # chạy toàn bộ test
python3 -m chonoi.live --mode campaign                              # chơi thử trên trình duyệt
```

### Windows (PowerShell)
```powershell
python tools/test_windows.py                                        # chạy toàn bộ test (thay alias python3 trong bộ nhớ)
python -X utf8 -m chonoi.live --mode campaign --port 8080           # chơi thử tại http://127.0.0.1:8080/
```

### Chạy Headless (Test Contract v1.1)
```bash
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out gather.jsonl --inventory-out catch.json
python3 -m chonoi.headless --mode quan   --seed 1 --inventory catch.json --ticks 600 --out quan.jsonl
python3 -m chonoi.headless --mode day    --days 1 --seed 1 --ticks 22200 --out day.jsonl
```

## Điều khiển & cách tính điểm
- **Điều khiển:** `WASD` / phím mũi tên để bơi (`gather`) hoặc đi lại (`quan`); `Space` bắt cá dưới nước; `E` tương tác (cập bến / hái rau / nhặt đồ ở buổi sáng; nấu / lấy món / phục vụ ở buổi tối); `R` chơi lại.
- **Tính điểm (Contract v1.1):** `score = earned + 100 × floor(reputation)` (tiền tính theo nghìn đồng; mua nâng cấp trong Shop trừ vào `money`, giữ nguyên `earned` và `score`).

---

## Sáng tạo của nhóm (chỉ bật ở bản live — tắt hoàn toàn ở headless)

Toàn bộ mở rộng sáng tạo nằm tách riêng trong `chonoi/sim/live_gather.py`, `chonoi/sim/live_quan.py`, `chonoi/sim/freshness.py`, `chonoi/progression.py`, `chonoi/progression.json`, `chonoi/live_gather.json`, `chonoi/live_world.json` và `chonoi/web/index.html` (nạp qua `deepcopy`, **không sửa `game.contract.json`** và **tắt hoàn toàn ở chế độ headless**):

1. **Chơi theo màn (`--mode campaign`), cốt truyện mở đầu & sảnh chờ:** Chạy `python -m chonoi.live --mode campaign` (hoặc bỏ `--mode`). Màn chào phát nhạc `assets/audio/lobby-music.mp3`; lần chơi đầu hiện 4 cảnh intro, chọn màn, đi lặn sáng → mở quán tối → nhận sao/xu → nâng cấp bình oxy, mũ, chân vịt, đèn (`chonoi/progression.json`, `docs/plan/level-economy.md`). Trong ca bấm **⌂ Về sảnh** để tạm dừng và quay lại sau, hoặc **Xem lại intro**. Tiến độ lưu tại `.chonoi-save.json` ở máy chạy game.
2. **Lặn có animation & bộ sưu tập dưới nước:** Atlas 4×4 (`assets/art-pack/10-underwater-animation.png`: lặn, bơi chìm, nhặt đồ, nổi) chọn frame theo vận tốc và tick; bộ sưu tập vỏ sò, ngọc trai, bùa cá, bình gốm (`chonoi/live_gather.json`) tách riêng khỏi kho nguyên liệu chuẩn.
3. **Sông mở rộng, thời tiết động, độ tươi nguyên liệu & Chú Áo Vàng:** Thời tiết xoay vòng nắng / mưa / tuyết / gió đảo hướng / bong bóng oxy / mưa cá; độ tươi nguyên liệu (`chonoi/sim/freshness.py`); khi mưa và đang lặn, Chú Áo Vàng (`11-rain-pursuer.png`) truy đuổi (chạm mất 1 HP, có miễn nhiễm để thoát, nổi lên hoặc hết mưa thì dừng), kèm âm thanh `chieu-troi-mua.mp3`.
4. **Nhà bè quán ăn sống động:** Ảnh nền nhà bè (`15-quan-cho-noi.jpg`) căn khớp 2 bếp lò và 3 bàn gỗ ven sông; bộ sprite khách ngồi gọi món & chờ bếp (`16-seated-waiting.png`) nối mượt sang ăn & uống (`13-dining-cast.png`), kèm hoạt ảnh khách đi bộ từ cầu gỗ vào ngồi bàn và rời quán.
5. **Sự kiện ngẫu nhiên buổi tối (live):** Nhân vật Khá Bảnh thu bảo kê (`17-kha-banh.png`) và Chú Công An tuần tra bắt giữ (`18-cong-an.png`) trong `LiveQuanSim`.

### Bằng chứng lõi headless vẫn đúng
- `tests/test_diving.py`, `tests/test_live_world.py`: xác nhận `Session("gather", ...)` và `headless` không có `collectibles`, không dùng tiến độ campaign, không đột biến `game.contract.json`, và `inventory_items()` lọc chỉ giữ đúng 6 nguyên liệu lõi Contract v1.1.
- `tests/test_smoke_p1.py`, `tests/test_quan_orders.py`, `tests/test_quan_v11.py`, `tests/test_v11_core.py` + bằng chứng chạy thật tại [`docs/verification/phase-2.md`](docs/verification/phase-2.md) và [`docs/proof/phase-2/`](docs/proof/phase-2/).

---

## Bắt buộc & Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 (TICKET-02, v1.1) | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Chi tiết khung kỹ thuật ở [`docs/STARTER.md`](docs/STARTER.md), quy ước AI ở [`AGENTS.md`](AGENTS.md), phân công nhóm ở [`TEAM.md`](TEAM.md) và [`PHAN_CONG_CONG_VIEC.md`](PHAN_CONG_CONG_VIEC.md).
