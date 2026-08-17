"""Prompt optimizer — automatically finds better prompts via trial-and-error.

DSPy-inspired approach: given a template, a labelled dataset, and an
evaluation metric, the optimizer searches for:
- The best few-shot examples (bootstrap strategy).
- Better template wording (refinement strategy).
- The highest-scoring template across a competing set (ensemble strategy).

All LLM calls are made through ``LLMClientProtocol``, keeping the optimizer
provider-agnostic.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from lexigram.ai.prompt.exceptions import OptimizationError
from lexigram.ai.prompt.optimization.few_shot import DynamicFewShotSelector
from lexigram.ai.prompt.optimization.types import (
    EvaluationMetric,
    Example,
    OptimizationStrategy,
    OptimizedPrompt,
)
from lexigram.contracts.ai.llm import ChatMessage, Role
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai import EmbeddingClientProtocol, LLMClientProtocol

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Prompt templates used internally by the optimizer
# ---------------------------------------------------------------------------

_REFINEMENT_SYSTEM = (
    "You are an expert prompt engineer. "
    "Given a prompt template and examples of where it fails, rewrite the "
    "template to improve accuracy while preserving the original intent. "
    "Return only the revised template text — no commentary."
)

_REFINEMENT_USER = (
    "Original template:\n{template}\n\n"
    "Failures (input → predicted vs expected):\n{failures}\n\n"
    "Write an improved version:"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_examples(examples: list[Example]) -> str:
    """Format examples as a readable block for inclusion in prompts."""
    lines: list[str] = []
    for i, ex in enumerate(examples, start=1):
        lines.append(f"[{i}] Input: {ex.input}")
        lines.append(f"    Expected: {ex.expected_output}")
    return "\n".join(lines)


async def _evaluate_template(
    llm: LLMClientProtocol,
    template: str,
    examples: list[Example],
    metric: EvaluationMetric,
    few_shot: list[Example],
) -> tuple[float, list[tuple[str, str, str]]]:
    """Run *template* on each *example*, score with *metric*.

    Args:
        llm: LLM client for generating predictions.
        template: Prompt template (uses ``{input}`` placeholder).
        examples: Evaluation examples.
        metric: Callable ``(prediction, expected) -> float``.
        few_shot: Few-shot examples to prepend to every call.

    Returns:
        Tuple of (mean_score, failures) where failures is a list of
        (input, predicted, expected) for low-scoring examples.
    """
    prefix = _format_examples(few_shot) + "\n\n" if few_shot else ""

    scores: list[float] = []
    failures: list[tuple[str, str, str]] = []

    async def _run_one(ex: Example) -> tuple[float, tuple[str, str, str] | None]:
        prompt = prefix + template.replace("{input}", ex.input)
        messages = [ChatMessage(role=Role.USER, content=prompt)]
        result = await llm.complete(messages)
        if result.is_err():
            return 0.0, (ex.input, "<error>", ex.expected_output)
        prediction = result.unwrap().content or ""
        score = metric(prediction, ex.expected_output)
        fail_entry = None
        if score < 0.5:
            fail_entry = (ex.input, prediction, ex.expected_output)
        return score, fail_entry

    tasks = [_run_one(ex) for ex in examples]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    for s, f in results:
        scores.append(s)
        if f is not None:
            failures.append(f)

    mean_score = sum(scores) / len(scores) if scores else 0.0
    return mean_score, failures


# ---------------------------------------------------------------------------
# PromptOptimizer
# ---------------------------------------------------------------------------


class PromptOptimizer:
    """Automatically optimize a prompt template on a labelled dataset.

    Supports three strategies (see :class:`OptimizationStrategy`):

    * ``BOOTSTRAP_FEW_SHOT`` — iteratively searches the example pool for few-shot
      combinations that maximise the evaluation metric.
    * ``TEMPLATE_REFINEMENT`` — asks the LLM to rewrite the template based on
      analysis of failure cases; repeats until score stops improving.
    * ``ENSEMBLE`` — evaluates a list of candidate templates, returns the best.

    Example::

        from lexigram.ai.prompt.optimization import PromptOptimizer, Example

        optimizer = PromptOptimizer(llm=my_llm, embedding_client=my_embedder)

        best = await optimizer.optimize(
            template="Answer the question: {input}",
            examples=training_data,
            metric=lambda pred, exp: 1.0 if pred.strip() == exp.strip() else 0.0,
            max_iterations=10,
        )
        print(best.template, best.score)
    """

    def __init__(
        self,
        llm: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol | None = None,
        *,
        seed: int = 42,
    ) -> None:
        """Initialize the optimizer.

        Args:
            llm: LLM client used for generating predictions (and template
                rewrites in TEMPLATE_REFINEMENT mode).
            embedding_client: Optional embedding client used for
                ``BOOTSTRAP_FEW_SHOT`` dynamic example selection.  When
                ``None``, examples are sampled randomly.
            seed: Random seed for reproducibility.
        """
        self._llm = llm
        self._embedding_client = embedding_client
        self._rng = random.Random(seed)  # noqa: S311 — deterministic optimization sampling

    async def optimize(
        self,
        template: str,
        examples: list[Example],
        metric: EvaluationMetric,
        *,
        max_iterations: int = 20,
        strategy: OptimizationStrategy = OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        val_fraction: float = 0.2,
        max_few_shot: int = 3,
        candidate_templates: list[str] | None = None,
    ) -> OptimizedPrompt:
        """Run the optimization loop and return the best prompt found.

        Args:
            template: Starting prompt template (use ``{input}`` as the
                placeholder for the user's input).
            examples: Labelled examples (split into train/val internally).
            metric: Scoring function ``(prediction, expected) -> float``
                returning a value in [0, 1].
            max_iterations: Maximum optimization iterations.
            strategy: Which search strategy to use.
            val_fraction: Fraction of examples used for held-out validation.
            max_few_shot: Maximum few-shot examples to prepend.
            candidate_templates: For ``ENSEMBLE`` strategy — list of
                templates to evaluate; *template* is always included.

        Returns:
            :class:`OptimizedPrompt` with the best template and examples found.

        Raises:
            OptimizationError: If the dataset is too small or the LLM fails
                consistently.
        """
        if len(examples) < 2:
            raise OptimizationError(
                f"Need at least 2 examples for optimization, got {len(examples)}"
            )

        # Split train/val
        shuffled = list(examples)
        self._rng.shuffle(shuffled)
        n_val = max(1, int(len(shuffled) * val_fraction))
        val_set = shuffled[:n_val]
        train_set = shuffled[n_val:]

        logger.info(
            "prompt_optimizer_start",
            strategy=strategy,
            train_size=len(train_set),
            val_size=len(val_set),
            max_iterations=max_iterations,
        )

        if strategy == OptimizationStrategy.BOOTSTRAP_FEW_SHOT:
            return await self._bootstrap_few_shot(
                template, train_set, val_set, metric, max_iterations, max_few_shot
            )
        if strategy == OptimizationStrategy.TEMPLATE_REFINEMENT:
            return await self._template_refinement(
                template, train_set, val_set, metric, max_iterations, max_few_shot
            )
        if strategy == OptimizationStrategy.ENSEMBLE:
            candidates = list(candidate_templates or [])
            if template not in candidates:
                candidates.insert(0, template)
            return await self._ensemble(candidates, val_set, metric, max_few_shot)

        raise OptimizationError(f"Unknown strategy: {strategy}")

    # ------------------------------------------------------------------
    # Bootstrap few-shot strategy
    # ------------------------------------------------------------------

    async def _bootstrap_few_shot(
        self,
        template: str,
        train: list[Example],
        val: list[Example],
        metric: EvaluationMetric,
        max_iter: int,
        max_few_shot: int,
    ) -> OptimizedPrompt:
        """Iteratively search for the best few-shot combination."""
        best_score = -1.0
        best_examples: list[Example] = []

        if self._embedding_client is not None:
            selector = DynamicFewShotSelector(
                train,
                self._embedding_client,
                max_examples=max_few_shot,
            )
        else:
            selector = None

        for iteration in range(max_iter):
            if selector is not None:
                # Use embedding similarity on the first val example as proxy
                candidate_examples = await selector.select(val[0].input)
            else:
                k = min(max_few_shot, len(train))
                candidate_examples = self._rng.sample(train, k)

            score, _ = await _evaluate_template(
                self._llm, template, val, metric, candidate_examples
            )

            logger.debug(
                "bootstrap_iteration",
                iteration=iteration,
                score=score,
                best_score=best_score,
            )

            if score > best_score:
                best_score = score
                best_examples = list(candidate_examples)

            if best_score >= 1.0:
                break  # perfect score

        return OptimizedPrompt(
            template=template,
            few_shot_examples=best_examples,
            score=best_score,
            iterations=max_iter,
            strategy=OptimizationStrategy.BOOTSTRAP_FEW_SHOT,
        )

    # ------------------------------------------------------------------
    # Template refinement strategy
    # ------------------------------------------------------------------

    async def _template_refinement(
        self,
        template: str,
        train: list[Example],
        val: list[Example],
        metric: EvaluationMetric,
        max_iter: int,
        max_few_shot: int,
    ) -> OptimizedPrompt:
        """Ask the LLM to iteratively rewrite the template to fix failures."""
        current_template = template
        few_shot: list[Example] = []

        best_score, failures = await _evaluate_template(
            self._llm, current_template, val, metric, few_shot
        )
        best_template = current_template

        for iteration in range(max_iter):
            if not failures:
                break  # no failures to fix

            failures_text = "\n".join(
                f"Input: {inp}\n  Predicted: {pred}\n  Expected: {exp}"
                for inp, pred, exp in failures[:5]  # only show top 5
            )
            messages = [
                ChatMessage(role=Role.SYSTEM, content=_REFINEMENT_SYSTEM),
                ChatMessage(
                    role=Role.USER,
                    content=_REFINEMENT_USER.format(
                        template=current_template,
                        failures=failures_text,
                    ),
                ),
            ]
            result = await self._llm.complete(messages)
            if not result.is_ok():
                logger.warning(
                    "template_refinement_llm_failure",
                    iteration=iteration,
                    error=str(result.unwrap_err()),
                )
                break

            candidate_template = (result.unwrap().content or "").strip()
            if not candidate_template:
                break

            score, failures = await _evaluate_template(
                self._llm, candidate_template, val, metric, few_shot
            )

            logger.debug(
                "refinement_iteration",
                iteration=iteration,
                score=score,
                best_score=best_score,
            )

            if score > best_score:
                best_score = score
                best_template = candidate_template
                current_template = candidate_template
            else:
                # Revert and try again from the best known template
                current_template = best_template

        return OptimizedPrompt(
            template=best_template,
            few_shot_examples=few_shot,
            score=best_score,
            iterations=max_iter,
            strategy=OptimizationStrategy.TEMPLATE_REFINEMENT,
        )

    # ------------------------------------------------------------------
    # Ensemble strategy
    # ------------------------------------------------------------------

    async def _ensemble(
        self,
        candidates: list[str],
        val: list[Example],
        metric: EvaluationMetric,
        max_few_shot: int,
    ) -> OptimizedPrompt:
        """Evaluate all candidate templates and return the best."""
        best_score = -1.0
        best_template = candidates[0]

        async def _score(tmpl: str) -> tuple[float, str]:
            s, _ = await _evaluate_template(self._llm, tmpl, val, metric, [])
            return s, tmpl

        results = await asyncio.gather(*[_score(t) for t in candidates])
        for score, tmpl in results:
            logger.debug("ensemble_candidate", score=score)
            if score > best_score:
                best_score = score
                best_template = tmpl

        return OptimizedPrompt(
            template=best_template,
            few_shot_examples=[],
            score=best_score,
            iterations=len(candidates),
            strategy=OptimizationStrategy.ENSEMBLE,
        )


__all__ = ["PromptOptimizer"]
