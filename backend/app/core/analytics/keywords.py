"""Keyword extraction from comment lists.

Uses regex tokenization + Vietnamese stopword filtering.
No external NLP dependencies.
"""

import re
from collections import Counter

# ~120 common Vietnamese stopwords (function words, particles, TikTok filler)
VIETNAMESE_STOPWORDS: frozenset[str] = frozenset(
    {
        # Pronouns
        "tôi",
        "tao",
        "mình",
        "chúng",
        "ta",
        "bạn",
        "cậu",
        "anh",
        "chị",
        "em",
        "ông",
        "bà",
        "nó",
        "họ",
        "ai",
        "gì",
        # Conjunctions & prepositions
        "và",
        "hoặc",
        "hay",
        "nhưng",
        "mà",
        "với",
        "của",
        "cho",
        "từ",
        "trong",
        "trên",
        "dưới",
        "ngoài",
        "về",
        "theo",
        "bằng",
        "để",
        "tới",
        "đến",
        # Particles & modifiers
        "là",
        "có",
        "không",
        "đã",
        "đang",
        "sẽ",
        "được",
        "bị",
        "phải",
        "cần",
        "nên",
        "thì",
        "cũng",
        "vẫn",
        "còn",
        "rất",
        "lắm",
        "quá",
        "hơn",
        "nhất",
        "này",
        "đó",
        "kia",
        "ấy",
        "nào",
        "mỗi",
        "các",
        "những",
        "một",
        "hai",
        "ba",
        "tất",
        "cả",
        "mọi",
        # Question words
        "sao",
        "đâu",
        # TikTok filler words
        "ạ",
        "nha",
        "nhé",
        "ơi",
        "vậy",
        "nhỉ",
        "hen",
        "nè",
        "luôn",
        "nghen",
        "dạ",
        "vâng",
        "ừ",
        "ờ",
        "à",
        "ồ",
        # Common verbs that are too generic
        "làm",
        "biết",
        "nói",
        "xem",
        "lấy",
        "đi",
        "ra",
        "vào",
        "lên",
        "xuống",
        # Other function words
        "thế",
        "rồi",
        "đây",
        "khi",
        "nếu",
        "vì",
        "do",
        "tại",
        "lại",
        "chỉ",
        "mới",
        "ngay",
        "thôi",
        "hết",
        "xong",
        # Additional modifiers & adverbs
        "thật",
        "cứ",
        "chưa",
        "đấy",
        "nhau",
        "mấy",
        "dù",
        "hãy",
        "nữa",
        "đều",
        "riêng",
        "giống",
    }
)

_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ỹ0-9]+", re.UNICODE)


def extract_keywords(comments: list[str], top_n: int = 20) -> list[dict[str, int | str]]:
    """Extract top keywords from a list of comment strings.

    Process:
    1. Lowercase + normalize
    2. Tokenize: regex split on non-word characters
    3. Filter: remove stopwords, words < 2 chars
    4. Count frequency
    5. Return top_n as [{"word": "giá", "count": 45}, ...]
    """
    if not comments:
        return []

    counter: Counter[str] = Counter()

    for comment in comments:
        tokens = _TOKEN_RE.findall(comment.lower())
        for token in tokens:
            if len(token) >= 2 and token not in VIETNAMESE_STOPWORDS:
                counter[token] += 1

    return [{"word": word, "count": count} for word, count in counter.most_common(top_n)]
