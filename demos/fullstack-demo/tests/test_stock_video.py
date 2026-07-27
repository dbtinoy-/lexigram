from shorts_creator.pipeline import stock_video


class TestQueryForLine:
    def test_stress_line_selects_calm_query(self):
        pool = ["calm pool", "sunrise pool", "ocean pool", "meditation pool"]
        assert stock_video.query_for_line("I feel stressed and anxious", pool) == "calm pool"

    def test_energy_discipline_line_selects_sunrise(self):
        pool = ["calm pool", "sunrise pool", "ocean pool", "meditation pool"]
        assert stock_video.query_for_line("discipline and raw energy", pool) == "sunrise pool"

    def test_rest_peace_line_selects_meditation(self):
        pool = ["calm pool", "sunrise pool", "meditation pool"]
        assert stock_video.query_for_line("find rest and peace", pool) == "meditation pool"

    def test_default_line_random_from_pool(self):
        pool = ["one", "two", "three"]
        results = {stock_video.query_for_line("plain line", pool) for _ in range(60)}
        assert results <= set(pool)
        assert len(results) > 1

    def test_falls_back_to_default_queries(self):
        assert stock_video.query_for_line("plain line") in stock_video.DEFAULT_QUERIES

    def test_calm_keyword_matches_default_pool(self):
        assert stock_video.query_for_line("anxious stress") in {
            "calming nature forest river",
            "peaceful waterfall stream",
        }

    def test_deterministic_per_line(self):
        pool = ["calm pool", "sunrise pool", "ocean pool", "meditation pool"]
        first = stock_video.query_for_line("discipline and energy", pool)
        assert first == stock_video.query_for_line("discipline and energy", pool)


class TestStockVideoApiKeys:
    async def test_no_keys_returns_false_without_network(self, monkeypatch):
        monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)

        async def _boom(*args, **kwargs):
            raise AssertionError("must not search without providers")

        monkeypatch.setattr(stock_video, "_pixabay_search", _boom)
        monkeypatch.setattr(stock_video, "_pexels_search", _boom)
        assert await stock_video.fetch_background_video("q", "/tmp/out.mp4", 5) is False

    async def test_api_keys_param_wins_over_env(self, monkeypatch):
        seen = {}

        async def _fake_pixabay(query, key, category):
            seen["key"] = key

        monkeypatch.setattr(stock_video, "_pixabay_search", _fake_pixabay)
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)
        monkeypatch.setenv("PIXABAY_API_KEY", "env-key")
        ok = await stock_video.fetch_background_video(
            "q", "/tmp/out.mp4", 5, api_keys={"pixabay_api_key": "stored-key"}
        )
        assert ok is False
        assert seen["key"] == "stored-key"

    async def test_env_fallback_when_not_stored(self, monkeypatch):
        seen = {}

        async def _fake_pexels(query, key):
            seen["key"] = key

        monkeypatch.setattr(stock_video, "_pexels_search", _fake_pexels)
        monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)
        monkeypatch.setenv("PEXELS_API_KEY", "env-key")
        ok = await stock_video.fetch_background_video(
            "q", "/tmp/out.mp4", 5, api_keys={"pixabay_api_key": "stored-key"}
        )
        assert ok is False
        assert seen["key"] == "env-key"

    async def test_pinned_provider_used_when_configured(self, monkeypatch):
        seen = {}

        async def _fake_pixabay(query, key, category):
            seen["provider"] = "pixabay"

        async def _fake_pexels(query, key):
            seen["provider"] = "pexels"

        monkeypatch.setattr(stock_video, "_pixabay_search", _fake_pixabay)
        monkeypatch.setattr(stock_video, "_pexels_search", _fake_pexels)
        monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)
        ok = await stock_video.fetch_background_video(
            "q",
            "/tmp/out.mp4",
            5,
            api_keys={"pixabay_api_key": "pb-1", "pexels_api_key": "px-2"},
            provider="pexels",
        )
        assert ok is False
        assert seen["provider"] == "pexels"

    async def test_pinned_provider_without_key_falls_back_to_configured(self, monkeypatch):
        seen = []

        async def _fake_pixabay(query, key, category):
            seen.append("pixabay")

        async def _fake_pexels(query, key):
            seen.append("pexels")

        monkeypatch.setattr(stock_video, "_pixabay_search", _fake_pixabay)
        monkeypatch.setattr(stock_video, "_pexels_search", _fake_pexels)
        monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)
        ok = await stock_video.fetch_background_video(
            "q",
            "/tmp/out.mp4",
            5,
            api_keys={"pixabay_api_key": "pb-1"},
            provider="pexels",
        )
        assert ok is False
        assert seen == ["pixabay"]
