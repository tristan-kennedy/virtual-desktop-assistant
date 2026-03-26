from __future__ import annotations

from dataclasses import dataclass


SCREEN_MARGIN_PX = 8
BUBBLE_GAP_PX = 24
TAIL_EDGE_MARGIN_PX = 24


@dataclass(frozen=True)
class BubblePlacement:
    bubble_x: int
    bubble_y: int
    tail_tip_x: int


def compute_bubble_placement(
    *,
    anchor_global_x: int,
    anchor_global_y: int,
    bubble_width: int,
    bubble_height: int,
    screen_left: int,
    screen_top: int,
    screen_right: int,
    screen_bottom: int,
    preferred_center_global_x: int | None = None,
) -> BubblePlacement:
    min_x = screen_left + SCREEN_MARGIN_PX
    max_x = max(min_x, screen_right - bubble_width - SCREEN_MARGIN_PX)
    center_global_x = (
        preferred_center_global_x if preferred_center_global_x is not None else anchor_global_x
    )
    ideal_x = center_global_x - (bubble_width // 2)
    bubble_x = max(min_x, min(max_x, ideal_x))

    preferred_y = anchor_global_y - bubble_height - BUBBLE_GAP_PX
    max_y = max(screen_top + SCREEN_MARGIN_PX, screen_bottom - bubble_height - SCREEN_MARGIN_PX)
    bubble_y = max(screen_top + SCREEN_MARGIN_PX, min(max_y, preferred_y))

    tail_tip_x = max(
        TAIL_EDGE_MARGIN_PX,
        min(bubble_width - TAIL_EDGE_MARGIN_PX, anchor_global_x - bubble_x),
    )
    return BubblePlacement(bubble_x=bubble_x, bubble_y=bubble_y, tail_tip_x=tail_tip_x)
