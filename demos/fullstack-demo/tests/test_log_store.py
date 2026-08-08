from shorts_creator.services.log_store import LogStore


class TestLogStore:
    def test_push_and_recent(self):
        s = LogStore(max_entries=10)
        s.push("op1", "info", "hello")
        s.push("op2", "progress", "working")
        assert len(s.recent()) == 2
        assert s.recent()[0]["op_id"] == "op1"
        assert s.recent()[1]["message"] == "working"

    def test_max_entries_ring_buffer(self):
        s = LogStore(max_entries=3)
        for i in range(5):
            s.push("op", "info", f"msg{i}")
        assert len(s.recent()) == 3
        assert s.recent()[0]["message"] == "msg2"
        assert s.recent()[-1]["message"] == "msg4"

    def test_clear(self):
        s = LogStore(max_entries=10)
        s.push("op1", "info", "a")
        s.clear()
        assert s.recent() == []

    def test_recent_with_since(self):
        s = LogStore(max_entries=10)
        s.push("op1", "info", "before")
        import time

        time.sleep(0.01)
        ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        time.sleep(0.01)
        s.push("op2", "info", "after")
        filtered = s.recent(since=ts)
        assert len(filtered) == 1
        assert filtered[0]["message"] == "after"
