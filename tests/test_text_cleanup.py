"""Tests for headline cleanup utility."""

import pytest
from backend.utils.text_cleanup import clean_headline


def test_all_caps_to_title_case():
    """ALL CAPS headline with >40% caps words should be title-cased."""
    result = clean_headline("BREAKING NEWS ABOUT TECHNOLOGY")
    assert result == "Breaking News About Technology"


def test_partial_caps_converted():
    """Headline with more than 40% all-caps words should be title-cased."""
    result = clean_headline("THIS IS A test WITH CAPS")
    # 4 out of 6 words are caps (67%) -> should title-case
    assert result[0].isupper()
    assert "THIS" not in result


def test_normal_title_unchanged():
    """Normal mixed-case headline should not be modified."""
    assert clean_headline("Normal headline here") == "Normal headline here"


def test_collapse_excessive_exclamation():
    """Multiple exclamation marks should be collapsed to one."""
    assert clean_headline("Amazing news!!!") == "Amazing news!"


def test_collapse_excessive_questions():
    """Multiple question marks should be collapsed to one."""
    assert clean_headline("Really???") == "Really?"


def test_collapse_excessive_dots():
    """Four or more dots should be collapsed to ellipsis."""
    assert clean_headline("What happened.....") == "What happened..."


def test_remove_breaking_prefix():
    """BREAKING: prefix should be stripped from the headline."""
    assert clean_headline("BREAKING: Major event") == "Major event"


def test_remove_watch_prefix():
    """WATCH: prefix should be stripped from the headline."""
    assert clean_headline("WATCH: Video goes viral") == "Video goes viral"


def test_remove_just_in_prefix():
    """JUST IN: prefix should be stripped from the headline."""
    assert clean_headline("JUST IN: New development") == "New development"


def test_remove_exclusive_prefix():
    """EXCLUSIVE: prefix should be stripped from the headline."""
    assert clean_headline("EXCLUSIVE: Secret revealed") == "Secret revealed"


def test_remove_developing_prefix():
    """DEVELOPING: prefix should be stripped from the headline."""
    assert clean_headline("DEVELOPING: Story unfolds") == "Story unfolds"


def test_remove_trailing_site_name_pipe():
    """Trailing | Site Name should be removed."""
    result = clean_headline("Article title | The New York Times")
    assert "New York Times" not in result
    assert result.strip() == "Article title"


def test_remove_trailing_site_name_dash():
    """Trailing - Site Name should be removed."""
    result = clean_headline("Article title - CNN")
    assert "CNN" not in result
    assert result.strip() == "Article title"


def test_empty_title():
    """Empty string should return empty string."""
    assert clean_headline("") == ""


def test_none_title():
    """None should return None."""
    assert clean_headline(None) is None


def test_combined_cleanup():
    """Multiple cleanup rules should all apply together."""
    result = clean_headline("BREAKING: THIS IS BIG NEWS!!! | Fox News")
    assert "BREAKING" not in result
    assert "Fox News" not in result
    assert "!!!" not in result
    # Should have exactly one ! if any
    assert result.count("!") <= 1
