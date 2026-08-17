"""Unit tests for lexigram-ai-governance content_gate.

Covers:
* AlwaysAllowGate.evaluate() returns ALLOW.
* CompositeGate with one DENY gate → DENY.
* CompositeGate with [ALLOW, THROTTLE, ALLOW] → THROTTLE.
* CompositeGate aggregates reasons from all gates.
* Observer is invoked with the correct payload.
* Two-gate composition: custom deny gate + AlwaysAllowGate → DENY.
* ContentPolicyService emits a structured log and delegates to the gate.
"""

from __future__ import annotations

import pytest

from lexigram.ai.governance.content_gate.gates import AlwaysAllowGate, CompositeGate
from lexigram.ai.governance.content_gate.models import (
    PolicyDecision,
    PolicyOutcome,
    PolicyRequest,
)
from lexigram.ai.governance.content_gate.protocol import (
    ContentPolicyGateProtocol,
    PolicyObserverProtocol,
)
from lexigram.ai.governance.content_gate.service import ContentPolicyService


# ---------------------------------------------------------------------------
# Helpers — test doubles
# ---------------------------------------------------------------------------


def _make_request(
    principal_id: str | None = "user-1",
    content_type: str = "image",
    metadata: dict[str, str] | None = None,
    history: dict[str, int] | None = None,
) -> PolicyRequest:
    return PolicyRequest(
        principal_id=principal_id,
        content_type=content_type,
        content_metadata=metadata or {},
        history_summary=history,
    )


class _FixedOutcomeGate:
    """Test gate that always returns the configured decision."""

    def __init__(self, outcome: PolicyOutcome, reason: str = "") -> None:
        self._decision = PolicyDecision(outcome=outcome, reason=reason)

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        return self._decision


class _MetadataDenyGate:
    """Denies if a specific key/value pair is present in content_metadata."""

    def __init__(self, key: str, value: str) -> None:
        self._key = key
        self._value = value

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        if request.content_metadata.get(self._key) == self._value:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                reason=f"{self._key}={self._value} is not allowed",
            )
        return PolicyDecision(outcome=PolicyOutcome.ALLOW, reason="")


class _RecordingObserver:
    """Observer that records every on_decision call."""

    def __init__(self) -> None:
        self.calls: list[tuple[PolicyRequest, PolicyDecision]] = []

    async def on_decision(
        self, request: PolicyRequest, decision: PolicyDecision
    ) -> None:
        self.calls.append((request, decision))


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


def test_always_allow_gate_satisfies_protocol() -> None:
    gate = AlwaysAllowGate()
    assert isinstance(gate, ContentPolicyGateProtocol)


def test_composite_gate_satisfies_protocol() -> None:
    composite = CompositeGate(gates=[AlwaysAllowGate()])
    assert isinstance(composite, ContentPolicyGateProtocol)


def test_recording_observer_satisfies_protocol() -> None:
    obs = _RecordingObserver()
    assert isinstance(obs, PolicyObserverProtocol)


# ---------------------------------------------------------------------------
# AlwaysAllowGate
# ---------------------------------------------------------------------------


class TestAlwaysAllowGate:
    @pytest.mark.asyncio
    async def test_returns_allow(self) -> None:
        gate = AlwaysAllowGate()
        decision = await gate.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.ALLOW

    @pytest.mark.asyncio
    async def test_returns_allow_for_anonymous(self) -> None:
        gate = AlwaysAllowGate()
        decision = await gate.evaluate(_make_request(principal_id=None))
        assert decision.outcome == PolicyOutcome.ALLOW

    @pytest.mark.asyncio
    async def test_reason_is_empty(self) -> None:
        gate = AlwaysAllowGate()
        decision = await gate.evaluate(_make_request())
        assert decision.reason == ""


# ---------------------------------------------------------------------------
# CompositeGate — basic composition
# ---------------------------------------------------------------------------


class TestCompositeGate:
    @pytest.mark.asyncio
    async def test_single_deny_returns_deny(self) -> None:
        composite = CompositeGate(
            gates=[_FixedOutcomeGate(PolicyOutcome.DENY, reason="blocked")]
        )
        decision = await composite.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.DENY

    @pytest.mark.asyncio
    async def test_all_allow_returns_allow(self) -> None:
        composite = CompositeGate(
            gates=[
                _FixedOutcomeGate(PolicyOutcome.ALLOW),
                _FixedOutcomeGate(PolicyOutcome.ALLOW),
            ]
        )
        decision = await composite.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.ALLOW

    @pytest.mark.asyncio
    async def test_allow_throttle_allow_returns_throttle(self) -> None:
        composite = CompositeGate(
            gates=[
                _FixedOutcomeGate(PolicyOutcome.ALLOW, reason=""),
                _FixedOutcomeGate(PolicyOutcome.THROTTLE, reason="rate-warning"),
                _FixedOutcomeGate(PolicyOutcome.ALLOW, reason=""),
            ]
        )
        decision = await composite.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.THROTTLE

    @pytest.mark.asyncio
    async def test_deny_beats_throttle(self) -> None:
        composite = CompositeGate(
            gates=[
                _FixedOutcomeGate(PolicyOutcome.THROTTLE, reason="throttled"),
                _FixedOutcomeGate(PolicyOutcome.DENY, reason="denied"),
            ]
        )
        decision = await composite.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.DENY

    @pytest.mark.asyncio
    async def test_reasons_are_aggregated(self) -> None:
        composite = CompositeGate(
            gates=[
                _FixedOutcomeGate(PolicyOutcome.ALLOW, reason=""),
                _FixedOutcomeGate(PolicyOutcome.DENY, reason="reason-a"),
                _FixedOutcomeGate(PolicyOutcome.DENY, reason="reason-b"),
            ]
        )
        decision = await composite.evaluate(_make_request())
        assert "reason-a" in decision.reason
        assert "reason-b" in decision.reason

    @pytest.mark.asyncio
    async def test_empty_gates_returns_allow(self) -> None:
        composite = CompositeGate(gates=[])
        decision = await composite.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.ALLOW


# ---------------------------------------------------------------------------
# CompositeGate — observer
# ---------------------------------------------------------------------------


class TestCompositeGateObserver:
    @pytest.mark.asyncio
    async def test_observer_called_once_per_evaluate(self) -> None:
        observer = _RecordingObserver()
        composite = CompositeGate(
            gates=[AlwaysAllowGate()],
            observers=[observer],
        )
        request = _make_request()
        await composite.evaluate(request)
        assert len(observer.calls) == 1

    @pytest.mark.asyncio
    async def test_observer_receives_correct_request(self) -> None:
        observer = _RecordingObserver()
        composite = CompositeGate(
            gates=[AlwaysAllowGate()],
            observers=[observer],
        )
        request = _make_request(principal_id="abc", content_type="video")
        await composite.evaluate(request)
        observed_request, _ = observer.calls[0]
        assert observed_request.principal_id == "abc"
        assert observed_request.content_type == "video"

    @pytest.mark.asyncio
    async def test_observer_receives_final_decision(self) -> None:
        observer = _RecordingObserver()
        composite = CompositeGate(
            gates=[_FixedOutcomeGate(PolicyOutcome.DENY, reason="blocked")],
            observers=[observer],
        )
        await composite.evaluate(_make_request())
        _, observed_decision = observer.calls[0]
        assert observed_decision.outcome == PolicyOutcome.DENY

    @pytest.mark.asyncio
    async def test_multiple_observers_all_called(self) -> None:
        obs1 = _RecordingObserver()
        obs2 = _RecordingObserver()
        composite = CompositeGate(
            gates=[AlwaysAllowGate()],
            observers=[obs1, obs2],
        )
        await composite.evaluate(_make_request())
        assert len(obs1.calls) == 1
        assert len(obs2.calls) == 1


# ---------------------------------------------------------------------------
# CompositeGate — custom gate + AlwaysAllowGate
# ---------------------------------------------------------------------------


class TestMetadataDenyGateComposition:
    @pytest.mark.asyncio
    async def test_metadata_gate_deny_wins_over_always_allow(self) -> None:
        composite = CompositeGate(
            gates=[
                _MetadataDenyGate(key="species", value="bird"),
                AlwaysAllowGate(),
            ]
        )
        request = _make_request(metadata={"species": "bird"})
        decision = await composite.evaluate(request)
        assert decision.outcome == PolicyOutcome.DENY
        assert "bird" in decision.reason

    @pytest.mark.asyncio
    async def test_metadata_gate_allow_for_permitted_species(self) -> None:
        composite = CompositeGate(
            gates=[
                _MetadataDenyGate(key="species", value="bird"),
                AlwaysAllowGate(),
            ]
        )
        request = _make_request(metadata={"species": "dog"})
        decision = await composite.evaluate(request)
        assert decision.outcome == PolicyOutcome.ALLOW


# ---------------------------------------------------------------------------
# ContentPolicyService
# ---------------------------------------------------------------------------


class TestContentPolicyService:
    @pytest.mark.asyncio
    async def test_delegates_to_gate(self) -> None:
        gate = _FixedOutcomeGate(PolicyOutcome.ALLOW, reason="ok")
        service = ContentPolicyService(gate=gate)
        decision = await service.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.ALLOW

    @pytest.mark.asyncio
    async def test_deny_propagated(self) -> None:
        gate = _FixedOutcomeGate(PolicyOutcome.DENY, reason="blocked")
        service = ContentPolicyService(gate=gate)
        decision = await service.evaluate(_make_request())
        assert decision.outcome == PolicyOutcome.DENY

    @pytest.mark.asyncio
    async def test_service_observer_called(self) -> None:
        observer = _RecordingObserver()
        gate = AlwaysAllowGate()
        service = ContentPolicyService(gate=gate, observers=[observer])
        request = _make_request()
        await service.evaluate(request)
        assert len(observer.calls) == 1
        observed_request, observed_decision = observer.calls[0]
        assert observed_request is request
        assert observed_decision.outcome == PolicyOutcome.ALLOW

    @pytest.mark.asyncio
    async def test_is_allowed_true_for_allow(self) -> None:
        service = ContentPolicyService(gate=AlwaysAllowGate())
        decision = PolicyDecision(outcome=PolicyOutcome.ALLOW, reason="")
        assert service.is_allowed(decision) is True

    @pytest.mark.asyncio
    async def test_is_allowed_true_for_throttle(self) -> None:
        service = ContentPolicyService(gate=AlwaysAllowGate())
        decision = PolicyDecision(outcome=PolicyOutcome.THROTTLE, reason="warning")
        assert service.is_allowed(decision) is True

    @pytest.mark.asyncio
    async def test_is_allowed_false_for_deny(self) -> None:
        service = ContentPolicyService(gate=AlwaysAllowGate())
        decision = PolicyDecision(outcome=PolicyOutcome.DENY, reason="blocked")
        assert service.is_allowed(decision) is False


# ---------------------------------------------------------------------------
# PolicyRequest / PolicyDecision — frozen dataclass invariants
# ---------------------------------------------------------------------------


class TestModels:
    def test_policy_request_is_frozen(self) -> None:
        req = PolicyRequest(principal_id="u1", content_type="image")
        with pytest.raises(Exception):
            req.principal_id = "other"  # type: ignore[misc]

    def test_policy_decision_is_frozen(self) -> None:
        dec = PolicyDecision(outcome=PolicyOutcome.ALLOW, reason="")
        with pytest.raises(Exception):
            dec.outcome = PolicyOutcome.DENY  # type: ignore[misc]

    def test_policy_outcome_is_str_enum(self) -> None:
        assert PolicyOutcome.ALLOW == "allow"
        assert PolicyOutcome.DENY == "deny"
        assert PolicyOutcome.THROTTLE == "throttle"

    def test_policy_request_defaults(self) -> None:
        req = PolicyRequest(principal_id=None, content_type="text")
        assert req.content_metadata == {}
        assert req.history_summary is None
