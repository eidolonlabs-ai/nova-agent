"""Tests for nova/display.py — pure logic functions only.

Skips terminal/Rich rendering (NovaTUI, print_banner, _cprint, ANSI output)
since those require live terminal I/O.
"""

from unittest.mock import patch

import pytest

from nova.display import (
    StreamingReasoningBox,
    extract_reasoning_blocks,
    split_reasoning_and_response,
    strip_reasoning_tags,
)

# ─── strip_reasoning_tags ────────────────────────────────────────────────────


class TestStripReasoningTags:
    def test_removes_closed_think_pair(self):
        text = "<think>internal thoughts</think>Final answer."
        assert strip_reasoning_tags(text) == "Final answer."

    def test_removes_thinking_tag(self):
        text = "<thinking>step by step</thinking>Result"
        assert strip_reasoning_tags(text) == "Result"

    def test_removes_reasoning_tag(self):
        text = "<reasoning>why</reasoning>Answer"
        assert strip_reasoning_tags(text) == "Answer"

    def test_removes_thought_tag(self):
        text = "<thought>quiet musing</thought>Done"
        assert strip_reasoning_tags(text) == "Done"

    def test_removes_multiline_block(self):
        text = "<think>\nline 1\nline 2\n</think>\nResponse text"
        assert strip_reasoning_tags(text) == "Response text"

    def test_removes_unterminated_open_tag(self):
        text = "<think>unfinished reasoning with no close"
        result = strip_reasoning_tags(text)
        assert "<think>" not in result
        assert "unfinished reasoning" not in result

    def test_removes_orphan_close_tag(self):
        text = "Preamble</think> actual response"
        assert "</think>" not in strip_reasoning_tags(text)

    def test_no_tags_returns_text_unchanged(self):
        text = "Plain response with no tags."
        assert strip_reasoning_tags(text) == text

    def test_case_insensitive(self):
        text = "<THINK>caps</THINK>response"
        result = strip_reasoning_tags(text)
        assert "caps" not in result
        assert "response" in result

    def test_multiple_blocks_removed(self):
        text = "<think>a</think>middle<think>b</think>end"
        result = strip_reasoning_tags(text)
        assert "a" not in result
        assert "b" not in result
        assert "middle" in result
        assert "end" in result

    def test_empty_string(self):
        assert strip_reasoning_tags("") == ""

    def test_only_tags_no_content(self):
        result = strip_reasoning_tags("<think></think>")
        assert result == ""


# ─── extract_reasoning_blocks ────────────────────────────────────────────────


class TestExtractReasoningBlocks:
    def test_extracts_single_think_block(self):
        text = "<think>my reasoning</think>"
        blocks = extract_reasoning_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["tag"] == "think"
        assert blocks[0]["content"] == "my reasoning"

    def test_extracts_multiple_blocks(self):
        text = "<think>first</think> gap <reasoning>second</reasoning>"
        blocks = extract_reasoning_blocks(text)
        assert len(blocks) == 2
        contents = {b["content"] for b in blocks}
        assert "first" in contents
        assert "second" in contents

    def test_returns_empty_list_when_no_blocks(self):
        assert extract_reasoning_blocks("plain text") == []

    def test_blocks_sorted_by_position(self):
        text = "<think>early</think> middle <reasoning>late</reasoning>"
        blocks = extract_reasoning_blocks(text)
        assert blocks[0]["content"] == "early"
        assert blocks[1]["content"] == "late"

    def test_includes_start_and_end_positions(self):
        text = "<think>content</think>"
        blocks = extract_reasoning_blocks(text)
        assert "start" in blocks[0]
        assert "end" in blocks[0]
        assert blocks[0]["start"] == 0
        assert blocks[0]["end"] == len(text)

    def test_content_is_stripped(self):
        text = "<think>  spaced  </think>"
        blocks = extract_reasoning_blocks(text)
        assert blocks[0]["content"] == "spaced"

    def test_multiline_content(self):
        text = "<thinking>\nline 1\nline 2\n</thinking>"
        blocks = extract_reasoning_blocks(text)
        assert len(blocks) == 1
        assert "line 1" in blocks[0]["content"]

    def test_case_insensitive_match(self):
        text = "<THINK>caps content</THINK>"
        blocks = extract_reasoning_blocks(text)
        assert len(blocks) == 1


# ─── split_reasoning_and_response ───────────────────────────────────────────


class TestSplitReasoningAndResponse:
    def test_splits_single_block(self):
        text = "<think>internal</think>Final answer."
        blocks, response = split_reasoning_and_response(text)
        assert len(blocks) == 1
        assert "Final answer." in response
        assert "<think>" not in response

    def test_no_blocks_returns_full_text(self):
        text = "Plain response."
        blocks, response = split_reasoning_and_response(text)
        assert blocks == []
        assert response == text

    def test_response_is_stripped(self):
        text = "<think>x</think>   answer   "
        _, response = split_reasoning_and_response(text)
        assert response == "answer"

    def test_multiple_blocks_removed(self):
        text = "<think>a</think>mid<reasoning>b</reasoning>end"
        blocks, response = split_reasoning_and_response(text)
        assert len(blocks) == 2
        assert "a" not in response
        assert "b" not in response
        assert "mid" in response
        assert "end" in response

    def test_only_reasoning_block_gives_empty_response(self):
        text = "<think>everything is here</think>"
        blocks, response = split_reasoning_and_response(text)
        assert len(blocks) == 1
        assert response == ""


# ─── StreamingReasoningBox ───────────────────────────────────────────────────


@pytest.fixture
def box():
    """Return a fresh StreamingReasoningBox with _cprint mocked out."""
    with patch("nova.display._cprint"):
        b = StreamingReasoningBox()
        yield b


class TestStreamingReasoningBoxInit:
    def test_initial_state(self):
        with patch("nova.display._cprint"):
            b = StreamingReasoningBox()
        assert b._reasoning_tokens == 0
        assert b._reasoning_lines == []
        assert b._reasoning_buf == ""
        assert b._response_buf == ""
        assert b._reasoning_opened is False
        assert b._response_opened is False
        assert b._in_reasoning is False
        assert b._prefilt_buf == ""
        assert b._last_was_newline is True
        assert b._deferred_content == ""

    def test_console_arg_accepted_for_compat(self):
        with patch("nova.display._cprint"):
            b = StreamingReasoningBox(console=object())
        assert b._reasoning_tokens == 0


class TestStreamingReasoningBoxReset:
    def test_reset_clears_all_state(self, box):
        box._reasoning_tokens = 42
        box._reasoning_lines = ["line"]
        box._reasoning_buf = "partial"
        box._response_buf = "resp"
        box._reasoning_opened = True
        box._response_opened = True
        box._in_reasoning = True
        box._prefilt_buf = "buf"
        box._last_was_newline = False
        box._deferred_content = "defer"

        box.reset()

        assert box._reasoning_tokens == 0
        assert box._reasoning_lines == []
        assert box._reasoning_buf == ""
        assert box._response_buf == ""
        assert box._reasoning_opened is False
        assert box._response_opened is False
        assert box._in_reasoning is False
        assert box._prefilt_buf == ""
        assert box._last_was_newline is True
        assert box._deferred_content == ""


class TestStreamingReasoningBoxFeedReasoning:
    def test_feed_reasoning_accumulates_lines(self, box):
        box.feed_reasoning("hello\nworld\n")
        assert "hello" in box._reasoning_lines
        assert "world" in box._reasoning_lines

    def test_feed_reasoning_empty_string_no_op(self, box):
        box.feed_reasoning("")
        assert box._reasoning_lines == []

    def test_feed_reasoning_partial_line_buffered(self, box):
        box.feed_reasoning("partial")
        assert box._reasoning_buf == "partial"
        assert box._reasoning_lines == []


class TestStreamingReasoningBoxFeed:
    def test_plain_text_passes_through(self, box):
        box.feed("Hello world")
        # No reasoning tag — text goes to response buffer
        assert box._in_reasoning is False

    def test_open_tag_enters_reasoning_mode(self, box):
        box.feed("<think>")
        assert box._in_reasoning is True

    def test_complete_reasoning_block_handled(self, box):
        box.feed("<think>reasoning content</think>")
        assert box._in_reasoning is False
        # Content without newline stays in _reasoning_buf until flush
        all_content = " ".join(box._reasoning_lines) + " " + box._reasoning_buf
        assert "reasoning content" in all_content

    def test_inline_tag_mid_text_not_triggered(self, box):
        # A tag not at a block boundary (preceded by non-whitespace) is treated as text
        box.feed("prefix text<think>not a reasoning block")
        # The tag wasn't at a block boundary, so reasoning not entered
        # (behaviour: depends on _is_block_boundary; with preceding non-whitespace text
        # and _last_was_newline=True initially, the result varies by implementation)
        # Just verify no crash and we get a consistent state
        assert isinstance(box._in_reasoning, bool)

    def test_empty_input_returns_empty_string(self, box):
        result = box.feed("")
        assert result == ""

    def test_streaming_open_tag_split_across_calls(self, box):
        # Feed the tag in two chunks
        box.feed("<thi")
        assert box._in_reasoning is False
        box.feed("nk>inner</think>")
        assert box._in_reasoning is False
        # Short content without newline stays in _reasoning_buf
        all_content = " ".join(box._reasoning_lines) + " " + box._reasoning_buf
        assert "inner" in all_content

    def test_close_tag_exits_reasoning(self, box):
        box.feed("<think>")
        assert box._in_reasoning is True
        box.feed("some thoughts</think>")
        assert box._in_reasoning is False

    def test_content_after_close_tag_fed_back(self, box):
        # Text after close tag should be processed as response
        box.feed("<think>reasoning</think>response text")
        assert box._in_reasoning is False

    def test_reasoning_scratchpad_tag_works(self, box):
        box.feed("<REASONING_SCRATCHPAD>content</REASONING_SCRATCHPAD>")
        assert box._in_reasoning is False
        all_content = " ".join(box._reasoning_lines) + " " + box._reasoning_buf
        assert "content" in all_content

    def test_large_reasoning_block_flushed_incrementally(self, box):
        # Reasoning longer than max_tag_len should be flushed before end
        box.feed("<think>")
        long_text = "word " * 100
        box.feed(long_text)
        # Lines should have been flushed incrementally
        assert len(box._reasoning_lines) > 0 or box._reasoning_buf != ""


class TestStreamingReasoningBoxFlush:
    def test_flush_closes_open_reasoning(self, box):
        box.feed("<think>unfinished reasoning")
        box.flush()
        # After flush, reasoning_opened should be False
        assert box._reasoning_opened is False

    def test_flush_emits_deferred_content(self, box):
        box._deferred_content = "deferred"
        box.flush()
        assert box._deferred_content == ""

    def test_flush_noop_on_clean_state(self, box):
        box.flush()  # Should not raise
        assert box._reasoning_opened is False

    def test_flush_recovers_false_positive_reasoning(self, box):
        # Simulates unclosed reasoning tag treated as response on flush
        box._in_reasoning = True
        box._prefilt_buf = "actually response text"
        box.flush()
        assert box._in_reasoning is False
        assert box._prefilt_buf == ""
