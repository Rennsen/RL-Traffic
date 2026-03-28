from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random
from typing import DefaultDict, List, Tuple

State = Tuple[int, int, int, int, int]


@dataclass
class QLearningHyperParams:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    seed: int = 0


class QLearningAgent:
    def __init__(self, params: QLearningHyperParams) -> None:
        self.params = params
        self.epsilon = params.epsilon_start
        self._rng = random.Random(params.seed)
        self._q_table: DefaultDict[State, List[float]] = defaultdict(lambda: [0.0, 0.0])

    def select_action(self, state: State, explore: bool = True) -> int:
        if explore and self._rng.random() < self.epsilon:
            return self._rng.randint(0, 1)

        action_values = self._q_table[state]
        return 0 if action_values[0] >= action_values[1] else 1

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        lr = self.params.learning_rate
        gamma = self.params.discount_factor

        current_q = self._q_table[state][action]
        future = 0.0 if done else max(self._q_table[next_state])
        target = reward + gamma * future

        self._q_table[state][action] = current_q + lr * (target - current_q)

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.params.epsilon_min, self.epsilon * self.params.epsilon_decay)

    @property
    def q_table_size(self) -> int:
        return len(self._q_table)
