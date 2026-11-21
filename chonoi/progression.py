"""Kinh tế nhiều màn cho bản chơi trực tiếp; headless không gọi module này.

QuanSim đã cộng giá món và tiền boa vào ``money``/``earned`` khi phát ``paid``.
Chỉ cộng thưởng cuối màn một lần, sau khi ca quán kết thúc.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_progression(path: str | Path | None = None) -> dict:
    source = Path(path) if path is not None else Path(__file__).with_name("progression.json")
    with source.open(encoding="utf-8") as handle:
        return json.load(handle)


def settle_day(
    contract: dict,
    progression: dict,
    day: int,
    *,
    paid_by_dish: dict[str, int],
    earned: int,
    reputation: float,
    money_after_shift: int,
) -> dict:
    """Tính sao và thưởng; ``earned`` đã gồm giá món + boa.

    ``money_after_shift`` là ví hiện tại từ QuanSim, đã gồm ``earned``.
    Lời gọi này chỉ dành cho lúc đóng ca, và kết quả cần lưu để tránh nhận thưởng lặp.
    """
    plans = contract["tuning"]["day_plan"]
    plan = next((item for item in plans if item["day"] == day), None)
    if plan is None:
        raise ValueError(f"Không có màn {day} trong day_plan")
    day_reward = progression["days"][str(day)]
    menu = contract["tuning"]["menu"]
    planned_count = sum(plan["dishes"].values())
    paid_count = sum(paid_by_dish.values())
    fulfilled_count = sum(min(paid_by_dish.get(dish, 0), quantity)
                          for dish, quantity in plan["dishes"].items())
    revenue_goal = sum(menu[dish]["price"] * quantity for dish, quantity in plan["dishes"].items())
    if any(not isinstance(qty, int) or qty < 0 for qty in paid_by_dish.values()) or earned < 0 or money_after_shift < 0:
        raise ValueError("Số khách và xu phải không âm")
    paid_ratio = fulfilled_count / planned_count
    revenue_ratio = earned / revenue_goal
    stars = 0
    for gate in sorted(progression["stars"], key=lambda item: item["count"]):
        if (paid_ratio >= gate["min_paid_ratio"]
                and revenue_ratio >= gate["min_revenue_ratio"]
                and reputation >= gate["min_reputation"]):
            stars = gate["count"]
    bonus = (day_reward["clear_bonus"] + stars * day_reward["bonus_per_star"]) if stars else 0
    return {
        "day": day,
        "planned_count": planned_count,
        "paid_count": paid_count,
        "fulfilled_count": fulfilled_count,
        "revenue_goal": revenue_goal,
        "earned_from_customers": earned,
        "reputation": reputation,
        "stars": stars,
        "bonus": bonus,
        "total_earned_this_day": earned + bonus,
        "money_after_reward": money_after_shift + bonus,
    }


def buy_upgrade(progression: dict, item: str, current_level: int, money: int) -> dict:
    """Mua đúng một cấp kế tiếp; cấp 0 là đồ mặc định, tương ứng thẻ Cấp 1 trên ảnh."""
    levels = progression["upgrades"][item]["levels"]
    if not 0 <= current_level < len(levels):
        raise ValueError("Cấp nâng không hợp lệ")
    if current_level == len(levels) - 1:
        raise ValueError("Đã đạt cấp tối đa")
    next_level = levels[current_level + 1]
    price = next_level["price"]
    if money < price:
        raise ValueError("Không đủ xu")
    return {
        "item": item,
        "level": next_level["level"],
        "display_level": next_level["level"] + 1,
        "price_paid": price,
        "money_left": money - price,
        "stats": {key: value for key, value in next_level.items() if key not in {"level", "price"}},
    }
