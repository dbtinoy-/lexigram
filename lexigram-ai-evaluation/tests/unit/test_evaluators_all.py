"""Unit tests for all evaluators."""

from lexigram.ai.evaluation.evaluators import (
    CriteriaEvaluator,
    EmbeddingDistanceEvaluator,
    QAEvaluator,
    StringDistanceEvaluator,
    TrajectoryEvaluator,
)


class TestEvaluatorRegistry:
    """Tests for evaluator registry."""

    def test_criteria_evaluator_registered(self) -> None:
        """Test criteria evaluator can be instantiated."""
        evaluator = CriteriaEvaluator(criteria=["accuracy"])
        assert evaluator is not None
        assert evaluator.name == "criteria"

    def test_embedding_distance_evaluator_registered(self) -> None:
        """Test embedding distance evaluator can be instantiated."""
        evaluator = EmbeddingDistanceEvaluator()
        assert evaluator is not None
        assert evaluator.name == "embedding_distance"

    def test_qa_evaluator_registered(self) -> None:
        """Test QA evaluator can be instantiated."""
        evaluator = QAEvaluator()
        assert evaluator is not None
        assert evaluator.name == "qa"

    def test_string_distance_evaluator_registered(self) -> None:
        """Test string distance evaluator can be instantiated."""
        evaluator = StringDistanceEvaluator()
        assert evaluator is not None
        assert evaluator.name == "string_distance"

    def test_trajectory_evaluator_registered(self) -> None:
        """Test trajectory evaluator can be instantiated."""
        evaluator = TrajectoryEvaluator()
        assert evaluator is not None
        assert evaluator.name == "trajectory"

    def test_all_evaluators_have_names(self) -> None:
        """Test all evaluators have name property."""
        evaluators = [
            CriteriaEvaluator(criteria=["test"]),
            EmbeddingDistanceEvaluator(),
            QAEvaluator(),
            StringDistanceEvaluator(),
            TrajectoryEvaluator(),
        ]
        for eval in evaluators:
            assert hasattr(eval, "name")
            assert isinstance(eval.name, str)
            assert len(eval.name) > 0