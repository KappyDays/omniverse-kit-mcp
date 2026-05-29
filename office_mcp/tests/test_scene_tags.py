"""Unit tests for scene_tags.organize / SceneTags (Kit-free)."""

from omni.office_mcp.network_demo import scene_tags as st
from omni.office_mcp.network_demo.scene_tags import TaggedPrim


def _full_set():
    # Deliberately unsorted to prove organize() sorts by order.
    return [
        TaggedPrim("/W/Cable/Seg2", st.ROLE_CABLE, 2),
        TaggedPrim("/W/Cable/Seg0", st.ROLE_CABLE, 0),
        TaggedPrim("/W/PC/PowerButton", st.ROLE_TRIGGER, 0),
        TaggedPrim("/W/Cable/Seg3", st.ROLE_CABLE, 3),
        TaggedPrim("/W/DC/Switch", st.ROLE_SWITCH, None),
        TaggedPrim("/W/DC/Server3/LED", st.ROLE_SERVER_LED, 3),
        TaggedPrim("/W/Cable/Seg1", st.ROLE_CABLE, 1),
        TaggedPrim("/W/DC/Server1/LED", st.ROLE_SERVER_LED, 1),
        TaggedPrim("/W/DC/Server2/LED", st.ROLE_SERVER_LED, 2),
    ]


def test_organize_groups_and_sorts_by_order():
    tags = st.organize(_full_set())
    assert tags.trigger == "/W/PC/PowerButton"
    assert tags.switch == "/W/DC/Switch"
    assert [c.order for c in tags.cables] == [0, 1, 2, 3]
    assert [s.order for s in tags.server_leds] == [1, 2, 3]
    assert tags.cable_paths == (
        "/W/Cable/Seg0", "/W/Cable/Seg1", "/W/Cable/Seg2", "/W/Cable/Seg3",
    )
    assert tags.server_led_orders == (1, 2, 3)


def test_organize_ok_and_missing_complete():
    tags = st.organize(_full_set())
    assert tags.ok is True
    assert tags.missing() == []


def test_missing_reports_absent_roles():
    tags = st.organize([TaggedPrim("/W/DC/Switch", st.ROLE_SWITCH, None)])
    assert tags.ok is False
    assert set(tags.missing()) == {st.ROLE_TRIGGER, st.ROLE_CABLE, st.ROLE_SERVER_LED}


def test_first_trigger_wins():
    tags = st.organize([
        TaggedPrim("/W/A", st.ROLE_TRIGGER, 0),
        TaggedPrim("/W/B", st.ROLE_TRIGGER, 0),
    ])
    assert tags.trigger == "/W/A"


def test_none_order_sorts_as_zero_without_raising():
    tags = st.organize([
        TaggedPrim("/W/PC/PowerButton", st.ROLE_TRIGGER, 0),
        TaggedPrim("/W/Cable/A", st.ROLE_CABLE, None),
        TaggedPrim("/W/Cable/B", st.ROLE_CABLE, 1),
        TaggedPrim("/W/DC/S/LED", st.ROLE_SERVER_LED, 1),
    ])
    # order None -> 0, so it sorts before order 1.
    assert tags.cables[0].path == "/W/Cable/A"
    assert tags.cables[1].path == "/W/Cable/B"
