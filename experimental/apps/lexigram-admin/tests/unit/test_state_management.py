"""Unit tests for the State Management System (Phase 4)."""

from lexigram.admin.state.persistence import (
    DictionaryStorage,
    PersistedSignal,
    StatePersistenceManager,
)
from lexigram.admin.state.store import computed, signal, watch
from lexigram.admin.state.url_sync import URLStateManager


class TestSignals:
    def test_basic_reactivity(self):
        count = signal(0)
        double = computed(lambda: count.get() * 2)

        # Track double in a watcher
        log = []
        watch(lambda: log.append(double.get()))

        assert log == [0]

        count.set(1)
        assert double.get() == 2
        assert log == [0, 2]

        count.set(5)
        assert double.get() == 10
        assert log == [0, 2, 10]

    def test_dependency_tracking(self):
        a = signal(1)
        b = signal(2)
        use_a = signal(True)

        calc = computed(lambda: a.get() if use_a.get() else b.get())

        assert calc.get() == 1

        # If we change b, calc should NOT update (not a dependency currenty)
        b.set(10)
        assert calc.get() == 1

        # Switch to b
        use_a.set(False)
        assert calc.get() == 10

        # Now changing a should NOT update calc
        a.set(100)
        assert calc.get() == 10


class TestURLSync:
    def test_serialization(self):
        manager = URLStateManager()
        state = {"filter": "active", "page": 1, "tags": ["admin", "staff"]}

        qs = manager.serialize(state)
        assert "filter=active" in qs
        assert "page=1" in qs
        assert "tags=admin" in qs
        assert "tags=staff" in qs

    def test_deserialization(self):
        manager = URLStateManager()
        # Test with BOTH bloated (repair) and clean formats
        qs_bloated = "?tags=%5B%22user%22%5D&active=true"
        state = manager.deserialize(qs_bloated)
        assert state["tags"] == "user"  # Flattened if single internal val
        assert state["active"] is True

        qs_clean = "?tags=user1&tags=user2"
        state = manager.deserialize(qs_clean)
        assert state["tags"] == ["user1", "user2"]


class TestPersistence:
    def test_persistence_manager(self):
        storage = DictionaryStorage()
        manager = StatePersistenceManager(storage)

        active_tab = signal("basic")
        manager.persist("admin_tab", active_tab)

        # Initial save
        assert storage.get("admin_tab") == '"basic"'

        active_tab.set("advanced")
        assert storage.get("admin_tab") == '"advanced"'

        # Reloading in another signal
        new_tab = signal("basic")
        manager.persist("admin_tab", new_tab)
        assert new_tab.get() == "advanced"

    def test_persisted_signal_class(self):
        storage = DictionaryStorage({"theme": '"dark"'})
        theme = PersistedSignal("theme", "light", storage)

        assert theme.get() == "dark"

        theme.set("system")
        assert storage.get("theme") == '"system"'
