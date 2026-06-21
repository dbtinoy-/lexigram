"""XSS regression tests for the dashboard widget organisms (F3/F4).

ActivityFeed actor/resource/action/resource_id/icon, StatCard icon and
SystemHealthWidget latency/dot values all previously flowed through
``raw(f"...")`` interpolation or verbatim string children — every field
must now render escaped.
"""

from __future__ import annotations

from lexigram.admin.ui.organisms.dashboard.widgets import (
    ActivityFeed,
    ActivityItem,
    HealthEntry,
    Stat,
    StatCard,
    SystemHealthWidget,
)
from lexigram.ui import render_to_string

PAYLOAD = '<img src=x onerror="alert(1)">'
ESCAPED = '&lt;img src=x onerror="alert(1)"&gt;'


class TestActivityFeed:
    def test_actor_escaped(self) -> None:
        html = render_to_string(
            ActivityFeed(
                [ActivityItem(actor=PAYLOAD, action="created", resource="User")]
            )
        )
        assert PAYLOAD not in html
        assert ESCAPED in html

    def test_action_escaped(self) -> None:
        html = render_to_string(
            ActivityFeed([ActivityItem(actor="a", action=PAYLOAD, resource="User")])
        )
        assert PAYLOAD not in html
        assert ESCAPED in html

    def test_resource_escaped(self) -> None:
        html = render_to_string(
            ActivityFeed([ActivityItem(actor="a", action="created", resource=PAYLOAD)])
        )
        assert PAYLOAD not in html
        assert ESCAPED in html

    def test_resource_id_escaped(self) -> None:
        html = render_to_string(
            ActivityFeed(
                [
                    ActivityItem(
                        actor="a",
                        action="created",
                        resource="User",
                        resource_id=PAYLOAD,
                    )
                ]
            )
        )
        assert PAYLOAD not in html
        assert ESCAPED in html

    def test_icon_attribute_escaped(self) -> None:
        html = render_to_string(
            ActivityFeed(
                [
                    ActivityItem(
                        actor="a", action="created", resource="User", icon=PAYLOAD
                    )
                ]
            )
        )
        assert f'data-lucide="{PAYLOAD}"' not in html
        assert 'data-lucide="&lt;img' in html


class TestStatCard:
    def test_icon_attribute_escaped(self) -> None:
        html = render_to_string(StatCard(Stat(label="L", value="1", icon=PAYLOAD)))
        assert PAYLOAD not in html
        assert 'data-lucide="&lt;img' in html

    def test_value_and_label_escaped(self) -> None:
        html = render_to_string(StatCard(Stat(label=PAYLOAD, value=PAYLOAD)))
        assert PAYLOAD not in html
        assert ESCAPED in html


class TestSystemHealthWidget:
    def test_latency_escaped(self) -> None:
        html = render_to_string(
            SystemHealthWidget([HealthEntry(name="api", latency_ms=123)])
        )
        assert "123ms" in html

    def test_name_escaped(self) -> None:
        html = render_to_string(SystemHealthWidget([HealthEntry(name=PAYLOAD)]))
        assert PAYLOAD not in html
        assert ESCAPED in html

    def test_latency_ms_formatted_number_escaped(self) -> None:
        html = render_to_string(
            SystemHealthWidget([HealthEntry(name="api", latency_ms=-1)])
        )
        assert "-1ms" in html
