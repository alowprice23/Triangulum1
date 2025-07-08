from .state import BugState, Phase

import asyncio

async def step(bug: BugState, free: int, coordinator) -> tuple[BugState, int]:
    """Return next bug state and delta to free-agent pool."""
    p, t, a, code_snippet = bug.phase, bug.timer, bug.attempts, bug.code_snippet

    # timer-countdown branch
    if p in {Phase.REPRO, Phase.PATCH, Phase.VERIFY} and t > 0:
        return BugState(p, t-1, a, code_snippet), 0

    # phase transitions
    if p is Phase.WAIT and free >= 3:
        return BugState(Phase.REPRO, 3, 0, code_snippet), -3

    if p is Phase.REPRO and t == 0:
        return BugState(Phase.PATCH, 3, a, code_snippet), 0

    if p is Phase.PATCH and t == 0:
        if coordinator:
            # Call the coordinator to generate a patch
            patch_success = await coordinator.step()
            if patch_success:
                return BugState(Phase.VERIFY, 3, a, code_snippet), 0
            else:
                return BugState(Phase.PATCH, 3, a + 1, code_snippet), 0
        else:
            # Fallback to deterministic behavior if no coordinator is available
            return BugState(Phase.VERIFY, 3, a, code_snippet), 0

    if p is Phase.VERIFY and t == 0 and a == 0:     # deterministic failure
        return BugState(Phase.PATCH, 3, 1, code_snippet), 0

    if p is Phase.VERIFY and t == 0 and a == 1:     # deterministic success
        return BugState(Phase.DONE, 0, 0, code_snippet), +3

    # terminal states or invalid timer
    return bug, 0
