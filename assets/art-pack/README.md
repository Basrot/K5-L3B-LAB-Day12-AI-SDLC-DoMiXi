# Bộ hình Quán Ăn Chợ Nổi

Ngày tạo: 2026-11-21. Công cụ: built-in image_gen. Khuôn mặt tham chiếu do người dùng cung cấp; thân, trang phục, cảnh và vật dụng được tạo mới.

## Danh mục

- [01-ut-sen](01-ut-sen.png): Bảng nhân vật/vật phẩm/hiệu ứng.
- [02-items-food](02-items-food.png): Bảng nhân vật/vật phẩm/hiệu ứng.
- [03-props-npcs](03-props-npcs.png): Bảng nhân vật/vật phẩm/hiệu ứng.
- [04-river-scene](04-river-scene.png): Cảnh hoặc bố cục giao diện.
- [05-restaurant-scene](05-restaurant-scene.png): Cảnh hoặc bố cục giao diện.
- [06-ui-inventory](06-ui-inventory.png): Cảnh hoặc bố cục giao diện.
- [07-title-day-cycle](07-title-day-cycle.png): Cảnh hoặc bố cục giao diện.
- [08-results-settings](08-results-settings.png): Cảnh hoặc bố cục giao diện.
- [09-animation-fx](09-animation-fx.png): Bảng nhân vật/vật phẩm/hiệu ứng.

## Sử dụng

Đây là bộ hình và concept UI, chưa được nối vào game. Các atlas cần tách ảnh, xử lý nền khi cần và căn điểm neo; tư thế nhân vật không phải animation theo frame. Có sai khác nhỏ về trang phục/nốt ruồi giữa các tư thế. Cảnh quán có nhiều bàn là minh họa, vị trí/số bàn gameplay vẫn phải lấy từ contract. Chữ trong ảnh UI là minh họa; dùng chữ HTML khi triển khai. Công thức, nguyên liệu trang trí và số trên ảnh không thay thế game.contract.json. Không dùng ảnh atlas trực tiếp làm tọa độ gameplay.

Vật phẩm lõi: ca_linh, ca_loc, bong_dien_dien, bong_sung; món ca_loc_nuong_trui, goi_bong_sung, lau_ca_linh_dien_dien. Dừa, chè sen, cơm gói lá, me, ớt, bùa cá vàng là ý tưởng mở rộng, chưa có luật; phải tắt ở headless nếu thêm vào game.

## Prompt gốc

High quality cohesive 2D hand drawn cartoon game art for Vietnamese Mekong floating market game Quan An Cho Noi. Thick expressive dark chocolate outlines, flat clean cel shading, warm coral, turquoise, mustard gold, leafy jade, cream palette. Charming humorous handmade indie game aesthetic, readable small silhouettes, no photorealism, no 3D. Reference image supplied is identity reference for Ut Sen: pale white round face, almond sideways glancing eyes, small sly curved smile, one black beauty mark on lower LEFT cheek as seen by viewer, blonde asymmetric fringe over dark brown bob, huge coral pink head bow. Preserve these features faithfully. Invent body: petite adult chibi 3 heads tall, teal ao ba ba, brown rolled trousers, coral sash, barefoot, woven gathering basket; evening apron variation. 

### 01-ut-sen

Requested transparent background: true

Transparent background character sprite atlas, 4 columns x 3 rows with generous equal margins and isolated complete figures no overlap. Twelve Ut Sen full body poses: front idle, rear idle, left walk, right walk; swim right, swim left, gather flower, catch fish with small net; cook stirring pot in apron, carry plated fish, happy victory holding basket, exhausted sitting. Exactly same face and outfit identity throughout, side view swimming horizontal. No grid lines, no words. Each cell fully contains figure and props. Crisp professional game sprite concept atlas.

### 02-items-food

Requested transparent background: true

Transparent background inventory icon atlas, 6 columns x 4 rows, 24 isolated icons equally spaced no overlap no labels no frames. Row1 ca linh silver small fish, ca loc dark snakehead fish, yellow bong dien dien blossoms, pink bong sung water lily stems, grilled snakehead on banana leaf, water lily stem salad on ceramic plate. Row2 ca linh yellow flower hotpot in clay pot, empty bamboo basket, full bamboo basket, woven fish trap, handheld fish net, terracotta water jar. Row3 fresh coconut drink, lotus seed sweet soup, banana leaf wrapped rice, tamarind jar, red chili bundle, lucky golden fish charm. Row4 oxygen bubble, red heart, gold coin, reputation gold star, blue clock, coral ribbon trophy. All icons large detailed readable and fully inside each equal cell. Authentic Vietnamese foods, visually distinct optional bonus items.

### 03-props-npcs

Requested transparent background: true

Transparent background game object atlas in 4 columns x 4 rows with equal generous empty gutters, no frames no text. Row1 wooden floating dock segment, small wooden sampan boat, water lily harvest patch with pink flower, yellow dien dien harvest shrub. Row2 clay charcoal stove idle, stove with simmering clay pot, stove with ready golden steaming dish, stove with burned smoky pot. Row3 wooden dining table empty, table with plated food, small wooden stool, lantern hung on bamboo pole. Row4 four separate full body adult customer characters: friendly older woman in purple ao ba ba and conical hat, fisherman in indigo shirt, round cheerful merchant in ochre, young traveler in mint clothes. Characters match Ut Sen cartoon universe but distinct faces. Complete isolated silhouettes small top down three quarter game-friendly props.

### 04-river-scene

Requested transparent background: false

Wide landscape 16:9 complete gameplay background illustration only, NO HUD NO TEXT NO CHARACTERS. Side cutaway view of Mekong river for diving gathering level. Upper quarter: sunny sky, distant coconut palms and stilt houses, cheerful floating market boats on horizon, left wooden dock at waterline. Lower three quarters clear turquoise underwater side view continuous traversable open water, sandy muddy riverbed along bottom, reeds along edges, submerged logs and clay pots and gentle light shafts, few tiny ambient bubbles. Keep middle water open for player and fish sprites. Rich parallax feel with darker foreground corners, Vietnamese native flora, crisp clean drawn illustration matching reference cartoon outlines. NO split screen, no inventory, no panels.

### 05-restaurant-scene

Requested transparent background: false

Wide 16:9 playable restaurant background illustration, top down orthographic with slight hand drawn depth, NO people NO HUD NO text. Cozy Mekong floating restaurant on large rectangular bamboo and timber raft at dusk, river visible around edges, warm string lanterns and pink lotus water plants outside, kitchen along upper left with clay charcoal stove, preparation counter and ingredient jars, clear spacious walkway in center and service area, three simple wooden tables with stools to right, small mooring dock at bottom. Strong legibility and inviting warm light, charming thick outline cartoon consistent with supplied face reference but do not put face in background. No perspective vanishing point, no interface.

### 06-ui-inventory

Requested transparent background: false

Wide 16:9 highly polished complete game interface design board on warm cream backdrop, consistent thick outlined hand drawn Mekong floating market game style. Large central inventory panel shaped from woven bamboo and warm timber with coral fabric header, 4 by 3 slots exactly twelve, each separate clearly readable: fish, flowers, salad, net, basket, clay pot, coconut, coin; four empty slots. Right panel recipe card showing three visual ingredient-to-dish combinations: snakehead to grilled fish, two water lily stems to salad, three ca linh plus yellow flower to hotpot. Bottom row distinct reusable UI components: coral rounded primary button, teal secondary button, wooden pause icon button, inventory tab basket, sound button, restart arrow button. Top row HUD components: character portrait faithfully reference identity, oxygen blue bubble bar, three red hearts, coin count icon, reputation five stars, time clock. Minimal text only title 'KHO DO', no fake tiny text, clean gutters, beautiful production-ready interface concept board. No gameplay background.

### 07-title-day-cycle

Requested transparent background: false

Wide 16:9 illustrated game title screen. Beautiful sunrise Mekong floating market, colorful boats carrying fruits and flowers, coconut palms, floating wooden restaurant with warm lanterns at right, gentle teal river. Foreground left Ut Sen full body retaining reference face bow hair beauty mark, standing on sampan holding net and basket, excited mischievous smile. Leave central upper sky readable title in large charming cream letters 'CHO NOI' and three lower center stacked bamboo buttons labeled 'CHOI', 'KHO DO', 'CAI DAT'. Thoughtful finished hand drawn indie game title composition matching supplied reference, lovely narrative detail, no other lettering.

### 08-results-settings

Requested transparent background: false

Wide 16:9 game UI screen layout board with three distinct finished panels beside each other on cream background. LEFT pause/settings panel in bamboo frame with coral ribbon header 'TAM DUNG', large play triangle button, music slider with note icon, speaker slider, home icon. CENTER end-of-day results panel 'HET CA' with Ut Sen reference identity delighted portrait, coin trophy and five reputation stars, three large stat rows with fish icon, plated dish icon, coin icon and simple numeric values 12, 8, 540, bottom teal restart button with arrow. RIGHT recipe book panel 'THUC DON' with hand drawn appetizing grilled snakehead on banana leaf, pink water lily stem salad, steaming ca linh flower hotpot, each with ingredient icons beneath. Large legible visual components no tiny nonsense text. Full screen concepts, coherent warm bamboo coral teal game UI.

### 09-animation-fx

Requested transparent background: true

Transparent background 5 column x 4 row game visual effects and aquatic sprite atlas, equal cells generous gutters, no text no lines. Row1 five consecutive frames of small turquoise water splash emerging and dispersing left to right. Row2 five frames of golden star sparkle burst and fading. Row3 silver ca linh school left, silver ca linh school right, single dark ca loc left, single dark ca loc right, pink water lily bloom. Row4 small bubble cluster, white cooking steam swirl, dark burned smoke puff, gold coin spinning face, heart healing burst. Clean isolated graphic assets, bold outline, readable game vfx, consistent illustrated style.

