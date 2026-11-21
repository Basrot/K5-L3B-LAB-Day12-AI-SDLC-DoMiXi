# DoMiXi — Phân công phát triển Quán Ăn Chợ Nổi cho 4 người

> Căn cứ: PRD-0 Phase 1 và Test Contract v1.0 do nhóm cung cấp, README và mã hiện có trong repo.
> Dùng bảng này làm backlog chung. Thay Người 1–4 bằng tên và GitHub handle thật trong 15 phút kickoff.
> Chưa có Ticket-02/03/04: phần phase sau dưới đây là cách phối hợp, không phải yêu cầu sản phẩm đã được phát hành.

## 1. Mục tiêu và thứ tự ưu tiên

1. **P0 — Lõi:** chơi được buổi sáng và buổi tối; đúng luật, tick, schema, event và kho liên thông theo PRD-0.
2. **P1 — Trải nghiệm:** HUD rõ, nhân vật/animation, nguyên liệu và món có hình/tên, thao tác dễ hiểu.
3. **P2 — Sáng tạo:** mưa, nhân vật áo vàng truy đuổi, sông rộng, cá/vật phẩm mới, bàn có tên và khách ăn/uống. Chỉ bật trong live, tắt ở headless.

Nhóm 4 người không bắt buộc làm mở rộng. Khi thiếu thời gian, cả nhóm ưu tiên P0 và bằng chứng bàn giao trước P2.

## 2. Bảng người phụ trách

| Người | Tên / GitHub handle (điền thật) | Lát chính theo PRD §6.2 | Vai quy trình | Phần UI / sáng tạo đi kèm | Người hỗ trợ / review |
|---|---|---|---|---|---|
| **Người 1** | Chưa điền / `@...` | **Lát 1:** bơi, oxy, biên, giỏ | **Integrator:** điều phối tích hợp, giữ interface, gắn tag sau bàn giao | Animation lặn/bơi/nổi, camera sông, thời tiết, truy đuổi và HP trong live | Người 2 review; hỗ trợ Người 4 khi bị chậm |
| **Người 2** | Chưa điền / `@...` | **Lát 2:** hái, bắt cá, cập bến, file kho | **Scrum/Release:** theo dõi mốc, phối hợp đóng gói/demo | Asset nguyên liệu/cá/vật phẩm, tên và icon kho, UI tương tác/thu hoạch | Người 1 review; hỗ trợ Người 3 |
| **Người 3** | Chưa điền / `@...` | **Lát 3:** khách, giữ chỗ nguyên liệu, kiên nhẫn | **PO + QA lead:** hỏi chỗ mơ hồ, giữ ma trận truy vết | Khách đa dạng, tên bàn, món gọi, kiên nhẫn, hình ăn/uống | Người 4 review; hỗ trợ Người 2 |
| **Người 4** | Chưa điền / `@...` | **Lát 4:** bếp, bưng, phục vụ, tiền | **Tech lead quán:** ghép luật quán và rà kinh tế | Hình bếp/món ăn, trạng thái nấu/chín, món trên tay, tiền/uy tín/kết ca | Người 3 review; hỗ trợ Người 1 |

**Nguyên tắc:** cả 4 người đều làm gameplay và tự ghi bằng chứng phần mình. Không giao một người chỉ làm test hoặc chỉ làm tài liệu trong khi hai buổi chưa có đủ luật.

## 3. Công việc chi tiết và điều kiện bàn giao

### Người 1 — Bơi, sinh tồn và tích hợp

| Mã nội bộ | Việc phải làm | File / phạm vi | Bàn giao khi |
|---|---|---|---|
| N1-01 | Bơi `[x,d]`, chuẩn hóa input, ramp, hướng mặt, chặn biên và vận tốc hướng ra ngoài | Phần di chuyển trong `chonoi/sim/gather.py`, phối hợp khung inputs/ramp | Đi ngang/dọc/chéo đúng tốc độ; không vượt miền; đứng yên giữ hướng cuối |
| N1-02 | Oxy dưới nước, hồi ở mặt nước, đếm ngạt, trừ HP và ngất | Phần sinh tồn trong `gather.py` | Đúng thứ tự PRD §F; nổi đúng tick ngạt được hồi; ngất dừng bước và kho rỗng |
| N1-03 | Giỏ có sức chứa, thứ tự nhặt và bỏ theo LIFO | Interface giỏ dùng chung với Người 2 | Không nhận quá trần; event `faint` có `cause`, `lost` đúng thứ tự, `hp:0` |
| N1-04 | Snapshot và event sinh tồn đúng schema | `gather.py`, phối hợp Người 2 | `dive/surface` đúng mép; `oxygen_empty` có `oxygen_ticks:0`; không phát thừa event |
| N1-05 | Ghép các thay đổi của Người 2 vào vòng `step` đúng thứ tự | Chủ trì tích hợp `gather.py` | Hái/bắt ở tick cuối vẫn vào kho; bến ưu tiên trước hái; ngất ưu tiên dừng bước |
| N1-06 | Nối sprite lặn/bơi/nhặt/nổi theo tick; camera theo nhân vật | `chonoi/web/`, `assets/art-pack/` | Nhân vật thực sự nằm dưới mặt nước; hướng và frame không phụ thuộc tốc độ render |
| N1-07 | Hoàn thiện mưa và Chú Áo Vàng chỉ trong live | `sim/live_gather.py`, `live_world.json` | Mưa mới xuất hiện; chạm trừ 1 HP; có miễn nhiễm để thoát; lên mặt nước/hết mưa ngừng đuổi |
| N1-08 | Ghép main và gắn tag theo mốc | Git + checklist bàn giao | Tag trỏ đúng commit main; ghi trung thực phần chưa đạt; không gắn tag trước cho đủ tên |

### Người 2 — Thu hoạch, kho và bộ hình

| Mã nội bộ | Việc phải làm | File / phạm vi | Bàn giao khi |
|---|---|---|---|
| N2-01 | Hái ở mặt nước; chọn nút ready gần nhất, hòa theo id; mọc lại | Phần tài nguyên `gather.py` hoặc helper mới do hai người thống nhất | Đúng bán kính kể cả mép; giỏ đầy giữ nguyên cây; tick mọc lại hái được ngay |
| N2-02 | Bắt cá dưới nước; chọn đúng một đàn; đủ toàn bộ yield mới nhận | Phần tài nguyên gather | Thiếu chỗ không bắt một phần, không thử đàn khác; không đặt cooldown nếu bắt hụt/đầy |
| N2-03 | Cập bến/hết giờ/ngất và chuyển giỏ thành kho | Phối hợp `gather.py`, đọc hiểu `inventory.py`/`runner.py` | Event inventory và file trùng nhau; chưa kết thúc không tạo/ghi đè kho; ghi nguyên tử đúng một lần |
| N2-04 | Chốt schema kho và mẫu với Người 3–4 | `docs/contracts/`, `inventory.sample.json` | Chỉ `{"items":{...}}`; đúng 4 kind lõi; bỏ lượng 0; không ghi cá/item sáng tạo vào kho chuẩn |
| N2-05 | Rà payload sự kiện thu hoạch theo PRD §E | `gather.py` | `gather` dùng `amount`, `fish_caught` dùng `yield`; `hold_full` đủ action/id/required/free |
| N2-06 | Phân loại, đặt tên, căn ô và gắn hình cá/vật phẩm/món | `assets/art-pack/`, `chonoi/web/`, `CREDITS.md` | Ảnh không lẫn ô/cắt nhân vật; tên rõ; có fallback khi ảnh chưa tải; ghi công cụ/nguồn |
| N2-07 | Sông rộng và đồ nhặt mới chỉ trong live | `live_world.json`, phối hợp Người 1 | Cá/item mới có tên, icon và vị trí; camera vẫn nhìn rõ; không đổi headless |
| N2-08 | Hướng dẫn chạy, release note và kịch bản demo | `README.md`, `CHANGELOG.md`, `CREDITS.md` | Cách chạy từ clone sạch tối đa 3 lệnh trên macOS/Linux; demo dưới 5 phút |

### Người 3 — Khách, đơn và kiểm chứng

| Mã nội bộ | Việc phải làm | File / phạm vi | Bàn giao khi |
|---|---|---|---|
| N3-01 | Sinh khách theo phase_tick; chọn bàn trống id nhỏ nhất | Luật khách `chonoi/sim/quan.py` / helper thống nhất với Người 4 | Khách mới chỉ tham gia bước sau; không sinh khi hết ca hoặc hết bàn; tôn trọng `random_customers:false` |
| N3-02 | Kho khả dụng = tồn vật lý − giữ chỗ; chọn đều món đủ nguyên liệu qua Streams | Luật khách/đơn quán | Hai đơn không giữ trùng một lượng nguyên liệu; thiếu món phát `no_dish`; không trừ tồn trước khi nấu |
| N3-03 | Đơn `reserved/assigned/unfulfillable/served`; patience, rời bàn và nhả giữ | Interface khách ↔ bếp với Người 4 | Không bỏ khách trước cơ hội phục vụ ở tick patience về 0; khách rời dọn liên kết đúng |
| N3-04 | Dựng khách fixture và kiểm mâu thuẫn mức luật | `chonoi/scenario.py`, phần khởi tạo quan | Đơn/bếp/tay khớp id, recipe, giá, timer; sai liên kết/giữ quá kho trả mã 2 trước ghi output |
| N3-05 | Khách đa dạng, bàn có tên, hình ăn và uống | `sim/live_quan.py`, `live_world.json`, UI quán | Lõi headless vẫn 1 bàn T1; live có tên bàn, tên khách, món gọi, trạng thái ăn/uống |
| N3-06 | Hỏi PO/giảng viên và ghi câu trả lời | `docs/clarify.md` | Chỗ mơ hồ có nguồn quyết định; không biến giả định thành yêu cầu chính thức |
| N3-07 | Giữ ma trận yêu cầu → bằng chứng → kết quả | `docs/verification/phase-n.md`, `docs/proof/phase-n/` | Dùng output thật ở commit bàn giao; phân biệt smoke qua với đủ mọi luật; không ghi “đạt” nếu chưa kiểm |
| N3-08 | Điều phối kiểm tra liên thông/hồi quy khi nhóm chuẩn bị nộp | Bộ kiểm chứng của repo | Mỗi chủ module tự kiểm; QA tổng hợp, không gánh việc kiểm chứng thay cả nhóm |

### Người 4 — Bếp, phục vụ và kinh tế

| Mã nội bộ | Việc phải làm | File / phạm vi | Bàn giao khi |
|---|---|---|---|
| N4-01 | Ghép vòng `step` quán đúng thứ tự PRD §F | Chủ trì `chonoi/sim/quan.py` | Timer → bếp → di chuyển/interact → ăn xong/rời/đóng ca → sinh khách |
| N4-02 | Bếp idle nhận đơn reserved cũ nhất, hòa theo id bàn; tiêu nguyên liệu giữ | Luật bếp | Chốt giá một lần; `cook_started.items` sắp theo kind; không nấu đơn không có giữ chỗ |
| N4-03 | Nấu/chín/ready_ticks; nhấc món khi tay trống | Luật bếp/tay | Đúng tick chín; P1 `burn_s:null`; payload món là `{order_id,dish_id,base_price}` |
| N4-04 | Chọn tối đa một interact theo khoảng cách, bếp trước bàn, id | Luật tương tác | Đối tượng được chọn không làm được thì bỏ lượt, không tự thử đối tượng thứ hai |
| N4-05 | Phục vụ đúng order_id; chốt boa bằng floor theo patience sau giảm | Luật phục vụ | Phục vụ đúng tick patience=0 hoặc cuối ca vẫn hợp lệ; giữ đủ field event `served` |
| N4-06 | Ăn xong trả tiền/boa, uy tín và điểm | Luật thanh toán | Không thu hai lần; tiền nguyên nghìn đồng; điểm = earned + multiplier × floor(reputation) |
| N4-07 | Đóng ca: khách ăn trả ngay, khách chờ rời không giảm uy tín, dọn món | Luật kết ca | Có `paid`/`customer_left` đúng closing; `quan_end` đủ money/earned/shift_earned/reputation |
| N4-08 | HUD bếp, món trên tay, bàn, tiền, uy tín; mở rộng menu chỉ live | UI, `sim/live_quan.py`, `live_world.json` | Người chơi biết món dành cho bàn nào; hình món và tên khớp; demo stock được ghi rõ |

## 4. Trạng thái repo để nhận việc đúng

| Khu vực | Đang có | Việc còn phải chốt với PRD |
|---|---|---|
| Khung CLI/headless | Có đọc input/scenario, seed, tick, JSONL, file kho | Hạn chế sửa; đọc hiểu trước khi làm lại |
| `GatherSim` | Đã bổ sung luật bơi/oxy/hái/bắt cơ bản | Rà payload event đầy đủ theo §E, mép tick và LIFO; không mặc định là đã đạt PRD chỉ vì có hình |
| `QuanSim` dùng ở headless | Còn TODO luật khách, bếp và tiền | **Ưu tiên cao nhất cho Người 3–4:** đưa đúng luật lõi vào sim headless |
| Live mở rộng | Đã có lặn, ảnh, kho sưu tập; đang bổ sung mưa/truy đuổi/sông rộng/quán đa dạng | Hoàn thiện riêng luồng live; không dùng thay cho việc hoàn thành QuanSim theo contract |
| Art pack | Đã tạo atlas nhân vật, cảnh, cá, đồ dùng, món, khách ăn/uống | Căn frame/điểm neo, nối asset thật, kiểm nguồn ảnh tham chiếu và CREDITS |
| Hồ sơ nhóm | TEAM.md còn trống | Điền tên/handle thật; không tự gán commit hay vai cho người chưa xác nhận |

## 5. Ranh giới file để tránh xung đột

| File / nhóm file | Người giữ tích hợp | Cách hai người làm song song |
|---|---|---|
| `chonoi/sim/gather.py` | Người 1 | Người 1 sửa di chuyển/sinh tồn; Người 2 sửa tài nguyên/helper. Thống nhất hàm trước, báo trước khi sửa cùng `step` |
| `chonoi/sim/quan.py` | Người 4 | Người 3 làm khách/đơn/khởi tạo hoặc helper riêng; Người 4 làm bếp/tay/thu tiền và ghép `step` |
| `chonoi/scenario.py` | Người 3 | Người 4 cung cấp các bất biến order/bếp/tay cần kiểm; thay starter phải ghi lý do |
| `chonoi/web/index.html` | Người 2 ghép UI | Người 1 cung cấp phần river/animation; Người 3 phần khách/bàn; Người 4 bếp/món. Không cùng sửa toàn file một lúc |
| `game.contract.json`, `docs/contracts/` | Người 1 điều phối, cả nhóm biết trước | Không tự đổi schema, kind, công thức hoặc số khóa. Dữ liệu sáng tạo ở JSON riêng |
| `assets/art-pack/` | Người 2 | Giữ tên file ổn định, có mapping ô/frame; thay ảnh đã tích hợp phải báo người dùng ảnh đó |
| Tài liệu chung | Theo vai ở bảng người phụ trách | Ai làm phần nào ghi phần đó; Người 3 tổng hợp bằng chứng, Người 2 chuẩn bị release |

### Giao diện phải chốt ngay

- Giỏ gather là danh sách kind theo thứ tự nhặt; người viết luật không tự sắp lại giỏ.
- Kho bàn giao chuẩn: `{"items":{"bong_sung":2,"ca_loc":1}}`; kho rỗng `{"items":{}}`.
- Quán giữ tồn vật lý và giữ chỗ tách biệt; Người 3 và 4 thống nhất lúc reserve, consume, release và trạng thái đơn.
- UI đọc snapshot và gửi input; không tự quyết bắt được cá, trừ HP, cho tiền hoặc giữ nguyên liệu bằng đồng hồ render.
- Số liệu đọc từ contract/dữ liệu; ngẫu nhiên đi qua Streams; id qua IdAllocator; entity sắp bằng ids.sort_by_id.
- Event theo đúng tên và field PRD §E; không đổi `order_id` thành `customer_id` trong output contract.

## 6. Lịch phối hợp trong 3 giờ

| Mốc | Cả nhóm | Người 1 | Người 2 | Người 3 | Người 4 | Đầu ra |
|---|---|---|---|---|---|---|
| 0:00–0:15 | Kickoff, vào một fork, chọn vai, chốt interface | Chốt sim/UI và người tích hợp | Chốt kho với quán, kiểm asset sẵn | Điền vai/clarify, chia yêu cầu | Chốt order/bếp/tay với Người 3 | TEAM.md, kế hoạch P1, schema kho và mẫu |
| 0:15–0:25 | Làm bốn lát; rà vướng phút 20 | Sinh tồn/giỏ | Xuất kho thật trước phút 25 | Khách/reserve bằng kho mẫu | Bếp/tay bằng đơn mẫu | Kho thật và hai nhóm luật chạy độc lập |
| 0:25–0:45 | Tích hợp liên tục, standup 2–3 phút | Ghép gather | Nối kho và HUD sáng | Ghép khách, thu bằng chứng | Ghép quan và HUD tối | Luồng sáng → kho → tối |
| 0:45–0:55 | Kiểm chứng bàn giao trên main khi chuẩn bị nộp | Rà thứ tự tick | Smoke hai tiến trình/kho | Ma trận và kết quả thật | Rà kết ca, tiền, uy tín | Commit bàn giao và verification P1 |
| 0:55–1:00 | Dự phòng và push tag | Gắn/đẩy phase-1 | Rà README/run | Ghi phần chưa đạt | Hỗ trợ lỗi chặn | **phase-1 trước 1:00** |
| 1:00–1:55 | Đọc Ticket-02 khi mở; re-plan, smoke tích hợp phút 20 | Nhận thay đổi gather/integration | Nhận tài nguyên/UI/release | Phân tích yêu cầu và khách/QA | Nhận thay đổi quán/kinh tế | **phase-2 trước 1:55**, retro nhanh |
| 1:55–2:30 | Đọc Ticket-03; phân tích tác động và ADR trước build | Rà interface/luật sáng | Rà kho/ảnh/tích hợp | Rà scenario/AC và ghi quyết định | Rà bếp/đơn/tiền | ADR + **phase-3 trước 2:30** |
| 2:30–3:00 | Đọc Ticket-04; bench, đóng gói, retro | Chốt bản tích hợp/tag | README, changelog, demo, release | Kết quả thật, retro số liệu | Sửa lỗi chặn, rà kinh tế | **phase-4 + Release v1.0.0 trước 3:00** |

**Không bịa nội dung phase sau.** Khi ticket mở, từng người bổ sung checklist theo AC thật; giữ yêu cầu phase trước và điều chỉnh tải việc.

## 7. Git và làm việc nhóm thật

| Việc | Người chịu trách nhiệm | Cách làm |
|---|---|---|
| Fork đúng tên, repo public, thêm collaborator quyền Write | Trưởng nhóm thực tế (nhóm tự xác nhận) | Dùng fork DoMiXi chung; không đẩy bài vào upstream của lớp |
| TEAM.md và team_size | Cả nhóm; Người 3 tổng hợp | 4 tên/handle thật, module/vai/dự phòng; team_size=4 |
| Nhánh cá nhân | Mỗi người | Gợi ý `feature/gather-life`, `feature/gather-resources`, `feature/quan-orders`, `feature/quan-kitchen`; hoặc giữ nhánh tên thành viên đã có |
| Commit | Mỗi người | Ít nhất 3 commit có nội dung trong cả lab; pair thì Co-authored-by đúng người. Không chia commit rỗng để đủ số |
| Review | 1 ↔ 2 và 3 ↔ 4 | Rà diff, case biên và interface; ghi link commit/PR hoặc review trực tiếp |
| Ghép main | Người 1 với chủ module | Có thể PR hoặc merge trực tiếp theo thỏa thuận; không đẩy game đang hỏng lên main |
| Tag/release | Người 1 gắn tag; Người 2 chuẩn bị release | Tag đúng commit main đã bàn giao; không force-push hoặc viết lại tag đã nộp |

Gợi ý ba commit có ý nghĩa cho từng người:

| Người | Commit 1 | Commit 2 | Commit 3 |
|---|---|---|---|
| 1 | Di chuyển/sinh tồn | Biên tick, giỏ và sự kiện | Tích hợp + animation/live theo phạm vi được giao |
| 2 | Hái và mọc lại | Bắt cá + kho/schema | Asset/HUD/README và bàn giao |
| 3 | Sinh khách + reservation | Patience + kiểm fixture | UI khách + clarify/verification |
| 4 | Bếp + payload món | Phục vụ + thu tiền/kết ca | HUD kinh tế + sửa biên tích hợp |

## 8. Hồ sơ bắt buộc, không bỏ sót

| Hồ sơ | Người tổng hợp | Mỗi người phải đóng góp |
|---|---|---|
| TEAM.md | Người 3 | Tên/handle, module, vai, thỏa thuận và dự phòng |
| docs/contracts/ | Người 1 + Người 2 | Đồng thuận schema kho, snapshot/input và event |
| docs/plan/phase-n.md | Người 1 | Đầu việc, phụ thuộc, rủi ro, tình trạng thật |
| docs/verification/phase-n.md + docs/proof/phase-n/ | Người 3 | Bằng chứng thật phần mình và link commit/tag |
| docs/clarify.md | Người 3 | Câu hỏi, trả lời/giả định, người quyết |
| docs/ai-usage-log.md | Từng người tự điền | Phase, công cụ/model, việc, token/chi phí nếu đo được, AI sai ở đâu |
| docs/retro.md | Người 3 điều phối | Điều tốt/tệ, số liệu thật, hành động cải thiện và lần AI sai |
| docs/members/<handle>.md | Từng người | Phản tư ≤200 từ, commit/review và điều học được |
| AGENTS.md và ít nhất 2 skill/hook/command tự viết | Người 1 + Người 2 | Gợi ý: command smoke kho liên thông; command rà deterministic output. Phải có lệnh thật, không chỉ nêu ý tưởng |
| README.md, CHANGELOG.md, CREDITS.md | Người 2 | Cách chạy, điều khiển, điểm, sáng tạo, nguồn asset/công cụ AI |

## 9. Checklist trước mỗi lần nộp

- [ ] Lõi sáng và tối chạy ở headless, đúng PRD/contract; UI live không thay thế luật headless.
- [ ] Payload event, id, thứ tự, timer, RNG, file kho và đầu vào lỗi khớp tài liệu.
- [ ] Không hard-code số luật ngoài dữ liệu; không đưa phần sáng tạo vào output chuẩn.
- [ ] HUD đọc được; ảnh và animation khớp hành động; nguyên liệu chuyển đúng sang quán.
- [ ] Chạy kiểm chứng ở commit bàn giao khi nhóm chuẩn bị nộp và lưu kết quả thật. **Tài liệu phân công này không khẳng định đã chạy/đạt kiểm chứng.**
- [ ] TEAM.md đủ người, mỗi người có dấu vết đóng góp, AI log và phản tư.
- [ ] Main chạy được, tag đúng hạn, bằng chứng liên kết đúng tag/commit.
- [ ] Phase 4: có Release v1.0.0 và demo trực tiếp/video dưới 5 phút.

## 10. Thỏa thuận xử lý khi chậm

1. Báo ngay trong kênh nhóm khi vướng quá 10 phút; nêu lỗi và phần đã thử.
2. Người hỗ trợ trong bảng nhận một phần cụ thể, không cùng sửa chồng cả file.
3. Rà tiến độ phút 20; tạm dừng sáng tạo nếu lõi hay kho liên thông chưa chạy.
4. Bất đồng: trao đổi 2 phút; PO chốt ý nghĩa yêu cầu, Integrator chốt kỹ thuật sau khi nghe chủ module, ghi quyết định.
5. Hết phase thì ghi trung thực phần đạt/chưa đạt, gắn tag đúng mốc và đi tiếp.
