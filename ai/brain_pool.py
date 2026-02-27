"""Brain pool — manages N brains per mode with evolutionary selection.

Pool lifecycle per game run:
  1. pick_brain()       → brain with fewest recent episodes (round-robin)
  2. Brain drives AI    → _action_to_keys() each frame
  3. report_result()    → updates brain stats
  4. maybe_evolve()     → after pool_size results, run evolution
"""
import json
import os
import random
import tempfile
import logging

from ai.brain import BaseBrain, BRAIN_CLASSES, MODE_BRAIN_NAMES, random_brain_name

log = logging.getLogger(__name__)

BRAINS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brains")


class BrainPool:
    """Manages N brains per mode with evolution."""

    def __init__(self, mode_index, pool_size=8):
        self.mode_index = mode_index
        self.brain_class = BRAIN_CLASSES[mode_index]
        self.pool_size = pool_size
        self.brains = []
        self.generation = 0
        self._results_since_evolve = 0
        self._next_brain_id = 0

        self.mode_name = MODE_BRAIN_NAMES.get(mode_index, f"mode{mode_index}")
        self.brain_file = os.path.join(BRAINS_DIR, f"{self.mode_name}_pool.json")

        self._load()

    # ── Pool management ─────────────────────────────────────────

    def _make_brain(self):
        brain = self.brain_class(brain_id=self._next_brain_id, name=random_brain_name())
        brain.generation = self.generation
        brain.origin = "fresh"
        self._next_brain_id += 1
        return brain

    def _ensure_pool(self):
        """Fill pool to pool_size with fresh brains if needed."""
        while len(self.brains) < self.pool_size:
            self.brains.append(self._make_brain())

    def pick_brain(self):
        """Return the brain with fewest recent episodes (round-robin fairness)."""
        self._ensure_pool()
        return min(self.brains, key=lambda b: b.total_episodes)

    def get_brain_by_id(self, brain_id):
        for b in self.brains:
            if b.id == brain_id:
                return b
        return None

    def report_result(self, brain_id, score, frames=0):
        """Update brain stats after a game run. Triggers evolution check."""
        brain = self.get_brain_by_id(brain_id)
        if brain:
            brain.end_episode(score, frames)
        self._results_since_evolve += 1
        if self._results_since_evolve >= self.pool_size:
            self.evolve()
            self._results_since_evolve = 0
        self._save()

    # ── Evolution ───────────────────────────────────────────────

    def evolve(self):
        """Run one generation of evolution on the pool.

        - Top 2: survive unchanged (elites)
        - Next 2: crossover from top 2 parents
        - Next 2: mutation of a random elite
        - Last 2: fresh random brains (immigration)
        """
        if len(self.brains) < 4:
            return

        self.generation += 1
        ranked = sorted(self.brains, key=lambda b: b.avg_score, reverse=True)

        new_pool = []
        slots = self.pool_size

        # Elites (top 2, or top 1 if pool is tiny)
        n_elites = min(2, slots)
        for brain in ranked[:n_elites]:
            brain.origin = "elite"
            new_pool.append(brain)

        # Crossover (2 children from top 2)
        parent_a = ranked[0]
        parent_b = ranked[min(1, len(ranked) - 1)]
        n_crossover = min(2, slots - len(new_pool))
        for _ in range(n_crossover):
            child = self._crossover(parent_a, parent_b)
            new_pool.append(child)

        # Mutation (2 clones with noise)
        n_mutate = min(2, slots - len(new_pool))
        for _ in range(n_mutate):
            source = random.choice(ranked[:n_elites])
            mutant = self._mutate(source)
            new_pool.append(mutant)

        # Fresh immigration (fill remaining slots)
        while len(new_pool) < slots:
            fresh = self._make_brain()
            new_pool.append(fresh)

        self.brains = new_pool
        log.info("Evolution gen %d for %s pool", self.generation, self.mode_name)

    def _crossover(self, parent_a, parent_b):
        """Create child brain by randomly picking Q-values from two parents."""
        child = self.brain_class(brain_id=self._next_brain_id, name=random_brain_name())
        self._next_brain_id += 1
        child.generation = self.generation
        child.parent_ids = [parent_a.id, parent_b.id]
        child.origin = "crossover"

        # Average hyperparams
        child.alpha = (parent_a.alpha + parent_b.alpha) / 2
        child.gamma = (parent_a.gamma + parent_b.gamma) / 2
        child.epsilon = max(parent_a.epsilon, parent_b.epsilon)

        # Mix Q-tables
        all_keys = set(parent_a.q_table.keys()) | set(parent_b.q_table.keys())
        for key in all_keys:
            if key in parent_a.q_table and key in parent_b.q_table:
                # Randomly pick from either parent for each key
                if random.random() < 0.5:
                    child.q_table[key] = list(parent_a.q_table[key])
                else:
                    child.q_table[key] = list(parent_b.q_table[key])
            elif key in parent_a.q_table:
                child.q_table[key] = list(parent_a.q_table[key])
            else:
                child.q_table[key] = list(parent_b.q_table[key])

        return child

    def _mutate(self, source):
        """Clone a brain and add gaussian noise to Q-values."""
        mutant = self.brain_class(brain_id=self._next_brain_id, name=random_brain_name())
        self._next_brain_id += 1
        mutant.generation = self.generation
        mutant.parent_ids = [source.id]
        mutant.origin = "mutation"

        mutant.alpha = max(0.01, min(0.5, source.alpha + random.gauss(0, 0.02)))
        mutant.gamma = max(0.5, min(0.99, source.gamma + random.gauss(0, 0.02)))
        mutant.epsilon = max(0.01, min(0.5, source.epsilon + random.gauss(0, 0.05)))

        sigma = 0.5
        for key, vals in source.q_table.items():
            mutant.q_table[key] = [v + random.gauss(0, sigma) for v in vals]

        return mutant

    # ── Persistence ─────────────────────────────────────────────

    def _save(self):
        os.makedirs(BRAINS_DIR, exist_ok=True)
        data = {
            "mode_name": self.mode_name,
            "mode_index": self.mode_index,
            "generation": self.generation,
            "pool_size": self.pool_size,
            "next_brain_id": self._next_brain_id,
            "results_since_evolve": self._results_since_evolve,
            "brains": [b.to_dict() for b in self.brains],
        }
        tmp_fd, tmp_path = tempfile.mkstemp(dir=BRAINS_DIR, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                json.dump(data, f)
            os.replace(tmp_path, self.brain_file)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _load(self):
        if not os.path.exists(self.brain_file):
            self._ensure_pool()
            return
        try:
            with open(self.brain_file, 'r') as f:
                data = json.load(f)
            self.generation = data.get("generation", 0)
            self._next_brain_id = data.get("next_brain_id", 0)
            self._results_since_evolve = data.get("results_since_evolve", 0)
            self.brains = []
            for bd in data.get("brains", []):
                brain = self.brain_class.from_dict(bd)
                self.brains.append(brain)
            self._ensure_pool()
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("Failed to load brain pool %s: %s", self.brain_file, e)
            self.brains = []
            self._ensure_pool()

    # ── Info ────────────────────────────────────────────────────

    def ranked_brains(self):
        """Return brains sorted by avg_score descending."""
        return sorted(self.brains, key=lambda b: b.avg_score, reverse=True)

    def stats_summary(self):
        total_eps = sum(b.total_episodes for b in self.brains)
        best = max((b.best_score for b in self.brains), default=0)
        return (f"{self.mode_name} pool: gen={self.generation} | "
                f"{len(self.brains)} brains | "
                f"total_eps={total_eps} | best={best:,}")
