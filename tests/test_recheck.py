"""The recheck/correct flow persists fresh data into the stored result:
same row id, corrected prices, and previously-missing fields filled in.

Run:  python -m pytest tests/test_recheck.py -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.utils.compat  # noqa

from src.core.storage import Storage
from src.core.scoring import GroupMeetupResult, ParticipantFlight


def _result(price_you, price_sara, grand, **kw):
    return GroupMeetupResult(
        destination="VIE", outbound_date="2026-08-03", return_date="2026-08-06",
        participants=[
            ParticipantFlight(label="You", origin="BGY", price=price_you, stops=0,
                              **kw),
            ParticipantFlight(label="Sara", origin="RIX", price=price_sara, stops=1),
        ],
        total_price=price_you + price_sara, grand_total=grand,
        transfer_cost=24, bag_cost=18, nights=3,
        flight_airlines="FR", flight_numbers="FR1", confidence_label="HIGH",
    )


def test_recheck_overwrites_row_and_fills_missing(tmp_path):
    s = Storage(db_path=str(tmp_path / "t.db"))
    # Original saved result: no departure times (old-style row).
    s.save_group_result("sid1", _result(60, 40, 142))
    rows = s.get_search_results("sid1")
    assert len(rows) == 1
    rid = rows[0]["id"]
    assert rows[0]["participants"][0].get("departure_time", "") == ""  # missing

    # Fresh recheck: cheaper, and now carries departure time.
    fresh = _result(50, 30, 118, departure_time="2026-08-03 12:20",
                    arrival_time="2026-08-03 13:45")
    s.update_group_result(rid, fresh)

    updated = s.get_result(rid)
    assert updated["id"] == rid                       # same row, not a new one
    assert abs(updated["grand_total"] - 118) < 0.01   # price corrected
    assert updated["participants"][0]["price"] == 50
    assert updated["participants"][0]["departure_time"] == "2026-08-03 12:20"  # filled

    # Still exactly one row for the search (updated in place, not appended).
    assert len(s.get_search_results("sid1")) == 1


def test_purge_city_duplicates_never_crosses_searches(tmp_path):
    """Regression: a search's cleanup must not delete another search's rows.
    Previously the purge was global and wiped other groups' results."""
    s = Storage(db_path=str(tmp_path / "t.db"))
    # Search A: one Vienna deal.
    s.save_group_result("A", _result(50, 50, 100))
    # Search B: two Vienna deals on different dates (a duplicate city in B).
    b1 = _result(100, 100, 200)
    b1.outbound_date, b1.return_date = "2026-08-01", "2026-08-04"
    b2 = _result(70, 80, 150)
    b2.outbound_date, b2.return_date = "2026-08-10", "2026-08-13"
    s.save_group_result("B", b1)
    s.save_group_result("B", b2)

    deleted = s.purge_city_duplicates(search_id="B")
    assert deleted == 1                              # only B's duplicate removed
    assert len(s.get_search_results("A")) == 1       # A completely untouched
    assert len(s.get_search_results("B")) == 1       # B deduped to cheapest
    assert abs(s.get_search_results("B")[0]["grand_total"] - 150) < 0.01
