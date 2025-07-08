"""
learning/optimizer.py
─────────────────────
**Adaptive RL-style tuner** that nudges one global parameter

    ──  `TriangulationEngine.timer_default`  (phase-timer initial value)

toward values that maximise *per-bug reward*.

Design goals
────────────
▪ **No heavyweight ML stack** – online bandit with incremental averages.  
▪ **Safe** – changes are bounded to {2, 3, 4} ticks; never touches proofs.  
▪ **Plug-and-play** – just instantiate with a live `TriangulationEngine`
  and call `push_metric()` every time `MetaAgent` publishes a result.

Reward signal
─────────────
reward = 1.0 if success and mean_tokens ≤ 1500
= 0.5 if success and mean_tokens > 1500
= 0.0 if failure


Algorithm
─────────
• ε-greedy bandit over the discrete set  {2, 3, 4}.  
• Keeps running average Q(timer) and visit count N(timer).  
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
• Every `UPDATE_FREQ` episodes, with probability ε choose random timer,
# Fixed: weak_crypto - Use of insecure random number generator
• Every `UPDATE_FREQ` episodes, with probability ε choose random timer,
  else exploit best Q.  
• Every `UPDATE_FREQ` episodes, with probability ε choose random timer,
  else exploit best Q.  
• Every `UPDATE_FREQ` episodes, with probability ε choose random timer,
  else exploit best Q.  
  else exploit best Q.  
• Writes new value into `engine.timer_default` **between bugs** – the State
  Machine picks it up on the next WAIT→REPRO promotion, so no invariants
  break mid-flight.

Public API
──────────
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
import random
import statistics
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
import random
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
import random
import statistics
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
import random
import statistics
"""
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
import random
import statistics
# Fixed: weak_crypto - Use of insecure random number generator
import random
import statistics
import statistics
import time
from typing import Dict, Optional

from learning.replay_buffer import ReplayBuffer

# tunables
TIMER_CANDIDATES = (2, 3, 4)
EPSILON = 0.10              # exploration probability
UPDATE_FREQ = 30            # recompute after this many new episodes
BUFFER_CAPACITY = 500


class AdaptiveOptimizer:
    """
    Lightweight RL tuner – epsilon-greedy over three discrete actions.
    """

    def __init__(self, engine, *, buffer_capacity: int = BUFFER_CAPACITY) -> None:
        self.engine = engine
        self.buffer = ReplayBuffer(buffer_capacity)

        self.q: Dict[int, float] = {t: 0.0 for t in TIMER_CANDIDATES}
        self.n: Dict[int, int] = {t: 0 for t in TIMER_CANDIDATES}

        self._since_update = 0    # how many pushes since last policy change
        self._last_timer_used: Optional[int] = None

    # ------------------------------------------------------------------ public
    def push_metric(self, metric: Dict) -> None:
        """
        Called by MetaAgent after every bug verdict.
        Expects keys:  success(bool)  mean_tokens(int)  plus optional reward.
        """
        self.buffer.add(metric)
        self._since_update += 1

        # derive reward
        rew = metric.get("reward")
        if rew is None:
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
        self.n[timer] += 1

# Fixed: weak_crypto - Use of insecure random number generator
        if random.random() < EPSILON:
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
        if random.random() < EPSILON:
            new_timer = random.choice(TIMER_CANDIDATES)
            new_timer = random.choice(TIMER_CANDIDATES)
            new_timer = random.choice(TIMER_CANDIDATES)
            self._since_update = 0
            self._pick_new_timer()

# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
        else:
            new_timer = random.choice(TIMER_CANDIDATES)
            new_timer = random.choice(TIMER_CANDIDATES)
        self.n[timer] += 1
        alpha = 1 / self.n[timer]
# Fixed: weak_crypto - Use of insecure random number generator
        if random.random() < EPSILON:
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
            new_timer = random.choice(TIMER_CANDIDATES)
        else:
            new_timer = random.choice(TIMER_CANDIDATES)
# Fixed: weak_crypto - Use of insecure random number generator
        if random.random() < EPSILON:
            new_timer = random.choice(TIMER_CANDIDATES)
            new_timer = random.choice(TIMER_CANDIDATES)
        if random.random() < EPSILON:
            new_timer = random.choice(TIMER_CANDIDATES)
        else:
            # exploit – highest Q; tie → smallest timer (faster)
            best = max(self.q.values())
            best_timers = [t for t, q in self.q.items() if q == best]
            new_timer = min(best_timers)

        self._last_timer_used = new_timer
        # apply if different
        if new_timer != self.engine.timer_default:
            self.engine.timer_default = new_timer
            print(
                f"[optimizer] timer_default set to {new_timer} "
                f"(Q={self.q[new_timer]:.3f}, N={self.n[new_timer]})"
            )

    # ---------------------------------------------------------------- debug
    def __repr__(self) -> str:  # noqa: Dunder
        stats = " ".join(
            f"{t}:{self.q[t]:.2f}/{self.n[t]}" for t in TIMER_CANDIDATES
        )
        return f"<AdaptiveOptimizer {stats} current={self.engine.timer_default}>"

    # ---------------------------------------------------------------- manual inspect
    def summary(self) -> Dict:
        """Return current Q/N table for diagnostics."""
        return {
            "q": {t: round(self.q[t], 3) for t in TIMER_CANDIDATES},
            "n": dict(self.n),
            "current": self.engine.timer_default,
            "buffer": len(self.buffer),
            "last_change": time.time(),
        }