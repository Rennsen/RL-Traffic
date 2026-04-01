from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import math
import random
from typing import DefaultDict, Deque, List, Protocol, Tuple

import numpy as np

State = Tuple[int, int, int, int, int]


class RLAgent(Protocol):
    def select_action(self, state: State, explore: bool = True) -> int:
        ...

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        ...

    def decay_epsilon(self) -> None:
        ...

    @property
    def model_size(self) -> int:
        ...

    @property
    def model_label(self) -> str:
        ...

    @property
    def exploration_value(self) -> float:
        ...

    @property
    def exploration_label(self) -> str:
        ...


@dataclass
class QLearningHyperParams:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    seed: int = 0
    min_learning_rate: float = 0.05
    learning_rate_decay_power: float = 0.1


class QLearningAgent:
    def __init__(self, params: QLearningHyperParams) -> None:
        self.params = params
        self.epsilon = params.epsilon_start
        self._rng = random.Random(params.seed)
        self._q_table: DefaultDict[State, List[float]] = defaultdict(lambda: [0.0, 0.0])
        self._visit_counts: DefaultDict[State, List[int]] = defaultdict(lambda: [0, 0])

    def _effective_learning_rate(self, state: State, action: int) -> float:
        visits = self._visit_counts[state][action]
        base = self.params.learning_rate
        decayed = base / ((visits + 1) ** self.params.learning_rate_decay_power)
        return max(self.params.min_learning_rate, decayed)

    def select_action(self, state: State, explore: bool = True) -> int:
        if explore and self._rng.random() < self.epsilon:
            return self._rng.randint(0, 1)

        action_values = self._q_table[state]
        best_value = max(action_values)
        best_actions = [idx for idx, value in enumerate(action_values) if abs(value - best_value) < 1e-12]
        return int(self._rng.choice(best_actions))

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        lr = self._effective_learning_rate(state, action)
        gamma = self.params.discount_factor

        current_q = self._q_table[state][action]
        future = 0.0 if done else max(self._q_table[next_state])
        target = reward + gamma * future

        self._q_table[state][action] = current_q + lr * (target - current_q)
        self._visit_counts[state][action] += 1

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.params.epsilon_min, self.epsilon * self.params.epsilon_decay)

    @property
    def model_size(self) -> int:
        return len(self._q_table)

    @property
    def model_label(self) -> str:
        return "Q-table states"

    @property
    def exploration_value(self) -> float:
        return self.epsilon

    @property
    def exploration_label(self) -> str:
        return "Final epsilon"


@dataclass
class DQNHyperParams:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    seed: int = 0
    hidden_dim: int = 32
    replay_capacity: int = 6000
    batch_size: int = 48
    learning_starts: int = 256
    target_sync_interval: int = 120
    tau: float = 0.06
    gradient_clip: float = 1.8
    huber_delta: float = 1.0
    replay_alpha: float = 0.65
    replay_beta_start: float = 0.45
    replay_beta_end: float = 1.0
    replay_priority_eps: float = 1e-3
    replay_priority_clip: float = 10.0


@dataclass(frozen=True)
class Transition:
    state: State
    action: int
    reward: float
    next_state: State
    done: bool


class PrioritizedReplayBuffer:
    def __init__(
        self,
        capacity: int,
        alpha: float,
        priority_eps: float,
        priority_clip: float,
    ) -> None:
        self._alpha = alpha
        self._priority_eps = priority_eps
        self._priority_clip = priority_clip
        self._memory: Deque[Transition] = deque(maxlen=capacity)
        self._priorities: Deque[float] = deque(maxlen=capacity)

    def append(self, transition: Transition) -> None:
        max_priority = max(self._priorities, default=1.0)
        self._memory.append(transition)
        self._priorities.append(max_priority)

    def __len__(self) -> int:
        return len(self._memory)

    def sample(
        self,
        batch_size: int,
        np_rng: np.random.Generator,
        beta: float,
    ) -> Tuple[List[Transition], np.ndarray, np.ndarray]:
        priorities = np.array(self._priorities, dtype=np.float64)
        scaled = np.power(priorities, self._alpha)
        scaled_sum = np.sum(scaled)
        if scaled_sum <= 0.0:
            probabilities = np.full_like(scaled, 1.0 / max(1, len(scaled)))
        else:
            probabilities = scaled / scaled_sum

        indices = np_rng.choice(
            len(self._memory),
            size=batch_size,
            replace=False,
            p=probabilities,
        )

        memory_list = list(self._memory)
        samples = [memory_list[int(index)] for index in indices]

        weights = np.power(len(self._memory) * probabilities[indices], -beta)
        weights = weights / (np.max(weights) + 1e-9)

        return samples, indices.astype(np.int64), weights.astype(np.float64)

    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray) -> None:
        for index, td_error in zip(indices.tolist(), td_errors.tolist()):
            priority = min(
                self._priority_clip,
                abs(float(td_error)) + self._priority_eps,
            )
            self._priorities[int(index)] = priority


class DQNAgent:
    def __init__(self, params: DQNHyperParams) -> None:
        self.params = params
        self.epsilon = params.epsilon_start
        self._rng = random.Random(params.seed)
        self._np_rng = np.random.default_rng(params.seed)
        self._state_scale = np.array([4.0, 4.0, 1.0, 3.0, 3.0], dtype=np.float64)

        input_dim = len(self._state_scale)
        hidden_dim = params.hidden_dim
        output_dim = 2

        self._w1 = self._np_rng.normal(0.0, 0.12, size=(input_dim, hidden_dim))
        self._b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._w2 = self._np_rng.normal(0.0, 0.12, size=(hidden_dim, output_dim))
        self._b2 = np.zeros(output_dim, dtype=np.float64)

        self._target_w1 = self._w1.copy()
        self._target_b1 = self._b1.copy()
        self._target_w2 = self._w2.copy()
        self._target_b2 = self._b2.copy()

        self._replay = PrioritizedReplayBuffer(
            capacity=params.replay_capacity,
            alpha=params.replay_alpha,
            priority_eps=params.replay_priority_eps,
            priority_clip=params.replay_priority_clip,
        )
        self._train_steps = 0
        self._beta = params.replay_beta_start
        self._beta_increment = (params.replay_beta_end - params.replay_beta_start) / 7000.0

    def _encode_state(self, state: State) -> np.ndarray:
        encoded = np.array(state, dtype=np.float64)
        return encoded / self._state_scale

    def _forward(
        self,
        inputs: np.ndarray,
        use_target: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        w1 = self._target_w1 if use_target else self._w1
        b1 = self._target_b1 if use_target else self._b1
        w2 = self._target_w2 if use_target else self._w2
        b2 = self._target_b2 if use_target else self._b2

        hidden_linear = inputs @ w1 + b1
        hidden = np.maximum(hidden_linear, 0.0)
        output = hidden @ w2 + b2
        return hidden_linear, hidden, output

    def _predict(self, state: State, use_target: bool = False) -> np.ndarray:
        inputs = self._encode_state(state).reshape(1, -1)
        _, _, output = self._forward(inputs, use_target=use_target)
        return output[0]

    def select_action(self, state: State, explore: bool = True) -> int:
        if explore and self._rng.random() < self.epsilon:
            return self._rng.randint(0, 1)

        q_values = self._predict(state)
        best_value = float(np.max(q_values))
        best_actions = [idx for idx, value in enumerate(q_values.tolist()) if abs(value - best_value) < 1e-12]
        return int(self._rng.choice(best_actions))

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        self._replay.append(
            Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
            )
        )

        ready_threshold = max(self.params.batch_size, self.params.learning_starts)
        if len(self._replay) < ready_threshold:
            return

        batch, indices, weights = self._replay.sample(
            batch_size=self.params.batch_size,
            np_rng=self._np_rng,
            beta=self._beta,
        )
        self._train_batch(batch=batch, indices=indices, weights=weights)
        self._train_steps += 1

        self._soft_update_target_network()
        if self._train_steps % self.params.target_sync_interval == 0:
            self._sync_target_network()

        self._beta = min(self.params.replay_beta_end, self._beta + self._beta_increment)

    def _train_batch(
        self,
        batch: List[Transition],
        indices: np.ndarray,
        weights: np.ndarray,
    ) -> None:
        states = np.vstack([self._encode_state(item.state) for item in batch])
        next_states = np.vstack([self._encode_state(item.next_state) for item in batch])
        actions = np.array([item.action for item in batch], dtype=np.int64)
        rewards = np.array([item.reward for item in batch], dtype=np.float64)
        dones = np.array([item.done for item in batch], dtype=np.float64)

        hidden_linear, hidden, outputs = self._forward(states)
        _, _, next_online_outputs = self._forward(next_states, use_target=False)
        _, _, next_target_outputs = self._forward(next_states, use_target=True)

        next_actions = np.argmax(next_online_outputs, axis=1)
        next_best = next_target_outputs[np.arange(len(batch)), next_actions]
        targets = rewards + (1.0 - dones) * self.params.discount_factor * next_best

        selected_q = outputs[np.arange(len(batch)), actions]
        td_error = selected_q - targets

        delta = self.params.huber_delta
        huber_grad = np.where(np.abs(td_error) <= delta, td_error, delta * np.sign(td_error))

        norm_weights = weights / (np.sum(weights) + 1e-9)
        scaled_grad = huber_grad * norm_weights

        grad_output = np.zeros_like(outputs)
        grad_output[np.arange(len(batch)), actions] = scaled_grad

        grad_w2 = hidden.T @ grad_output
        grad_b2 = np.sum(grad_output, axis=0)

        grad_hidden = grad_output @ self._w2.T
        grad_hidden[hidden_linear <= 0.0] = 0.0

        grad_w1 = states.T @ grad_hidden
        grad_b1 = np.sum(grad_hidden, axis=0)

        self._clip_global_norm([grad_w1, grad_b1, grad_w2, grad_b2], self.params.gradient_clip)

        lr = self.params.learning_rate
        self._w2 -= lr * grad_w2
        self._b2 -= lr * grad_b2
        self._w1 -= lr * grad_w1
        self._b1 -= lr * grad_b1

        self._replay.update_priorities(indices=indices, td_errors=np.abs(td_error))

    def _clip_global_norm(self, gradients: List[np.ndarray], clip: float) -> None:
        squared_sum = 0.0
        for grad in gradients:
            squared_sum += float(np.sum(np.square(grad)))

        norm = math.sqrt(max(1e-12, squared_sum))
        if norm <= clip:
            return

        scale = clip / norm
        for grad in gradients:
            grad *= scale

    def _soft_update_target_network(self) -> None:
        tau = self.params.tau
        self._target_w1 = (1.0 - tau) * self._target_w1 + tau * self._w1
        self._target_b1 = (1.0 - tau) * self._target_b1 + tau * self._b1
        self._target_w2 = (1.0 - tau) * self._target_w2 + tau * self._w2
        self._target_b2 = (1.0 - tau) * self._target_b2 + tau * self._b2

    def _sync_target_network(self) -> None:
        self._target_w1 = self._w1.copy()
        self._target_b1 = self._b1.copy()
        self._target_w2 = self._w2.copy()
        self._target_b2 = self._b2.copy()

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.params.epsilon_min, self.epsilon * self.params.epsilon_decay)

    @property
    def model_size(self) -> int:
        return int(self._w1.size + self._b1.size + self._w2.size + self._b2.size)

    @property
    def model_label(self) -> str:
        return "DQN parameters"

    @property
    def exploration_value(self) -> float:
        return self.epsilon

    @property
    def exploration_label(self) -> str:
        return "Final epsilon"


@dataclass
class PPOHyperParams:
    learning_rate: float
    discount_factor: float
    seed: int = 0
    hidden_dim: int = 32
    clip_ratio: float = 0.2
    gae_lambda: float = 0.95
    value_coef: float = 0.5
    entropy_coef: float = 0.02
    entropy_coef_decay: float = 0.997
    entropy_coef_min: float = 0.002
    ppo_epochs: int = 6
    minibatch_size: int = 64
    target_kl: float = 0.03
    gradient_clip: float = 1.0


@dataclass(frozen=True)
class PPOTransition:
    state: State
    action: int
    reward: float
    done: bool
    old_log_prob: float
    value_estimate: float
    next_value_estimate: float


class PPOAgent:
    def __init__(self, params: PPOHyperParams) -> None:
        self.params = params
        self._np_rng = np.random.default_rng(params.seed)
        self._state_scale = np.array([4.0, 4.0, 1.0, 3.0, 3.0], dtype=np.float64)
        self._trajectory: List[PPOTransition] = []
        self._last_entropy = 0.0
        self._entropy_coef = params.entropy_coef

        input_dim = len(self._state_scale)
        hidden_dim = params.hidden_dim

        self._policy_w1 = self._np_rng.normal(0.0, 0.10, size=(input_dim, hidden_dim))
        self._policy_b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._policy_w2 = self._np_rng.normal(0.0, 0.10, size=(hidden_dim, 2))
        self._policy_b2 = np.zeros(2, dtype=np.float64)

        self._value_w1 = self._np_rng.normal(0.0, 0.10, size=(input_dim, hidden_dim))
        self._value_b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._value_w2 = self._np_rng.normal(0.0, 0.10, size=(hidden_dim, 1))
        self._value_b2 = np.zeros(1, dtype=np.float64)

    def _encode_state(self, state: State) -> np.ndarray:
        encoded = np.array(state, dtype=np.float64)
        return encoded / self._state_scale

    def _policy_forward(self, inputs: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        hidden_linear = inputs @ self._policy_w1 + self._policy_b1
        hidden = np.maximum(hidden_linear, 0.0)
        logits = hidden @ self._policy_w2 + self._policy_b2
        return hidden_linear, hidden, logits

    def _value_forward(self, inputs: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        hidden_linear = inputs @ self._value_w1 + self._value_b1
        hidden = np.maximum(hidden_linear, 0.0)
        values = hidden @ self._value_w2 + self._value_b2
        return hidden_linear, hidden, values

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exp_values = np.exp(shifted)
        return exp_values / np.sum(exp_values, axis=1, keepdims=True)

    def _policy_probs(self, state: State) -> np.ndarray:
        inputs = self._encode_state(state).reshape(1, -1)
        _, _, logits = self._policy_forward(inputs)
        return self._softmax(logits)[0]

    def _state_value(self, state: State) -> float:
        inputs = self._encode_state(state).reshape(1, -1)
        _, _, values = self._value_forward(inputs)
        return float(values[0, 0])

    def select_action(self, state: State, explore: bool = True) -> int:
        probs = self._policy_probs(state)
        self._last_entropy = float(-np.sum(probs * np.log(np.clip(probs, 1e-9, 1.0))))
        if explore:
            return int(self._np_rng.choice(len(probs), p=probs))
        return int(np.argmax(probs))

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        probs = self._policy_probs(state)
        next_value = 0.0 if done else self._state_value(next_state)
        self._trajectory.append(
            PPOTransition(
                state=state,
                action=action,
                reward=reward,
                done=done,
                old_log_prob=float(np.log(np.clip(probs[action], 1e-9, 1.0))),
                value_estimate=self._state_value(state),
                next_value_estimate=next_value,
            )
        )

        if done:
            self._train_from_trajectory()
            self._trajectory.clear()

    def _clip_global_norm(self, gradients: List[np.ndarray], clip: float) -> None:
        squared_sum = 0.0
        for grad in gradients:
            squared_sum += float(np.sum(np.square(grad)))

        norm = math.sqrt(max(1e-12, squared_sum))
        if norm <= clip:
            return

        scale = clip / norm
        for grad in gradients:
            grad *= scale

    def _compute_gae(
        self,
        rewards: np.ndarray,
        dones: np.ndarray,
        values: np.ndarray,
        next_values: np.ndarray,
    ) -> np.ndarray:
        advantages = np.zeros_like(rewards)
        running_advantage = 0.0

        gamma = self.params.discount_factor
        lam = self.params.gae_lambda

        for idx in range(len(rewards) - 1, -1, -1):
            not_done = 1.0 - dones[idx]
            delta = rewards[idx] + gamma * next_values[idx] * not_done - values[idx]
            running_advantage = delta + gamma * lam * not_done * running_advantage
            advantages[idx] = running_advantage

        return advantages

    def _train_from_trajectory(self) -> None:
        if not self._trajectory:
            return

        states = np.vstack([self._encode_state(item.state) for item in self._trajectory])
        actions = np.array([item.action for item in self._trajectory], dtype=np.int64)
        rewards = np.array([item.reward for item in self._trajectory], dtype=np.float64)
        dones = np.array([item.done for item in self._trajectory], dtype=np.float64)
        old_log_probs = np.array([item.old_log_prob for item in self._trajectory], dtype=np.float64)
        values = np.array([item.value_estimate for item in self._trajectory], dtype=np.float64)
        next_values = np.array([item.next_value_estimate for item in self._trajectory], dtype=np.float64)

        advantages = self._compute_gae(rewards=rewards, dones=dones, values=values, next_values=next_values)
        returns = advantages + values

        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

        n_samples = len(actions)
        if n_samples == 0:
            return

        lr = self.params.learning_rate
        clip = self.params.gradient_clip

        last_policy_logits = None

        for _ in range(self.params.ppo_epochs):
            permutation = self._np_rng.permutation(n_samples)
            epoch_approx_kls: List[float] = []

            for start in range(0, n_samples, self.params.minibatch_size):
                mb_indices = permutation[start : start + self.params.minibatch_size]
                if len(mb_indices) == 0:
                    continue

                mb_states = states[mb_indices]
                mb_actions = actions[mb_indices]
                mb_old_log_probs = old_log_probs[mb_indices]
                mb_advantages = advantages[mb_indices]
                mb_returns = returns[mb_indices]

                policy_h_linear, policy_hidden, policy_logits = self._policy_forward(mb_states)
                probs = self._softmax(policy_logits)
                selected_probs = np.clip(probs[np.arange(len(mb_actions)), mb_actions], 1e-9, 1.0)
                new_log_probs = np.log(selected_probs)
                ratios = np.exp(new_log_probs - mb_old_log_probs)

                ratio_clip = self.params.clip_ratio
                clipped_ratios = np.clip(ratios, 1.0 - ratio_clip, 1.0 + ratio_clip)
                clip_active = ((mb_advantages >= 0.0) & (ratios > 1.0 + ratio_clip)) | (
                    (mb_advantages < 0.0) & (ratios < 1.0 - ratio_clip)
                )

                coeff = -(mb_advantages * ratios)
                coeff[clip_active] = 0.0
                coeff /= len(mb_actions)

                grad_logits = probs.copy()
                grad_logits[np.arange(len(mb_actions)), mb_actions] -= 1.0
                grad_logits *= coeff[:, None]

                log_probs_full = np.log(np.clip(probs, 1e-9, 1.0))
                entropy_grad = probs * (
                    np.sum(probs * (log_probs_full + 1.0), axis=1, keepdims=True)
                    - (log_probs_full + 1.0)
                )
                grad_logits -= self._entropy_coef * entropy_grad / len(mb_actions)

                grad_policy_w2 = policy_hidden.T @ grad_logits
                grad_policy_b2 = np.sum(grad_logits, axis=0)
                grad_policy_hidden = grad_logits @ self._policy_w2.T
                grad_policy_hidden[policy_h_linear <= 0.0] = 0.0
                grad_policy_w1 = mb_states.T @ grad_policy_hidden
                grad_policy_b1 = np.sum(grad_policy_hidden, axis=0)

                value_h_linear, value_hidden, value_outputs = self._value_forward(mb_states)
                value_error = (value_outputs[:, 0] - mb_returns) / len(mb_actions)
                grad_value_output = (2.0 * self.params.value_coef * value_error).reshape(-1, 1)
                grad_value_w2 = value_hidden.T @ grad_value_output
                grad_value_b2 = np.sum(grad_value_output, axis=0)
                grad_value_hidden = grad_value_output @ self._value_w2.T
                grad_value_hidden[value_h_linear <= 0.0] = 0.0
                grad_value_w1 = mb_states.T @ grad_value_hidden
                grad_value_b1 = np.sum(grad_value_hidden, axis=0)

                self._clip_global_norm(
                    [grad_policy_w1, grad_policy_b1, grad_policy_w2, grad_policy_b2],
                    clip,
                )
                self._clip_global_norm(
                    [grad_value_w1, grad_value_b1, grad_value_w2, grad_value_b2],
                    clip,
                )

                self._policy_w2 -= lr * grad_policy_w2
                self._policy_b2 -= lr * grad_policy_b2
                self._policy_w1 -= lr * grad_policy_w1
                self._policy_b1 -= lr * grad_policy_b1

                self._value_w2 -= lr * grad_value_w2
                self._value_b2 -= lr * grad_value_b2
                self._value_w1 -= lr * grad_value_w1
                self._value_b1 -= lr * grad_value_b1

                approx_kl = float(np.mean(mb_old_log_probs - new_log_probs))
                epoch_approx_kls.append(max(0.0, approx_kl))
                last_policy_logits = policy_logits

            mean_kl = float(np.mean(epoch_approx_kls)) if epoch_approx_kls else 0.0
            if mean_kl > self.params.target_kl * 1.5:
                break

        if last_policy_logits is None:
            _, _, last_policy_logits = self._policy_forward(states)

        final_probs = self._softmax(last_policy_logits)
        self._last_entropy = float(-np.mean(np.sum(final_probs * np.log(np.clip(final_probs, 1e-9, 1.0)), axis=1)))
        self._entropy_coef = max(
            self.params.entropy_coef_min,
            self._entropy_coef * self.params.entropy_coef_decay,
        )

    def decay_epsilon(self) -> None:
        return

    @property
    def model_size(self) -> int:
        return int(
            self._policy_w1.size
            + self._policy_b1.size
            + self._policy_w2.size
            + self._policy_b2.size
            + self._value_w1.size
            + self._value_b1.size
            + self._value_w2.size
            + self._value_b2.size
        )

    @property
    def model_label(self) -> str:
        return "PPO parameters"

    @property
    def exploration_value(self) -> float:
        return self._last_entropy

    @property
    def exploration_label(self) -> str:
        return "Policy entropy"


def build_agent(
    algorithm: str,
    learning_rate: float,
    discount_factor: float,
    epsilon_start: float,
    epsilon_min: float,
    epsilon_decay: float,
    seed: int,
) -> RLAgent:
    if algorithm == "dqn":
        dqn_lr = max(0.003, min(0.03, learning_rate * 0.15))
        return DQNAgent(
            DQNHyperParams(
                learning_rate=dqn_lr,
                discount_factor=discount_factor,
                epsilon_start=epsilon_start,
                epsilon_min=epsilon_min,
                epsilon_decay=epsilon_decay,
                seed=seed,
            )
        )

    if algorithm == "ppo":
        ppo_lr = max(0.001, min(0.015, learning_rate * 0.08))
        return PPOAgent(
            PPOHyperParams(
                learning_rate=ppo_lr,
                discount_factor=discount_factor,
                seed=seed,
            )
        )

    return QLearningAgent(
        QLearningHyperParams(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon_start=epsilon_start,
            epsilon_min=epsilon_min,
            epsilon_decay=epsilon_decay,
            seed=seed,
        )
    )
