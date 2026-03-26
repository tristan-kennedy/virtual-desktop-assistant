from dipsy_dolphin.ui.bubble_layout import compute_bubble_placement


def test_bubble_layout_centers_above_anchor_when_space_allows() -> None:
    placement = compute_bubble_placement(
        anchor_global_x=300,
        anchor_global_y=400,
        bubble_width=200,
        bubble_height=120,
        screen_left=0,
        screen_top=0,
        screen_right=800,
        screen_bottom=600,
    )

    assert placement.bubble_x == 200
    assert placement.bubble_y == 256
    assert placement.tail_tip_x == 100


def test_bubble_layout_clamps_left_but_tail_still_points_to_anchor() -> None:
    placement = compute_bubble_placement(
        anchor_global_x=40,
        anchor_global_y=300,
        bubble_width=240,
        bubble_height=100,
        screen_left=0,
        screen_top=0,
        screen_right=500,
        screen_bottom=400,
    )

    assert placement.bubble_x == 8
    assert placement.tail_tip_x == 32


def test_bubble_layout_clamps_right_but_tail_still_points_to_anchor() -> None:
    placement = compute_bubble_placement(
        anchor_global_x=470,
        anchor_global_y=300,
        bubble_width=240,
        bubble_height=100,
        screen_left=0,
        screen_top=0,
        screen_right=500,
        screen_bottom=400,
    )

    assert placement.bubble_x == 252
    assert placement.tail_tip_x == 216


def test_bubble_layout_centers_on_character_even_when_tail_target_is_offset() -> None:
    placement = compute_bubble_placement(
        anchor_global_x=332,
        anchor_global_y=280,
        bubble_width=220,
        bubble_height=96,
        screen_left=0,
        screen_top=0,
        screen_right=900,
        screen_bottom=700,
        preferred_center_global_x=280,
    )

    assert placement.bubble_x == 170
    assert placement.bubble_y == 160
    assert placement.tail_tip_x == 162
