from dipsy_dolphin.llm.prompt_builder import build_system_prompt


def test_system_prompt_avoids_literal_stock_example_lines() -> None:
    prompt = build_system_prompt()

    assert "Never copy, quote, or lightly remix literal wording" in prompt
    assert "Absolutely. I am a desktop dolphin, not a spreadsheet" not in prompt
    assert (
        "I tried to organize the ocean once. It turned into absolute current events." not in prompt
    )
    assert "Observe this tiny act of desktop drama." not in prompt
    assert "<one short direct reply>" in prompt
