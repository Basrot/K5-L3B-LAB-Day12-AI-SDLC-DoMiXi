# TEAM

**Tên nhóm:** DoMiXi **Số người:** 4 (khớp `team_size` trong `game.contract.json`)

| Thành viên         | GitHub handle | Module chính | Vai quy trình                                             | Người dự phòng cho |
| ------------------ | ------------- | ------------ | --------------------------------------------------------- | ------------------ |
| Nam Nguyễn         | `Basrot`      | `sim/gather` | Integrator (giữ `docs/contracts/`, gắn tag)               | `BFNGOC2`          |
| Thiều Thế Ngọc     | `BFNGOC2`     | `client/ui`  | Scrum/Release (đóng gói, demo, UI live)                   | `Basrot`           |
| Đào Ngọc Hân       | `daongochan`  | `sim/quan`   | PO + QA lead (`docs/clarify.md`, `verification`, `proof`) | `DucTai2804`       |
| Trần Trọng Đức Tài | `DucTai2804`  | `qa`         | Tech lead quán (bếp/kinh tế, sự kiện live & QA Lát 4)     | `daongochan`       |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm (≤ 10 dòng)

- Kênh liên lạc: Nhóm chat chung của nhóm DoMiXi và GitHub repo `Basrot/K5-L3B-LAB-Day12-AI-SDLC-DoMiXi`.
- Khi bất đồng về thiết kế: trao đổi nhanh 2 phút; PO chốt nghĩa yêu cầu, Integrator (`Basrot`) quyết kỹ thuật và ghi `docs/clarify.md`.
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trong kênh chung kèm lỗi đã gặp để người dự phòng nhận lát phụ.
- Giờ standup giữa phase: phút 20 mỗi phase (ghi gọn 1 dòng/người tại `docs/standup.md`).
- Cách đọc code của nhau: chéo cặp `Basrot ↔ BFNGOC2` và `daongochan ↔ DucTai2804` rà diff trước khi gộp lên `main`.
- Cách làm việc với Git: làm trên nhánh ngắn hoặc commit rõ phạm vi lên `main`, bắt buộc chạy `python tools/test_windows.py` xanh trước khi push; phần sáng tạo bản live cô lập tuyệt đối khỏi lõi headless.
