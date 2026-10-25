"""Global context budget.

Every dynamic source (tasks, events, behavior, memory, conversation history) is a
`Block` of items ordered most-important-first. When the total is over budget we drop
items from the tail of the lowest-priority block (highest `priority` number) until it
fits. Whole items are dropped, never sliced mid-sentence, and the caller is told what
was omitted so the model can be honest about incompleteness.

The user's current message and the fixed system rules are NOT part of the budget and
are never trimmed.
"""
from dataclasses import dataclass, field

MAX_CONTEXT_CHARS = 7000


@dataclass
class Block:
    name: str
    priority: float  # lower = kept longest
    items: list[str]
    min_items: int = 0  # never trimmed below this many items
    header: str = ""


@dataclass
class BudgetResult:
    kept: dict[str, int]
    omitted: dict[str, int] = field(default_factory=dict)
    total_chars: int = 0
    over_budget: bool = False


def block_size(block: Block, count: int) -> int:
    if count <= 0:
        return 0
    return len(block.header) + 1 + sum(len(item) + 1 for item in block.items[:count])


def fit_blocks(blocks: list[Block], budget: int = MAX_CONTEXT_CHARS) -> BudgetResult:
    kept = {block.name: len(block.items) for block in blocks}
    by_name = {block.name: block for block in blocks}

    def total() -> int:
        return sum(block_size(by_name[name], count) for name, count in kept.items())

    # Header-only blocks (no items) still cost their header; keep them as-is.
    for name, block in by_name.items():
        if not block.items and block.header:
            kept[name] = 0

    order = sorted(blocks, key=lambda b: b.priority, reverse=True)
    while total() > budget:
        for block in order:
            if kept[block.name] > block.min_items:
                kept[block.name] -= 1
                break
        else:
            break  # everything is at its floor; accept being over budget

    omitted = {
        block.name: len(block.items) - kept[block.name]
        for block in blocks
        if len(block.items) - kept[block.name] > 0
    }
    current = total()
    return BudgetResult(kept=kept, omitted=omitted, total_chars=current, over_budget=current > budget)


OMISSION_NOTE = (
    "Note: some lower-priority context was left out to keep this short "
    "({parts}). Do not claim to have shown a complete list; say so if completeness matters."
)


def omission_note(omitted: dict[str, int]) -> str:
    if not omitted:
        return ""
    parts = ", ".join(f"{count} {name.replace('_', ' ')}" for name, count in omitted.items())
    return OMISSION_NOTE.format(parts=parts)
