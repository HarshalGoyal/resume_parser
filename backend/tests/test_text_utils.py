"""Unit tests for the generic text helpers.

These use synthetic inputs unrelated to any particular resume to demonstrate the
logic is layout/convention based and not tuned to one document.
"""

from app.utils.text_utils import (
    collapse_whitespace,
    split_layout_segments,
    looks_like_section_header,
    strip_bullet,
    split_top_level,
    clean_skill_token,
)


def test_collapse_whitespace():
    assert collapse_whitespace("  a\t b   c \n") == "a b c"


def test_split_layout_segments_multispace_and_tab():
    line = "Senior Engineer      Globex Corp\t   Jan 2020 - Present"
    assert split_layout_segments(line) == [
        "Senior Engineer",
        "Globex Corp",
        "Jan 2020 - Present",
    ]


def test_split_layout_segments_single_spaces_stay_one_segment():
    assert split_layout_segments("just one field here") == ["just one field here"]


def test_looks_like_section_header_positive():
    assert looks_like_section_header("EXPERIENCE")
    assert looks_like_section_header("Technical Skills")
    assert looks_like_section_header("WORK HISTORY")


def test_looks_like_section_header_negative():
    # A mixed-case project/role title must not be treated as a section header.
    assert not looks_like_section_header("Plug-and-Play Vision Platform")
    assert not looks_like_section_header(
        "Reduced latency by 40% across the fleet of services"
    )


def test_strip_bullet():
    assert strip_bullet("• Built things") == "Built things"
    assert strip_bullet("- did work") == "did work"
    assert strip_bullet("no bullet") == "no bullet"


def test_split_top_level_respects_parentheses():
    tokens = split_top_level("AWS (Compute, Networking), Docker, Kubernetes")
    assert tokens == ["AWS (Compute, Networking)", "Docker", "Kubernetes"]


def test_split_top_level_keeps_slash_tokens():
    assert split_top_level("CI/CD, TCP/IP") == ["CI/CD", "TCP/IP"]


def test_clean_skill_token():
    assert clean_skill_token("Bash.") == "Bash"
    assert clean_skill_token("AWS (Infrastructure, Networking)") == "AWS"
    assert clean_skill_token("  Python  ") == "Python"
    assert clean_skill_token("...") == ""
