import re

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

STOPWORDS = frozenset("""
about above after again all also and any are because been before being below between both but can
could did does doing down during each few for from further had has have having her here him his how
into its itself just more most much not now off once only other our out over own same she should
some such than that the their them then there these they this those through too under until very
was were what when where which while who whom why will with would you your say said says write wrote
written writing tell told mention mentioned note notes noted entry entries anything something
someone thing things like get got
""".split())

DATE_WORDS = frozenset(
    "january february march april may june july august september october november december "
    "today yesterday tomorrow week weeks month months day days year years ago last past previous "
    "recent recently lately earlier".split()
)


def content_terms(text: str, max_terms: int = 8) -> list[str]:
    """Return terms useful for deciding whether a date query needs semantic search."""
    seen: set[str] = set()
    terms: list[str] = []
    for token in _TOKEN.findall((text or "").casefold()):
        if len(token) < 3 or token in STOPWORDS or token in DATE_WORDS or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms[:max_terms]
