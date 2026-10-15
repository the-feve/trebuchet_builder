"""Order Trebuchet Supplies (/supplies) and the report's shopping links."""

from fastapi.testclient import TestClient

import treb_supplies
from app import app
from trebgen.build import plan
from trebgen.hardware import bill_of_materials
from trebgen.params import DesignParams

client = TestClient(app)
STORE = "tag=quiverdesig09-20"


def test_page_has_affiliate_links_and_disclosure():
    r = client.get("/supplies")
    assert r.status_code == 200
    assert r.text.count(treb_supplies.DISCLOSURE) >= 2  # top and bottom
    assert STORE in r.text and 'rel="sponsored noopener"' in r.text
    assert "Rocket Builder" in r.text and "Trebuchet Builder" in r.text


def test_every_link_carries_the_store_id():
    for links in treb_supplies.links_by_key().values():
        for l in links:
            assert STORE in l["url"] and l["url"].startswith("https://www.amazon.com/")


def test_default_shopping_list_items_have_links():
    """Everything the default design needs to buy has somewhere to buy it."""
    pl = plan(DesignParams())
    keys = {i["key"] for i in bill_of_materials(pl.params, pl.derived, pl.pin_angle)}
    links = treb_supplies.links_by_key()
    assert keys - set(links) == set(), keys - set(links)


def test_starter_kit_refers_to_real_items():
    ids = treb_supplies._by_id()
    for k in treb_supplies.gear()["starterKit"]["items"]:
        assert k["ref"] in ids


def test_options_carry_links_for_the_report():
    o = client.get("/api/options").json()
    assert "608_bearing" in o["supply_links"] and o["disclosure"] == treb_supplies.DISCLOSURE
