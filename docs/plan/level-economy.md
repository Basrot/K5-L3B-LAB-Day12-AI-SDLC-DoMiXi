# Kinh tế 5 màn cho bản chơi trực tiếp

Phần này chuẩn bị để nối hai ca sáng/tối sau khi đồng đội hoàn thiện. Không sửa `game.contract.json`, không đổi cách chấm headless. Giá 6 món, tiền boa, Bình khí và Máu dưới đây **đã nằm trong contract v1.1**; các thưởng màn và đồ lặn còn lại nằm trong `chonoi/progression.json`. Mọi số vẫn có thể cân bằng bằng cách sửa dữ liệu, không sửa công thức.

## Khách trả tiền

| Món | Giá cơ bản (xu) | Boa tối đa nếu phục vụ khi khách còn ít nhất nửa kiên nhẫn |
| --- | ---: | ---: |
| Cá lóc nướng trui | 60 | 12 |
| Gỏi bông súng | 40 | 8 |
| Lẩu cá linh điên điển | 120 | 24 |
| Canh chua cá lóc | 90 | 18 |
| Cá kèo nướng | 70 | 14 |
| Lẩu mắm | 200 | 40 |

Tiền từ một khách = giá món + boa. Boa bằng 20% giá món, làm tròn xuống, khi đủ điều kiện kiên nhẫn; nếu khách bỏ đi thì không thu tiền và uy tín giảm 0,5. Khách có boa tăng uy tín 0,2. Đây là luật sẵn có ở `game.contract.json` và `chonoi/sim/quan.py`.

## Kết màn, sao và thưởng

`earned` từ ca quán đã chứa giá món và boa. `paid_by_dish` đếm sự kiện `paid` theo từng món; số suất tính cho mục tiêu mỗi món không vượt số suất trong `day_plan`. `reputation` là uy tín cuối ca. Mục tiêu doanh thu = tổng giá cơ bản của các suất trong `day_plan`. Sao xét đồng thời cả ba điều kiện:

| Sao | Tỷ lệ khách đã trả / suất kế hoạch | Doanh thu / mục tiêu | Uy tín cuối ca |
| --- | ---: | ---: | ---: |
| 1 | ≥ 40% | ≥ 35% | ≥ 2,0 |
| 2 | ≥ 70% | ≥ 65% | ≥ 3,0 |
| 3 | 100% | ≥ 90% | ≥ 3,5 |

Thưởng thêm = thưởng qua màn + (số sao × thưởng mỗi sao), chỉ khi đạt ít nhất 1 sao. Xu thay đổi trong màn = tiền khách trả + xu từ sự kiện (thưởng công an, mất do bảo kê) + thưởng thêm. Ví sau màn = ví sau ca quán + thưởng thêm; **không cộng tiền khách trả lần hai**. Xu sự kiện = ví sau ca quán − ví trước ca quán − tiền khách trả.

| Màn | Suất kế hoạch | Mục tiêu doanh thu | Thưởng qua màn | Thưởng mỗi sao | Tổng xu ví dụ khi phục vụ đủ và mọi khách đều boa |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 6 | 300 | 50 | 20 | 470 |
| 2 | 4 | 360 | 70 | 30 | 592 |
| 3 | 6 | 400 | 90 | 40 | 690 |
| 4 | 4 | 360 | 120 | 60 | 732 |
| 5 | 3 | 380 | 160 | 80 | 856 |

Áp lực khách tăng theo màn trong bản live: khoảng cách sinh khách lần lượt là 22, 19, 16, 13, 10 giây; số khách có thể gọi thêm sau đơn kế hoạch là 0, 2, 4, 6, 8. Khách chỉ được gọi món khi kho còn đủ nguyên liệu. Mục tiêu sao vẫn dựa trên các suất `day_plan` của contract.

Các tổng trên là **ví dụ tốt nhất nếu phục vụ đúng các suất kế hoạch và mọi khách đều boa**, không phải số xu cố định; kết quả thực tế phụ thuộc khách phục vụ, thời gian và uy tín. Mở màn kế tiếp khi màn trước đạt ít nhất 1 sao. Có thể chơi lại để kiếm thêm sao và xu, nhưng chỉ trao thưởng kết màn một lần cho mỗi lượt kết thúc; lưu kết quả trước khi hiện màn tổng kết để tránh nhấn nhận nhiều lần.

## Giá nâng cấp

Mỗi món mặc định ở cấp hiển thị 1. Nút chỉ mua **một bậc kế tiếp**; sau khi mua cấp 2, cấp 3 mới sáng. Giá sau đây là giá cho riêng từng lần mua, không phải giá cộng dồn.

| Món | Cấp 1 mặc định | Mua cấp 2 | Mua cấp 3 |
| --- | --- | --- | --- |
| Bình khí | 30 giây oxy | 200 xu → 45 giây | 400 xu → 60 giây |
| Mũ lặn | sâu 20 | 250 xu → sâu 25 | 500 xu → sâu 30 |
| Chân vịt | tốc độ ×1,00 | 150 xu → ×1,15 | 300 xu → ×1,30 |
| Đèn lặn | tầm soi 3 | 180 xu → 5 | 360 xu → 7 |
| Túi thuốc | 3 HP | 250 xu → 4 HP | 500 xu → 5 HP |

`Bình khí` và `Túi thuốc` khớp giá/chỉ số contract. Ba món còn lại dành cho phần chơi trực tiếp; đội lặn sẽ nối tác dụng của chúng vào live. Ảnh giao diện shop dùng các ô giá trống để hiển thị số từ dữ liệu. Cấp hiển thị 1/2/3 tương ứng cấp dữ liệu 0/1/2.

## Điểm nối với code hai ca

1. Khi khách phát sự kiện `paid`, ca quán đã cộng tiền vào `money` và `earned`; đếm `paid` theo `dish_id` trong lượt.
2. Lúc ca quán đóng, gọi `settle_day` từ `chonoi/progression.py` với ngày, `paid_by_dish`, `earned`, `reputation`, `money_after_shift`, `wallet_before_shift`. Lưu kết quả và hiển thị trên ảnh tổng kết.
3. Nút cửa hàng đọc `upgrades` trong dữ liệu. Gọi `buy_upgrade` với ví và cấp hiện tại; ghi ví/cấp mới vào tiến độ người chơi. Chỉ áp chỉ số đã mua vào ca lặn kế tiếp.
4. Bản đồ đọc sao cao nhất từng màn để mở khóa. Giữ thưởng và đồ lặn này ngoài headless cho tới khi nhóm thống nhất thay đổi contract.
