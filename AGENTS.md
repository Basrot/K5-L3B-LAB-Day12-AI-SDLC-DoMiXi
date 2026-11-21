# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm

> Cập nhật qua các phase: Phase 1 (khởi tạo + live animation Windows) → Phase 2 (Contract v1.1: `gather` cá bơi/sinh/Cá Sấu, `quan` 2 bếp/4 bàn/6 món, `--mode day`/Shop/`pause`, và 2 skill kiểm chứng). Ngắn gọn, có lệnh chạy thật.

## Lệnh
- Test (Linux/macOS): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Test (Windows): `python tools/test_windows.py`
- Kiểm thành viên: `python tools/check_team.py` (hoặc `python3 tools/check_team.py`)
- Headless v1.1: `python -m chonoi.headless --mode gather|quan|day --seed 1 [--days 1..5] --ticks 600 --out out.jsonl`
- Chơi thử trên trình duyệt (Windows): `python -X utf8 -m chonoi.live --mode gather|quan [--port 8080]` (WASD, E, Space, R)

## Cấu trúc & quy ước
- Khung kỹ thuật: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/`. Hạn chế sửa; mọi thay đổi ở starter (ví dụ nâng cấp Contract v1.1 trên `contract.py`, `inventory.py`, `scenario.py`, `inputs.py`, `runner.py`, `headless.py`) phải ghi rõ lý do trong commit và `docs/clarify.md`.
- Luật chơi lõi (headless): `chonoi/sim/gather.py`, `chonoi/sim/quan.py`, `chonoi/sim/quan_orders.py`, `chonoi/sim/day.py`.
- Phần sáng tạo **chỉ dùng ở bản live** (tắt hoàn toàn ở headless): `chonoi/sim/live_gather.py`, `chonoi/sim/live_quan.py`, `chonoi/live_gather.json`, `chonoi/live_world.json`, `chonoi/live_world.py`.
- **Số liệu chỉ đọc từ `game.contract.json` / dữ liệu**, không hard-code trong luật.
- Mọi số ngẫu nhiên đi qua `Streams` (`chonoi/rng.py`); không dùng `random` toàn cục, không dùng đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` hoặc schema kho khi chưa báo cả nhóm.
- Không đẩy lên `main` khi chưa chạy test xanh (`python tools/test_windows.py`).
- Không bịa yêu cầu: chỗ mơ hồ ghi `docs/clarify.md` và hỏi PO / Anh Năm.
- Không sửa test cho xanh khi luật sai; nếu cập nhật test cũ do đổi luật phase mới (ví dụ v1.0 → v1.1), phải ghi rõ lý do trong commit và `docs/verification/phase-n.md`.

## Quy tắc làm việc với agent
- Mỗi agent một việc rõ ràng (một lát). Đọc PRD/ticket đúng phase và hợp đồng kho trước khi sửa code.
- Agent làm xong phải chạy test và ghi kết quả thật vào mô tả commit hoặc `docs/proof/phase-n/`; người đọc lại diff trước khi đẩy.
- Sáng tạo thêm được khuyến khích nhưng **phải cô lập hoàn toàn khỏi headless** (xem `README.md`, mục "Sáng tạo của nhóm").

## Skills / hooks của nhóm
Đặt tại `.agents/skills/`:
1. **`smoke-inventory-handoff`** (`.agents/skills/smoke-inventory-handoff/SKILL.md`): dùng trước khi gộp PR / gắn tag để chạy kiểm chứng hộp đen liên thông kho 2 tiến trình (`gather --inventory-out` → `quan --inventory`) và vòng ngày `--mode day --days 1`.
2. **`check-determinism-and-contract`** (`.agents/skills/check-determinism-and-contract/SKILL.md`): dùng sau khi sửa luật sim/live để kiểm tra tính tất định byte-từng-byte trên cả 3 mode (`gather`, `quan`, `day`), cô lập phần sáng tạo live khỏi contract và chạy `tools/check_team.py`.

## Ghi chú bản live (đồ họa & âm thanh)
- Atlas lặn: `assets/art-pack/10-underwater-animation.png` (4×4); nền nhà bè quán: `15-quan-cho-noi.jpg`; khách ngồi chờ/gọi món: `16-seated-waiting.png` (4×2); nhân vật sáng tạo live: `11-rain-pursuer.png`, `17-kha-banh.png`, `18-cong-an.png`; âm thanh: `chieu-troi-mua.mp3`.
- Mọi tính năng live cấu hình riêng trong `chonoi/live_gather.json` và `chonoi/live_world.json`, nạp qua `deepcopy` trong `live_tuning()`, tuyệt đối không ghi vào `game.contract.json` hoặc file kho headless.
