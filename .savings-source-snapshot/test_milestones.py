# test_milestones.py — throwaway, run directly
from datetime import datetime, timezone, timedelta
from app.savings.service import determine_milestone_tier, check_milestones
from app.savings.models import SavingsVault

now = datetime.now(timezone.utc)

# Short vault — 7 days — should get [50, 100] only
tier = determine_milestone_tier(now, now + timedelta(days=7))
assert tier == "short", f"Expected short, got {tier}"

# Long vault — 6 months — should get [25, 50, 75, 100]
tier = determine_milestone_tier(now, now + timedelta(days=180))
assert tier == "long", f"Expected long, got {tier}"

# Fake a vault object at 60% progress, short tier, nothing reached yet
class FakeVault:
    current_amount = 60
    target_amount = 100
    milestone_tier = "short"
    milestones_reached = []

result = check_milestones(FakeVault())
assert result == [50], f"Expected [50], got {result}"

# Same vault, but 50 already recorded — should return nothing new
FakeVault.milestones_reached = [50]
result = check_milestones(FakeVault())
assert result == [], f"Expected [], got {result}"

print("All milestone tests passed.")