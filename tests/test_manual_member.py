"""Offline tests for manually-added group members.

The owner can add a friend by hand (name + airports) instead of waiting for an
invite. Such members get a synthetic `manual_` telegram id: they count as a
search participant but are never messaged. No network, temp DB.

Run:  python -m pytest tests/test_manual_member.py -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.utils.compat  # noqa

from src.core.storage import Storage
from telegram_bot import _is_manual, _member_name, _MANUAL_PREFIX


def test_is_manual_prefix():
    assert _is_manual("manual_abcd1234")
    assert not _is_manual("123456789")
    assert not _is_manual("")


def test_member_name_prefers_label():
    # Real member: label present -> used.
    assert _member_name({"label": "oussama", "username": "oussama",
                         "telegram_id": "111"}) == "oussama"
    # Manual member: no users row so username falls back to the id; label wins.
    assert _member_name({"label": "Gorgi", "username": "manual_x",
                         "telegram_id": "manual_x"}) == "Gorgi"


def test_manual_member_counts_and_removes(tmp_path):
    s = Storage(db_path=str(tmp_path / "m.db"))
    g = s.create_group("two nerds trip", "111")
    gid = g["id"]
    s.join_group(gid, "111", "oussama", ["BGY", "MXP", "LIN"])

    # Owner adds a friend by hand.
    mid = _MANUAL_PREFIX + "abcd1234"
    s.join_group(gid, mid, "Gorgi", ["VIE"])

    members = s.get_group_members(gid)
    assert len(members) == 2, "manual friend should count toward the group"

    manual = [m for m in members if _is_manual(m["telegram_id"])]
    assert len(manual) == 1
    assert _member_name(manual[0]) == "Gorgi"
    assert manual[0]["origins"] == ["VIE"]

    # Participant labels used by the search resolve to real names, not ids.
    labels = sorted(_member_name(m) for m in members)
    assert labels == ["Gorgi", "oussama"]

    # Removing the manual member works and drops the count.
    assert s.leave_group(gid, mid) is True
    assert len(s.get_group_members(gid)) == 1
