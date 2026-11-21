---
name: smoke-inventory-handoff
description: Chạy kiểm chứng hộp đen liên thông kho 2 tiến trình (gather -> inventory -> quan), kiểm ngưỡng ươn 30 và vòng ngày (--mode day) theo Test Contract v1.2. Dùng trước khi gộp nhánh lên main hoặc trước khi gắn tag phase-n.
---

# Smoke Inventory Handoff, Freshness Threshold & Day Cycle (Contract v1.2)

Skill này chạy kiểm chứng hộp đen (black-box) bằng chính CLI `chonoi.headless` để xác nhận:
1. `gather --inventory-out` ghi đúng file kho cá thể v1.2 (`{"items":[{"id":"I1","kind":"ca_linh","fresh":99.992}]}`, ghi nguyên tử, sắp theo `id`, chỉ gồm 6 nguyên liệu lõi).
2. `quan --inventory --ticks 0` đọc lại file kho đó và khớp chính xác `id`, `kind`, `fresh` (đồng thời từ chối file kho đếm kiểu cũ với mã thoát `2`).
3. Ngưỡng ươn `fresh: 30` ở `gather` phát đúng 1 event `spoiled` tại tick `1` (`location: "hold"`).
4. `--mode day --days 1` hoàn thành trọn vòng `gather → quan → shop` với `reason: "days_complete"` và `days_completed: 1`.

## Khi nào dùng
- Trước khi tạo PR / gộp vào `main`.
- Tại mốc kiểm chứng mỗi phase (lưu bằng chứng vào `docs/proof/phase-n/integration.txt`).
- Trước khi gắn tag bàn giao `phase-3`, `phase-4`.

## Lệnh chạy thật

### macOS / Linux
```bash
PYTHONPATH=tests:. python3 -m unittest tests.test_smoke_p1 tests.test_quan_v11 tests.test_v11_core tests.test_v12_freshness -v
```

### Windows (PowerShell)
```powershell
python tools/test_windows.py
```

### Chạy nhanh smoke TICKET-03 (bàn giao file v1.2 + ngưỡng 30 + vòng ngày `--mode day`)
```powershell
python -c "import json, os, subprocess, sys, tempfile; from pathlib import Path; d = tempfile.mkdtemp(prefix='smoke-v12-'); sc = os.path.join(d, 'g.json'); sc30 = os.path.join(d, 'g30.json'); inp = os.path.join(d, 'i.json'); inv = os.path.join(d, 'catch.json'); go = os.path.join(d, 'g.jsonl'); g30 = os.path.join(d, 'g30.jsonl'); qo = os.path.join(d, 'q.jsonl'); do = os.path.join(d, 'd.jsonl'); Path(sc).write_text(json.dumps({'gather': {'hold': [{'id': 'I1', 'kind': 'ca_linh', 'fresh': 100}], 'random_fish': False, 'monsters': []}}), encoding='utf-8'); Path(sc30).write_text(json.dumps({'gather': {'hold': [{'id': 'I1', 'kind': 'ca_linh', 'fresh': 30}], 'random_fish': False, 'monsters': []}}), encoding='utf-8'); Path(inp).write_text(json.dumps({'frames': [{'tick': 0, 'interact': True}]}), encoding='utf-8'); subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'gather', '--seed', '1', '--scenario', sc, '--inputs', inp, '--ticks', '1', '--out', go, '--inventory-out', inv], check=True); subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'quan', '--seed', '1', '--inventory', inv, '--ticks', '0', '--out', qo], check=True); subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'gather', '--seed', '1', '--scenario', sc30, '--ticks', '1', '--out', g30], check=True); subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', 'day', '--days', '1', '--seed', '42', '--ticks', '22200', '--snapshot-every', '1000', '--out', do], check=True); saved = json.loads(Path(inv).read_text(encoding='utf-8')); q0 = json.loads(Path(qo).read_text(encoding='utf-8').splitlines()[0]); sp = [json.loads(l) for l in Path(g30).read_text(encoding='utf-8').splitlines() if '\"spoiled\"' in l]; assert q0['stock'] == saved['items']; assert len(sp) == 1 and sp[0]['tick'] == 1; print('catch.json:', saved); print('quan_tick0_match:', q0['stock'] == saved['items']); print('spoil_tick1:', sp[0]); print('day_end:', Path(do).read_text(encoding='utf-8').splitlines()[-1])"
```

## Tiêu chí đạt
- Mọi tiến trình trả mã thoát `0`.
- `catch.json` là `{"items":[{"id":"I1","kind":"ca_linh","fresh":99.992}]}` và khớp chính xác `quan` tick-0 snapshot `stock`.
- Mẫu `fresh: 30` phát đúng 1 event `spoiled` tại tick `1` (`location: "hold"`).
- Dòng cuối `day` có `"reason":"days_complete"` và `"days_completed":1`.
- Không có nguyên liệu/trường sáng tạo bản live lọt vào `catch.json` hay JSONL headless.
