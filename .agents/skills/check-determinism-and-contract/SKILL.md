---
name: check-determinism-and-contract
description: Kiểm tra tính tất định byte-từng-byte của headless trên cả 3 mode (gather, quan, day), cô lập phần sáng tạo live khỏi contract, và kiểm danh sách thành viên TEAM.md.
---

# Check Determinism, Contract Isolation & Team Checklist

Skill này đảm bảo mọi thay đổi mới (kể cả phần sáng tạo bản live) **không làm hỏng tính tất định** và **không phá Test Contract v1.2**.

## Khi nào dùng
- Sau khi sửa bất kỳ luật mô phỏng nào trong `chonoi/sim/*.py`, `chonoi/runner.py`, `chonoi/scenario.py`, hoặc `chonoi/live_world.py`.
- Trước khi gắn tag `phase-n` hoặc tạo Release `v1.0.0`.

## Lệnh chạy thật

### 1. Rà tính tất định byte-từng-byte cho cả 3 mode (`gather`, `quan`, `day`)
```powershell
python -c "import subprocess, sys, tempfile; from pathlib import Path; d = Path(tempfile.mkdtemp(prefix='det-v11-')); cases = [('gather', ['--ticks', '400']), ('quan', ['--ticks', '400']), ('day', ['--days', '1', '--ticks', '22200', '--snapshot-every', '1000'])]; [((subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', m, '--seed', '7', *extra, '--out', str(d / f'{m}_1.jsonl')], check=True), subprocess.run([sys.executable, '-m', 'chonoi.headless', '--mode', m, '--seed', '7', *extra, '--out', str(d / f'{m}_2.jsonl')], check=True), assert_eq := ((d / f'{m}_1.jsonl').read_bytes() == (d / f'{m}_2.jsonl').read_bytes()), print(m, 'BYTE_IDENTICAL=' + str(assert_eq)), (None if assert_eq else sys.exit(1)))) for m, extra in cases]"
```

### 2. Kiểm tra danh sách thành viên & khớp `team_size`
```powershell
python tools/check_team.py
```

### 3. Kiểm tra toàn bộ bộ test (gồm cô lập live vs headless)
```powershell
python tools/test_windows.py
```

## Tiêu chí đạt
- Cả 3 mode `gather`, `quan`, `day` đều in `BYTE_IDENTICAL=True`.
- Toàn bộ bộ test trả `OK` (không có trường live-only như `collectibles`, `weather`, `pursuer`, `kha_banh`, `cong_an` lọt vào JSONL headless).
- `tools/check_team.py` in `OK: 4 thành viên: ...` trước khi gắn tag bàn giao.
