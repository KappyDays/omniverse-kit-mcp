# kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/tests/test_metadata_store.py
"""Unit tests for metadata_store — whitelist + descriptions persistence and lookup.

Tests run with plain pytest (no Kit). pxr.Usd / Sdf used directly via venv.
"""

from __future__ import annotations

import pytest
from pxr import Sdf, Usd, UsdGeom, Vt


# Imported lazily inside tests to avoid circular paths during initial setup.
def _import_module():
    from omni.mycompany.usd_mouse_interact import metadata_store
    return metadata_store


@pytest.fixture
def empty_stage():
    """In-memory USD stage with a single root /World Xform."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")
    return stage


@pytest.fixture
def populated_stage():
    """Stage with a Mesh prim under /World/Container."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Container")
    UsdGeom.Mesh.Define(stage, "/World/Container/Box_03")
    return stage


# --- whitelist matching ----------------------------------------------------

class TestIsWhitelisted:
    def test_empty_set_never_matches(self):
        m = _import_module()
        assert m.is_whitelisted("/World/Robot", set()) is False

    def test_exact_match(self):
        m = _import_module()
        assert m.is_whitelisted("/A", {"/A"}) is True

    def test_descendant_match(self):
        m = _import_module()
        assert m.is_whitelisted("/A/B/C", {"/A"}) is True

    def test_unrelated_prim(self):
        m = _import_module()
        assert m.is_whitelisted("/Z", {"/A"}) is False

    def test_prefix_trap_not_a_descendant(self):
        """`/AB` is NOT a descendant of `/A` — needs slash boundary."""
        m = _import_module()
        assert m.is_whitelisted("/AB", {"/A"}) is False

    def test_non_ascii_path(self):
        m = _import_module()
        assert m.is_whitelisted("/World/로봇", {"/World/로봇"}) is True


# --- description lookup ----------------------------------------------------

class TestLookupDescription:
    def test_user_text_exact(self, populated_stage):
        m = _import_module()
        descs = {"/World/Container/Box_03": "EUR-pallet"}
        title, desc = m.lookup_description("/World/Container/Box_03", descs, populated_stage)
        assert title == "Box_03"
        assert desc == "EUR-pallet"

    def test_user_text_ancestor(self, populated_stage):
        m = _import_module()
        descs = {"/World/Container": "container area"}
        title, desc = m.lookup_description("/World/Container/Box_03", descs, populated_stage)
        assert title == "Box_03"
        assert desc == "container area"

    def test_longest_ancestor_wins(self, populated_stage):
        m = _import_module()
        descs = {"/World": "world", "/World/Container": "container"}
        title, desc = m.lookup_description("/World/Container/Box_03", descs, populated_stage)
        assert desc == "container"  # not "world"

    def test_metadata_fallback_known_prim(self, populated_stage):
        m = _import_module()
        title, desc = m.lookup_description("/World/Container/Box_03", {}, populated_stage)
        assert title == "Box_03"
        assert "Mesh" in desc
        assert "/World/Container" in desc

    def test_metadata_fallback_invalid_prim(self, populated_stage):
        m = _import_module()
        title, desc = m.lookup_description("/Nonexistent/Prim", {}, populated_stage)
        assert title == "Prim"
        assert desc == "(unknown prim)"


# --- customLayerData round-trip --------------------------------------------

class TestCustomLayerDataRoundTrip:
    def test_load_from_empty_stage(self, empty_stage):
        m = _import_module()
        allowed, descs = m.load_from_stage(empty_stage)
        assert allowed == set()
        assert descs == {}

    def test_save_and_load_roundtrip(self, empty_stage):
        m = _import_module()
        m.save_to_stage(empty_stage, {"/World/Robot", "/World/Pallet"}, {"/World/Robot": "Franka"})
        allowed, descs = m.load_from_stage(empty_stage)
        assert allowed == {"/World/Robot", "/World/Pallet"}
        assert descs == {"/World/Robot": "Franka"}

    def test_save_overrides_existing(self, empty_stage):
        m = _import_module()
        m.save_to_stage(empty_stage, {"/A"}, {})
        m.save_to_stage(empty_stage, {"/B"}, {})
        allowed, descs = m.load_from_stage(empty_stage)
        assert allowed == {"/B"}
        assert descs == {}

    def test_save_unicode_description(self, empty_stage):
        m = _import_module()
        m.save_to_stage(empty_stage, {"/A"}, {"/A": "한국어 설명"})
        _, descs = m.load_from_stage(empty_stage)
        assert descs == {"/A": "한국어 설명"}
