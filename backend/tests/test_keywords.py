"""Unit tests for keyword extraction."""

import pytest

from app.core.analytics.keywords import extract_keywords


class TestExtractKeywords:
    def test_returns_top_keywords_sorted_by_count(self):
        comments = [
            "giá bao nhiêu",
            "giá sản phẩm này",
            "giao hàng nhanh không",
            "giá rẻ quá",
            "hàng đẹp",
        ]
        result = extract_keywords(comments, top_n=3)
        assert len(result) == 3
        assert result[0]["word"] == "giá"
        assert result[0]["count"] == 3
        for entry in result:
            assert "word" in entry
            assert "count" in entry

    def test_filters_vietnamese_stopwords(self):
        comments = [
            "của tôi là cái này",
            "được không vậy",
            "sản phẩm đẹp lắm",
        ]
        result = extract_keywords(comments, top_n=20)
        words = [e["word"] for e in result]
        for sw in ["của", "là", "này", "được", "không", "vậy"]:
            assert sw not in words

    def test_empty_input_returns_empty_list(self):
        assert extract_keywords([], top_n=10) == []

    def test_filters_single_char_words(self):
        comments = ["a b c sản phẩm"]
        result = extract_keywords(comments, top_n=10)
        words = [e["word"] for e in result]
        assert "a" not in words
        assert "b" not in words
        assert "c" not in words

    def test_case_insensitive(self):
        comments = ["Giá bao nhiêu", "giá rẻ", "GIÁ tốt"]
        result = extract_keywords(comments, top_n=1)
        assert result[0]["word"] == "giá"
        assert result[0]["count"] == 3

    def test_top_n_limits_results(self):
        comments = ["từ1 từ2 từ3 từ4 từ5 từ6 từ7 từ8 từ9 từ10"]
        result = extract_keywords(comments, top_n=5)
        assert len(result) <= 5

    def test_handles_punctuation(self):
        comments = ["giá? giá! giá..."]
        result = extract_keywords(comments, top_n=1)
        assert result[0]["word"] == "giá"
        assert result[0]["count"] == 3
