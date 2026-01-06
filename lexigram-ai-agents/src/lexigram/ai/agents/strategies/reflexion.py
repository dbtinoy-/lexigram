"""Reflexion strategy — self-critique and iterative refinement for agent reasoning."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.agents.strategies.base import AbstractStrategy
from lexigram.ai.agents.types import ReasoningStep, ToolExecutionRecord
from lexigram.contracts.ai.agents import AgentError, AgentResponse
from lexigram.contracts.ai.llm import ChatMessage, Role
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.agents import ToolProtocol
    from lexigram.contracts.ai.llm import LLMClientProtocol

logger = get_logger(__name__)


_CRITIQUE_SUFFIX = (
    "\n\n---\nReview your previous response critically. "
    "Identify any factual errors, logical inconsistencies, missing information, "
    "or ways to be more helpful. "
    "If the response is already optimal, write 'NO_CHANGES_NEEDED'. "
    "Otherwise, describe the specific improvements needed in a numbered list."
)

_REFINE_PREFIX = (
    "Based on your self-critique, provide an improved response. "
    "Apply all identified improvements. Your refined response:\n\n"
)


class ReflexionStrategy(AbstractStrategy):
    """Reflexion reasoning strategy with self-critique and iterative refinement.

    The Reflexion strategy follows a three-phase loop:

    1. **Generate** — produce an initial response to the user's request.
    2. **Critique** — ask the same LLM to evaluate its own response,
       identifying errors or improvements.
    3. **Refine** — generate an improved response based on the critique.

    The loop repeats up to ``max_iterations`` times, stopping early when
    the critique declares the response optimal (``NO_CHANGES_NEEDED``).

    Example:
        >>> from lexigram.ai.agents import Agent
        >>> from lexigram.ai.agents.strategies import ReflexionStrategy
        >>>
        >>> agent = Agent(
        ...     llm=my_llm_client,
        ...     strategy=ReflexionStrategy(max_iterations=3),
        ... )
        >>> response = await agent.run("Explain quantum entanglement")
    """

    def __init__(
        self,
        max_iterations: int = 3,
        temperature_critique: float = 0.3,
        temperature_refine: float = 0.5,
    ) -> None:
        """Initialise the ReflexionStrategy.

        Args:
            max_iterations: Maximum number of critique–refine cycles (default 3).
                The strategy stops early when the critique returns
                ``NO_CHANGES_NEEDED``.
            temperature_critique: LLM temperature for the self-critique pass.
                Lower values yield more deterministic critiques.
            temperature_refine: LLM temperature for the refinement pass.
        """
        self.max_iterations = max_iterations
        self.temperature_critique = temperature_critique
        self.temperature_refine = temperature_refine

    async def execute(
        self,
        message: str,
        tools: list[ToolProtocol],
        history: list[dict[str, Any]],
        llm: LLMClientProtocol,
        **kwargs: Any,
    ) -> Result[AgentResponse, AgentError]:
        """Execute the Reflexion reasoning loop.

        Args:
            message: The user's input message.
            tools: Tools available to the agent (informational; reflexion does
                not call tools directly).
            history: Conversation history as list of message dicts.
            llm: LLM client implementing
                :class:`~lexigram.contracts.ai.LLMClientProtocol`.
            **kwargs: Additional parameters:
                - ``system_prompt`` (str): Optional system prompt.
                - ``timeout`` (float): Per-call timeout in seconds.

        Returns:
            ``Ok(AgentResponse)`` with the final refined message and the full
            reasoning trace (initial draft + critique + final response per
            iteration).
            ``Err(AgentError)`` if the LLM call fails or is cancelled.
        """
        system_prompt: str = kwargs.get("system_prompt", "")
        timeout: float = kwargs.get("timeout", 60.0)

        steps: list[ReasoningStep] = []
        tool_calls: list[ToolExecutionRecord] = []

        # Build initial chat messages from history
        messages: list[ChatMessage] = self._build_messages(
            message, history, system_prompt
        )

        # Phase 1: initial generation
        current_response = await self._call_llm(llm, messages, timeout=timeout)
        if current_response is None:
            return Err(
                AgentError("LLM returned empty response during initial generation")
            )

        steps.append(
            ReasoningStep(
                step_number=0,
                thought="[Reflexion] Initial response generated (iteration 0)",
                action=None,
                observation=current_response,
            )
        )

        logger.debug(
            "reflexion_initial_response",
            length=len(current_response),
        )

        # Phase 2+: critique → refine loop
        for iteration in range(1, self.max_iterations + 1):
            # Self-critique pass
            critique_messages = [
                *messages,
                ChatMessage(role=Role.ASSISTANT, content=current_response),
                ChatMessage(role=Role.USER, content=_CRITIQUE_SUFFIX),
            ]
            critique = await self._call_llm(
                llm,
                critique_messages,
                temperature=self.temperature_critique,
                timeout=timeout,
            )
            if critique is None:
                logger.warning("reflexion_critique_failed", iteration=iteration)
                break

            steps.append(
                ReasoningStep(
                    step_number=(iteration * 2) - 1,
                    thought=f"[Reflexion] Self-critique (iteration {iteration})",
                    action="critique",
                    observation=critique,
                )
            )

            logger.debug(
                "reflexion_critique",
                iteration=iteration,
                length=len(critique),
            )

            # Early stopping: LLM declared the response optimal
            if "NO_CHANGES_NEEDED" in critique.upper():
                logger.debug(
                    "reflexion_early_stop",
                    iteration=iteration,
                    reason="NO_CHANGES_NEEDED",
                )
                steps.append(
                    ReasoningStep(
                        step_number=iteration * 2,
                        thought=f"[Reflexion] No changes needed — stopping at iteration {iteration}",
                        action=None,
                        observation=current_response,
                    )
                )
                break

            # Refinement pass
            refine_messages = [
                *critique_messages,
                ChatMessage(role=Role.ASSISTANT, content=critique),
                ChatMessage(role=Role.USER, content=_REFINE_PREFIX),
            ]
            refined = await self._call_llm(
                llm,
                refine_messages,
                temperature=self.temperature_refine,
                timeout=timeout,
            )
            if refined is None:
                logger.warning("reflexion_refine_failed", iteration=iteration)
                break

            current_response = refined
            steps.append(
                ReasoningStep(
                    step_number=iteration * 2,
                    thought=f"[Reflexion] Refined response (iteration {iteration})",
                    action="refine",
                    observation=current_response,
                )
            )

            logger.debug(
                "reflexion_refined",
                iteration=iteration,
                length=len(current_response),
            )

        return Ok(
            AgentResponse(
                message=current_response,
                steps=steps,
                tool_calls=tool_calls,
            )
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        message: str,
        history: list[dict[str, Any]],
        system_prompt: str,
    ) -> list[ChatMessage]:
        """Convert history + new message into a list of ChatMessage objects."""
        messages: list[ChatMessage] = []

        if system_prompt:
            messages.append(ChatMessage(role=Role.SYSTEM, content=system_prompt))

        for entry in history:
            role_str = entry.get("role", "user")
            content = entry.get("content", "")
            try:
                role = Role(role_str)
            except ValueError:
                role = Role.USER
            messages.append(ChatMessage(role=role, content=content))

        messages.append(ChatMessage(role=Role.USER, content=message))
        return messages

    async def _call_llm(
        self,
        llm: LLMClientProtocol,
        messages: list[ChatMessage],
        temperature: float | None = None,
        timeout: float = 60.0,
    ) -> str | None:
        """Call the LLM and return the text content, or ``None`` on failure."""
        kwargs: dict[str, Any] = {}
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            result = await asyncio.wait_for(
                llm.complete(cast("list[Any]", messages), **kwargs),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning("reflexion_llm_timeout", timeout=timeout)
            return None
        except (OSError, ConnectionError, RuntimeError, ValueError) as exc:
            logger.warning("reflexion_llm_error", error=str(exc))
            return None

        if not result.is_ok():
            logger.warning("reflexion_llm_err_result", error=str(result.unwrap_err()))
            return None

        completion = result.unwrap()
        return completion.content if hasattr(completion, "content") else str(completion)


__all__ = ["ReflexionStrategy"]
