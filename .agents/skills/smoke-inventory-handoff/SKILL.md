---
name: smoke-inventory-handoff
description: Chạy kiểm chứng hộp đen liên thông kho 2 tiến trình (gather -> inventory -> quan) và vòng ngày (--mode day) theo Test Contract v1.1. Dùng trước khi gộp nhánh lên main hoặc trước khi gắn tag phase-n.
---

# Smoke Inventory Handoff & Day Cycle (Contract v1.1)

Skill này chạy kiểm chứng hộp đen (black-box) bằng chính CLI `chonoi.headless` để xác nhận:
1. `gather --inventory-out` ghi đúng file kho JSON theo mục G (`{"items":{...}}`, ghi nguyên tử, chỉ ghi 6 nguyên liệu lõi v1.1).
2. `quan --inventory` nạp đúng kho đó và nấu được món mới v1.1 (`lau_mam`, `ca_keo_nuong`, `canh_chua_ca_loc`).
3. `--mode day --days 1` hoàn thành trọn vòng `gather → quan → shop` với `reason: "days_complete"` và `days_completed: 1`.

## Khi nào dùng
- Trước khi tạo PR / gộp vào `main`.
- Tại mốc phút 20 của mỗi phase (lưu bằng chứng vào `docs/proof/phase-n/integration.txt`).
- Trước khi gắn tag bàn giao `phase-1`…`phase-4`.

## Lệnh chạy thật

### macOS / Linux
```bash
PYTHONPATH=tests:. python3 -m unittest tests.test_smoke_p1 tests.test_quan_v11 tests.test_v11_core -v
```

### Windows (PowerShell)
```powershell
python tools/test_windows.py
```

### Chạy nhanh smoke 2 tiến trình + vòng ngày `--mode day` (lưu log bằng chứng)
```powershell
python -c "import json, os, subprocess, sys, tempfile; from pathlib import Path; d = tempfile.mkdtemp(prefix='smoke-v11-'); sc = os.path.join(d, 'g.json'); inp = os.path.join(d, 'i.json'); inv = os.path.join(d, 'catch.json'); go = os.path.join(d, 'g.jsonl'); qo = os.path.join(d, 'q.jsonl'); do = os.path.join(d, 'd.jsonl'); Path(sc).write_text(json.dumps({'gather': {'hold': ['ca_linh', 'ca_linh', 'ca_keo', 'keo_neo', 'bong_dien_dien'], 'random_fish': False, 'monsters': []}}), encoding='utf-8'); Path(inp).write_text(json.dumps({'frames': [{'tick': 0, 'interact': True}]}), encoding='utf-8'); r1 = subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'gather', '--seed', '42', '--scenario', sc, '--inputs', inp, '--ticks', '1', '--out', go, '--inventory-out', inv], check=True); r2 = subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'quan', '--seed', '42', '--inventory', inv, '--ticks', '125', '--snapshot-every', '120', '--out', qo], check=True); r3 = subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'day', '--days', '1', '--seed', '42', '--ticks', '22200', '--snapshot-every', '1000', '--out', do], check=True); print('catch.json:', Path(inv).read_text(encoding='utf-8').strip()); print('day end:', Path(do).read_text(encoding='utf-8').splitlines()[-1])"
```

## Tiêu chí đạt
- Mọi tiến trình trả mã thoát `0`.
- `catch.json` khớp chính xác `{"items":{"bong_dien_dien":1,"ca_keo":1,"ca_linh":2,"keo_neo":1}}`.
- Dòng cuối `day` có `"reason":"days_complete"` và `"days_completed":1`.
- Không có nguyên liệu sáng tạo của bản live (`ca_ro`, `tom_song`, `shell`...) xuất hiện trong `catch.json` hay JSONL headless.
