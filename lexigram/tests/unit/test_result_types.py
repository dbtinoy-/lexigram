"""Tests for Result types (Ok, Err, Result)."""

import pytest

from lexigram.result import Err, Ok, Result
from lexigram.result.errors import UnwrapError


class TestOk:
    """Tests for Ok result type."""

    def test_is_ok(self) -> None:
        """Test that Ok.is_ok() returns True."""
        result: Result[int, str] = Ok(42)
        assert result.is_ok() is True

    def test_is_err(self) -> None:
        """Test that Ok.is_err() returns False."""
        result: Result[int, str] = Ok(42)
        assert result.is_err() is False

    def test_unwrap(self) -> None:
        """Test unwrap returns the value."""
        result: Result[int, str] = Ok(42)
        assert result.unwrap() == 42

    def test_unwrap_err_raises(self) -> None:
        """Test that unwrap_err raises UnwrapError on Ok."""
        result: Result[int, str] = Ok(42)
        with pytest.raises(UnwrapError, match="Called unwrap_err"):
            result.unwrap_err()

    def test_unwrap_or_returns_value(self) -> None:
        """Test that unwrap_or returns the value, not default."""
        result: Result[int, str] = Ok(42)
        assert result.unwrap_or(0) == 42

    def test_unwrap_or_else_returns_value(self) -> None:
        """Test that unwrap_or_else returns value, not calling fn."""
        result: Result[int, str] = Ok(42)
        assert result.unwrap_or_else(lambda _e: 0) == 42

    def test_map(self) -> None:
        """Test map_sync transforms the value."""
        result: Result[int, str] = Ok(21)
        mapped = result.map_sync(lambda x: x * 2)
        assert mapped.unwrap() == 42

    def test_map_err_on_ok(self) -> None:
        """Test that map_err on Ok returns Ok unchanged."""
        result: Result[int, str] = Ok(42)
        mapped = result.map_err(lambda e: e.upper())
        assert mapped.is_ok()
        assert mapped.unwrap() == 42

    def test_and_then(self) -> None:
        """Test and_then_sync chains operations."""
        result: Result[int, str] = Ok(21)
        chained = result.and_then_sync(lambda x: Ok(x * 2))
        assert chained.unwrap() == 42

    def test_or_else_on_ok(self) -> None:
        """Test that or_else_sync on Ok returns Ok, not calling fn."""
        result: Result[int, str] = Ok(42)
        assert result.or_else_sync(lambda _e: Ok(0)).unwrap() == 42


class TestErr:
    """Tests for Err result type."""

    def test_is_ok(self) -> None:
        """Test that Err.is_ok() returns False."""
        result: Result[int, str] = Err("error")
        assert result.is_ok() is False

    def test_is_err(self) -> None:
        """Test that Err.is_err() returns True."""
        result: Result[int, str] = Err("error")
        assert result.is_err() is True

    def test_unwrap_raises(self) -> None:
        """Test that unwrap raises UnwrapError on Err."""
        result: Result[int, str] = Err("error")
        with pytest.raises(UnwrapError, match="error"):
            result.unwrap()

    def test_unwrap_err(self) -> None:
        """Test unwrap_err returns the error."""
        result: Result[int, str] = Err("error")
        assert result.unwrap_err() == "error"

    def test_unwrap_or_returns_default(self) -> None:
        """Test that unwrap_or returns default on Err."""
        result: Result[int, str] = Err("error")
        assert result.unwrap_or(42) == 42

    def test_unwrap_or_else_calls_fn(self) -> None:
        """Test that unwrap_or_else calls fn on Err."""
        result: Result[int, str] = Err("error")
        assert result.unwrap_or_else(len) == 5

    def test_map_on_err(self) -> None:
        """Test that map_sync on Err returns Err unchanged."""
        result: Result[int, str] = Err("error")
        mapped = result.map_sync(lambda x: x * 2)
        assert mapped.is_err()
        assert mapped.unwrap_err() == "error"

    def test_map_err(self) -> None:
        """Test map_err transforms the error."""
        result: Result[int, str] = Err("error")
        mapped = result.map_err(lambda e: e.upper())
        assert mapped.is_err()
        assert mapped.unwrap_err() == "ERROR"

    def test_and_then_on_err(self) -> None:
        """Test that and_then_sync on Err returns Err, not calling fn."""
        result: Result[int, str] = Err("error")
        assert result.and_then_sync(lambda x: Ok(x * 2)).is_err()

    def test_or_else(self) -> None:
        """Test or_else_sync on Err calls fn and returns new Result."""
        result: Result[int, str] = Err("error")
        recovered = result.or_else_sync(lambda _e: Ok(42))  # noqa: ARG005
        assert recovered.is_ok()
        assert recovered.unwrap() == 42


class TestResultFlatten:
    """Tests for Result.flatten()."""

    def test_flatten_nested_ok(self) -> None:
        """Test flattening nested Ok values."""
        outer: Result[Result[int, str], str] = Ok(Ok(42))
        flattened = outer.flatten()
        assert flattened.is_ok()
        assert flattened.unwrap() == 42

    def test_flatten_nested_err_in_ok(self) -> None:
        """Test flattening when Ok contains Err."""
        outer: Result[Result[int, str], str] = Ok(Err("inner"))
        flattened = outer.flatten()
        assert flattened.is_err()
        assert flattened.unwrap_err() == "inner"

    def test_flatten_outer_err(self) -> None:
        """Test flattening when outer is Err."""
        outer: Result[Result[int, str], str] = Err("outer")
        flattened = outer.flatten()
        assert flattened.is_err()
        assert flattened.unwrap_err() == "outer"

    def test_flatten_non_result_value(self) -> None:
        """Test flattening when value is not a Result."""
        outer: Result[int, str] = Ok(42)
        flattened = outer.flatten()
        assert flattened.is_ok()
        assert flattened.unwrap() == 42


class TestResultMatch:
    """Tests for Result.match() method."""

    def test_match_ok(self) -> None:
        """Test match on Ok."""
        result: Result[int, str] = Ok(42)
        message = result.match(
            ok=lambda v: f"Got: {v}",
            err=lambda e: f"Error: {e}",
        )
        assert message == "Got: 42"

    def test_match_err(self) -> None:
        """Test match on Err."""
        result: Result[int, str] = Err("error")
        message = result.match(
            ok=lambda v: f"Got: {v}",
            err=lambda e: f"Error: {e}",
        )
        assert message == "Error: error"


class TestOkAsyncMethods:
    """Tests for Ok async methods (canonical map/and_then/or_else)."""

    @pytest.mark.asyncio
    async def test_map(self) -> None:
        """Test map transforms the value asynchronously."""
        ok = Ok(21)

        async def double(x: int) -> int:
            return x * 2

        result = await ok.map(double)
        assert result.unwrap() == 42

    @pytest.mark.asyncio
    async def test_and_then(self) -> None:
        """Test and_then chains operations asynchronously."""
        ok = Ok(21)

        async def double(x: int) -> Result[int, str]:
            return Ok(x * 2)

        result = await ok.and_then(double)
        assert result.unwrap() == 42

    @pytest.mark.asyncio
    async def test_and_then_returns_err(self) -> None:
        """Test and_then can return Err."""
        ok = Ok(21)

        async def fail(_x: int) -> Result[int, str]:
            return Err("failed")

        result = await ok.and_then(fail)
        assert result.is_err()
        assert result.unwrap_err() == "failed"

    @pytest.mark.asyncio
    async def test_or_else_on_ok(self) -> None:
        """Test or_else on Ok returns self."""
        ok = Ok(42)

        async def fallback(_e: str) -> Result[int, str]:
            return Ok(0)

        result = await ok.or_else(fallback)
        assert result.unwrap() == 42


class TestErrAsyncMethods:
    """Tests for Err async methods (canonical map/and_then/or_else)."""

    @pytest.mark.asyncio
    async def test_map_on_err(self) -> None:
        """Test map on Err returns same Err."""
        err = Err("error")

        async def double(x: int) -> int:
            return x * 2

        result = await err.map(double)
        assert result.is_err()
        assert result.unwrap_err() == "error"

    @pytest.mark.asyncio
    async def test_and_then_on_err(self) -> None:
        """Test and_then on Err returns same Err."""
        err = Err("error")

        async def double(x: int) -> Result[int, str]:
            return Ok(x * 2)

        result = await err.and_then(double)
        assert result.is_err()
        assert result.unwrap_err() == "error"

    @pytest.mark.asyncio
    async def test_or_else(self) -> None:
        """Test or_else on Err calls function."""
        err = Err("error")

        async def recover(_e: str) -> Result[int, str]:
            return Ok(42)

        result = await err.or_else(recover)
        assert result.unwrap() == 42


class TestOkExpect:
    """Tests for Ok.expect()."""

    def test_expect_on_ok(self) -> None:
        """Test expect on Ok returns value."""
        ok: Result[int, str] = Ok(42)
        assert ok.expect("should not raise") == 42


class TestErrExpect:
    """Tests for Err.expect()."""

    def test_expect_raises_with_message(self) -> None:
        """Test expect on Err raises UnwrapError with custom message."""
        err: Result[int, str] = Err("error")
        with pytest.raises(UnwrapError, match="custom message"):
            err.expect("custom message")


class TestOkEquality:
    """Tests for Ok equality and hashing."""

    def test_eq_same_value(self) -> None:
        """Test Ok equality with same value."""
        assert Ok(42) == Ok(42)

    def test_eq_different_value(self) -> None:
        """Test Ok inequality with different value."""
        assert Ok(42) != Ok(100)

    def test_eq_different_type(self) -> None:
        """Test Ok != Err."""
        assert Ok(42) != Err(42)

    def test_hash_same_value(self) -> None:
        """Test hash equality for same value."""
        assert hash(Ok(42)) == hash(Ok(42))

    def test_can_use_in_set(self) -> None:
        """Test Ok can be used in set."""
        s = {Ok(1), Ok(2), Ok(1)}
        assert len(s) == 2


class TestErrEquality:
    """Tests for Err equality and hashing."""

    def test_eq_same_error(self) -> None:
        """Test Err equality with same error."""
        assert Err("error") == Err("error")

    def test_eq_different_error(self) -> None:
        """Test Err inequality with different error."""
        assert Err("error") != Err("different")

    def test_eq_different_type(self) -> None:
        """Test Err != Ok."""
        assert Err("error") != Ok("error")

    def test_hash_same_error(self) -> None:
        """Test hash equality for same error."""
        assert hash(Err("error")) == hash(Err("error"))


class TestOkRepr:
    """Tests for Ok repr."""

    def test_repr(self) -> None:
        """Test repr format."""
        assert repr(Ok(42)) == "Ok(42)"

    def test_repr_string(self) -> None:
        """Test repr with string value."""
        assert repr(Ok("test")) == "Ok('test')"


class TestErrRepr:
    """Tests for Err repr."""

    def test_repr(self) -> None:
        """Test repr format."""
        assert repr(Err("error")) == "Err('error')"


class TestErrUnwrapWithException:
    """Tests for Err containing exceptions."""

    def test_unwrap_propagates_exception(self) -> None:
        """Test unwrap on Err with exception raises UnwrapError."""
        err: Result[int, ValueError] = Err(ValueError("test error"))
        with pytest.raises(UnwrapError, match="Called unwrap"):
            err.unwrap()

    def test_unwrap_or_returns_default_for_exception(self) -> None:
        """Test unwrap_or returns default for Err with exception."""
        err: Result[int, ValueError] = Err(ValueError("test"))
        assert err.unwrap_or(42) == 42


class TestOkMapErrOnException:
    """Tests for map_err when Ok contains exception."""

    def test_map_err_preserves_ok_with_exception(self) -> None:
        """Test map_err on Ok preserves value."""
        ok: Result[int, ValueError] = Ok(42)
        result = ok.map_err(lambda e: RuntimeError(str(e)))
        assert result.is_ok()
        assert result.unwrap() == 42


class TestResultFilter:
    """Tests for Result.filter() combinator."""

    def test_ok_filter_passes(self) -> None:
        """Test filter returns Ok when predicate is true."""
        result: Result[int, str] = Ok(5)
        filtered = result.filter(lambda x: x > 0, "negative")
        assert filtered == Ok(5)

    def test_ok_filter_fails(self) -> None:
        """Test filter converts Ok to Err when predicate is false."""
        result: Result[int, str] = Ok(5)
        filtered = result.filter(lambda x: x > 10, "too small")
        assert filtered == Err("too small")

    def test_ok_filter_with_string(self) -> None:
        """Test filter with string value."""
        result: Result[str, str] = Ok("hello")
        filtered = result.filter(lambda s: len(s) > 3, "too short")
        assert filtered == Ok("hello")

    def test_ok_filter_empty_string(self) -> None:
        """Test filter converts empty string to Err."""
        result: Result[str, str] = Ok("hi")
        filtered = result.filter(lambda s: len(s) > 3, "too short")
        assert filtered == Err("too short")

    def test_err_filter_noop(self) -> None:
        """Test filter is no-op on Err."""
        result: Result[int, str] = Err("original")
        filtered = result.filter(lambda _x: True, "ignored")
        assert filtered == Err("original")

    def test_err_filter_noop_predicate_not_called(self) -> None:
        """Test filter predicate is not called on Err."""
        call_count = [0]

        def predicate(x: int) -> bool:
            call_count[0] += 1
            return True

        result: Result[int, str] = Err("original")
        _filtered = result.filter(predicate, "ignored")
        assert call_count[0] == 0

    def test_filter_chain(self) -> None:
        """Test chaining multiple filters."""
        result: Result[int, str] = Ok(5)
        filtered = result.filter(lambda x: x > 0, "negative").filter(
            lambda x: x < 10, "too large"
        )
        assert filtered == Ok(5)

    def test_filter_chain_fails_early(self) -> None:
        """Test chain stops at first filter failure."""
        result: Result[int, str] = Ok(15)
        filtered = result.filter(lambda x: x > 0, "negative").filter(
            lambda x: x < 10, "too large"
        )
        assert filtered == Err("too large")


class TestResultInspectErr:
    """Tests for Result.inspect_err() combinator."""

    def test_err_inspect_err_side_effect_called(self) -> None:
        """Test inspect_err calls side effect on Err."""
        errors: list[str] = []
        result: Result[str, ValueError] = Err(ValueError("bad"))
        result.inspect_err(lambda e: errors.append(str(e)))
        assert errors == ["bad"]

    def test_err_inspect_err_returns_self(self) -> None:
        """Test inspect_err returns the same Err unchanged."""
        result: Result[str, ValueError] = Err(ValueError("bad"))
        inspected = result.inspect_err(lambda _e: None)
        assert inspected == result

    def test_ok_inspect_err_side_effect_not_called(self) -> None:
        """Test inspect_err side effect is not called on Ok."""
        errors: list[str] = []
        result: Result[str, ValueError] = Ok("good")
        result.inspect_err(lambda e: errors.append(str(e)))
        assert errors == []

    def test_ok_inspect_err_returns_self(self) -> None:
        """Test inspect_err returns the same Ok unchanged."""
        result: Result[str, ValueError] = Ok("good")
        inspected = result.inspect_err(lambda _e: None)
        assert inspected == result

    def test_err_inspect_err_chain(self) -> None:
        """Test chaining inspect_err with other operations."""
        errors: list[str] = []

        result: Result[str, str] = Err("first error")
        chained = result.inspect_err(errors.append).map_err(lambda e: e.upper())

        assert errors == ["first error"]
        assert chained == Err("FIRST ERROR")

    def test_inspect_err_with_complex_operation(self) -> None:
        """Test inspect_err with a more complex side effect."""
        logs: dict[str, int] = {"count": 0, "sum": 0}

        result: Result[int, int] = Err(42)
        result.inspect_err(
            lambda e: logs.update({"count": logs["count"] + 1, "sum": logs["sum"] + e})
        )

        assert logs["count"] == 1
        assert logs["sum"] == 42


class TestResultOkOr:
    """Tests for Result.ok_or() accessor."""

    def test_ok_returns_value(self) -> None:
        """Test ok_or returns Ok value, ignoring default."""
        result: Result[int, str] = Ok(42)
        assert result.ok_or(0) == 42

    def test_err_returns_default(self) -> None:
        """Test ok_or returns default on Err."""
        result: Result[int, str] = Err("oops")
        assert result.ok_or(0) == 0

    def test_ok_or_with_string(self) -> None:
        """Test ok_or with string values."""
        result: Result[str, str] = Ok("hello")
        assert result.ok_or("default") == "hello"

    def test_ok_or_with_err_returns_default_string(self) -> None:
        """Test ok_or with string error returns default."""
        result: Result[str, str] = Err("error")
        assert result.ok_or("default") == "default"

    def test_ok_or_with_none(self) -> None:
        """Test ok_or with None as default."""
        result: Result[int, str] = Err("error")
        assert result.ok_or(None) is None

    def test_ok_or_preserves_ok_type(self) -> None:
        """Test ok_or preserves the Ok type."""
        result: Result[list[int], str] = Ok([1, 2, 3])
        value = result.ok_or([])
        assert value == [1, 2, 3]
        assert isinstance(value, list)


class TestResultAsyncMapAlias:
    """Tests for Result.async_map alias."""

    @pytest.mark.asyncio
    async def test_async_map_ok(self) -> None:
        """Test async_map alias works on Ok."""
        ok = Ok(21)

        async def double(x: int) -> int:
            return x * 2

        result = await ok.async_map(double)
        assert result.unwrap() == 42

    @pytest.mark.asyncio
    async def test_async_map_err(self) -> None:
        """Test async_map alias works on Err."""
        err = Err("error")

        async def double(x: int) -> int:
            return x * 2

        result = await err.async_map(double)
        assert result.is_err()
        assert result.unwrap_err() == "error"

    @pytest.mark.asyncio
    async def test_async_map_is_same_as_map(self) -> None:
        """Test async_map is the same as map."""
        ok = Ok(21)

        async def double(x: int) -> int:
            return x * 2

        result1 = await ok.map(double)
        result2 = await ok.async_map(double)
        assert result1 == result2


class TestResultCombinatorsIntegration:
    """Integration tests combining multiple new combinators."""

    def test_filter_and_inspect_err(self) -> None:
        """Test filter followed by inspect_err."""
        errors: list[str] = []

        result: Result[int, str] = Ok(5)
        filtered = result.filter(lambda x: x > 10, "too small").inspect_err(
            lambda e: errors.append(f"Error: {e}")
        )

        assert filtered.is_err()
        assert errors == ["Error: too small"]

    def test_filter_ok_or_pattern(self) -> None:
        """Test filter followed by ok_or for safe extraction."""
        result: Result[int, str] = Ok(5)
        filtered = result.filter(lambda x: x > 0, "negative")
        value = filtered.ok_or(0)
        assert value == 5

    def test_filter_ok_or_err_pattern(self) -> None:
        """Test filter followed by ok_or with error path."""
        result: Result[int, str] = Ok(-5)
        filtered = result.filter(lambda x: x > 0, "negative")
        value = filtered.ok_or(0)
        assert value == 0

    @pytest.mark.asyncio
    async def test_filter_and_async_map(self) -> None:
        """Test filter followed by async_map."""

        async def fetch_double(x: int) -> int:
            return x * 2

        result: Result[int, str] = Ok(5)
        processed = await result.filter(lambda x: x > 0, "negative").async_map(
            fetch_double
        )

        assert processed.unwrap() == 10

    def test_inspect_and_filter_chain(self) -> None:
        """Test inspect followed by filter."""
        logs: list[str] = []

        result: Result[int, str] = Ok(5)
        processed = (
            result.inspect(lambda x: logs.append(f"Original: {x}"))
            .filter(lambda x: x > 0, "negative")
            .inspect(lambda x: logs.append(f"After filter: {x}"))
        )

        assert processed.is_ok()
        assert logs == ["Original: 5", "After filter: 5"]


class TestResultFromException:
    """Tests for Result.from_exception() class method."""

    def test_from_exception_returns_err(self) -> None:
        """Test from_exception wraps exception in Err."""
        result = Result.from_exception(ValueError("test error"))
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_from_exception_with_string_error(self) -> None:
        """Test from_exception with string error type."""
        result = Result.from_exception(RuntimeError("runtime failed"))
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RuntimeError)
        assert str(err) == "runtime failed"

    def test_from_exception_preserves_exception_message(self) -> None:
        """Test from_exception preserves exception message."""
        result = Result.from_exception(KeyError("missing key"))
        err = result.unwrap_err()
        assert isinstance(err, KeyError)

    def test_from_exception_type_inference(self) -> None:
        """Test from_exception type inference works."""
        result: Result[int, Exception] = Result.from_exception(ValueError("test"))
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_from_exception_ok_type_parameter(self) -> None:
        """Test from_exception ok_type parameter is accepted."""
        result = Result.from_exception(OSError("io failed"), ok_type=int)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), OSError)


class TestOkInspectSideEffects:
    """Tests for Ok.inspect() side effects."""

    def test_inspect_calls_side_effect(self) -> None:
        """Test inspect calls side effect with Ok value."""
        calls: list[int] = []

        result: Result[int, str] = Ok(42)
        result.inspect(calls.append)

        assert calls == [42]

    def test_inspect_returns_self(self) -> None:
        """Test inspect returns same Ok instance."""
        result: Result[int, str] = Ok(42)
        inspected = result.inspect(lambda _x: None)

        assert inspected is result

    def test_inspect_chaining(self) -> None:
        """Test chaining inspect with other operations."""
        results: list[str] = []

        result: Result[int, str] = Ok(5)
        result = result.inspect(lambda x: results.append(f"got {x}"))
        result = result.map_sync(lambda x: x * 2)
        result = result.inspect(lambda x: results.append(f"mapped {x}"))

        assert result.unwrap() == 10
        assert results == ["got 5", "mapped 10"]


class TestOkAsyncMap:
    """Tests for Ok.async_map method alias."""

    @pytest.mark.asyncio
    async def test_async_map_alias_works(self) -> None:
        """Test async_map is an alias for map."""
        ok = Ok(10)

        async def transform(x: int) -> int:
            return x + 5

        result = await ok.async_map(transform)
        assert result.unwrap() == 15

    @pytest.mark.asyncio
    async def test_async_map_on_err_returns_err(self) -> None:
        """Test async_map alias on Err returns Err."""
        err = Err("error")

        async def transform(x: int) -> int:
            return x * 2

        result = await err.async_map(transform)
        assert result.is_err()
        assert result.unwrap_err() == "error"


class TestErrAsyncMap:
    """Tests for Err.async_map method alias."""

    @pytest.mark.asyncio
    async def test_async_map_alias_on_err(self) -> None:
        """Test async_map alias preserves Err."""
        err = Err("failure")

        async def transform(x: int) -> int:
            return x * 2

        result = await err.async_map(transform)
        assert result.is_err()
        assert result.unwrap_err() == "failure"
