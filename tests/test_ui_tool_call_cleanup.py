"""Static UI tests for quieter tool-call rendering and shared design tokens.

These tests intentionally follow the repo's existing pytest style: read static
source files, isolate the relevant function/rule, and assert implementation
invariants before changing the UI.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).parent.parent
UI_JS = (REPO / "static" / "ui.js").read_text(encoding="utf-8")
CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")


def _function_body(src: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", src)
    assert match, f"{name}() not found"
    brace = src.find("{", match.end())
    assert brace != -1, f"{name}() has no body"
    depth = 1
    i = brace + 1
    in_string = None
    escaped = False
    in_line_comment = False
    in_block_comment = False
    while i < len(src) and depth:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in "'\"`":
            in_string = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    assert depth == 0, f"{name}() body did not close"
    return src[brace + 1:i - 1]


class TestToolCallGroupingStatic:
    def test_render_messages_wraps_settled_tool_calls_in_collapsible_groups(self):
        fn = _function_body(UI_JS, "renderMessages")
        assert "tool-call-group" in fn, (
            "Settled tool calls should render inside a single per-turn "
            ".tool-call-group wrapper, not as loose individual rows."
        )
        assert "data-tool-call-group" in fn, (
            "Tool-call groups need a stable data-tool-call-group attribute for "
            "CSS, accessibility, and future behavioural tests."
        )
        assert re.search(r"cards\.length|toolCalls\.length|group\.length", fn), (
            "The group header should derive its summary/count from the number "
            "of tool calls in the group."
        )

    def test_tool_call_groups_default_collapsed_with_summary_visible(self):
        fn = _function_body(UI_JS, "renderMessages")
        assert "tool-call-group-collapsed" in fn or "collapsed" in fn, (
            "Historical tool-call groups should default to a collapsed state."
        )
        assert "tool-call-group-summary" in fn, (
            "Collapsed groups must expose a visible summary/header row."
        )
        assert "tool-call-group-body" in fn, (
            "Tool-card detail rows should live inside a group body that can be "
            "expanded/collapsed."
        )
        assert "aria-expanded" in fn, (
            "The expand/collapse control must expose aria-expanded."
        )

    def test_live_tool_cards_use_same_grouping_path_as_settled_cards(self):
        live_fn = _function_body(UI_JS, "appendLiveToolCard")
        settled_fn = _function_body(UI_JS, "renderMessages")
        assert "tool-call-group" in live_fn, (
            "Live streaming tool cards should use the same grouped visual "
            "container as settled history cards to avoid layout jumps."
        )
        assert "buildToolCard" in live_fn and "buildToolCard" in settled_fn, (
            "Live and settled tool rendering should share buildToolCard() for "
            "consistent markup."
        )
        assert "data-live-tid" in live_fn, (
            "Live grouping must preserve data-live-tid so tool_start/tool_complete "
            "updates still replace the correct card."
        )


class TestToolCardDesignTokens:
    def test_root_defines_shared_layout_design_tokens(self):
        for token in (
            "--radius-sm",
            "--radius-md",
            "--radius-card",
            "--space-1",
            "--space-2",
            "--space-3",
            "--font-size-xs",
            "--font-size-sm",
            "--surface-subtle",
            "--border-subtle",
        ):
            assert token in CSS, f"Missing design token {token} in style.css"

    def test_tool_card_css_uses_design_tokens_for_chrome(self):
        css_min = re.sub(r"\s+", "", CSS)
        assert ".tool-card{" in css_min, ".tool-card rule missing"
        assert "border-radius:var(--radius-card)" in css_min, (
            ".tool-card border radius should use --radius-card, not hardcoded px."
        )
        assert "background:var(--surface-subtle)" in css_min, (
            ".tool-card background should use --surface-subtle."
        )
        assert "border:1pxsolidvar(--border-subtle)" in css_min, (
            ".tool-card border should use --border-subtle."
        )

    def test_tool_card_header_and_text_use_spacing_and_font_tokens(self):
        css_min = re.sub(r"\s+", "", CSS)
        assert ".tool-card-header{" in css_min, ".tool-card-header rule missing"
        assert "gap:var(--space-2)" in css_min, (
            ".tool-card-header gap should use --space-2."
        )
        assert "padding:var(--space-1)var(--space-3)" in css_min, (
            ".tool-card-header padding should use spacing tokens."
        )
        assert ".tool-card-name{" in css_min and "font-size:var(--font-size-xs)" in css_min, (
            ".tool-card-name should use --font-size-xs."
        )
        assert ".tool-card-preview{" in css_min and "font-size:var(--font-size-xs)" in css_min, (
            ".tool-card-preview should use --font-size-xs."
        )
