from __future__ import annotations

from crawler import classify, india
from crawler.config import REPO_DIR


def test_gstin_checksum_state_and_pan():
    assert india.gstin("27aapfu0939f1zv") == "27AAPFU0939F1ZV"  # published sample GSTIN
    assert india.gstin("27AAPFU0939F1ZW") is None  # wrong check character
    assert india.gstin("99AAPFU0939F1ZV") is None  # no such state code
    assert india.gstin_state("09AABCS1234A1ZZ") == "Uttar Pradesh"
    assert india.pan_from_gstin("09AABCS1234A1ZZ") == "AABCS1234A"


def test_cin_carries_industry_code_and_state():
    info = india.cin("U12002UP2005PTC030001")
    assert (info.nic_code, info.state, info.year) == ("12002", "Uttar Pradesh", 2005)
    assert (info.company_type, info.listed) == ("PTC", False)
    assert india.cin("L16004KA1910PLC000001").state == "Karnataka"
    assert india.cin("U12002XX2005PTC03000") is None


def test_phones_emails_websites():
    assert india.phone("0821-2345678") == "+91 821 234 5678"
    assert india.phone("98300 12345 / 98300 54321") == "+91 98300 12345"
    assert india.phone("12345") is None
    assert india.phone_key("+91 98300 12345") == "+919830012345"
    assert india.email("Mail: SALES@Example.CO.IN.") == "sales@example.co.in"
    assert india.website_from_email("sales@sharmabidi.example") == "https://sharmabidi.example"
    assert india.website_from_email("someone@gmail.com") is None
    assert india.registrable_domain("https://www.shop.kaveri.co.in/contact") == "kaveri.co.in"


def test_states_regions_and_pins():
    assert india.state_in_text("21 Industrial Area, Mysuru, Karnataka - 570016") == "Karnataka"
    assert india.state_name("UP") is None and india.state_name("UP", allow_codes=True) == "Uttar Pradesh"
    assert india.state_name("Orissa") == "Odisha"
    assert india.region_for("Assam") == "North East" and india.region_for("Uttar Pradesh") == "North"
    assert india.region_for("Chhattisgarh") == "Central" and india.region_for("Telangana") == "South"
    assert india.pin_code("Agra -282004, India") == "282004"
    assert india.pin_matches_state("282004", "Uttar Pradesh") and not india.pin_matches_state("282004", "Kerala")


def test_names():
    assert india.dealer_name("M/s. KAVERI ELECTRICALS") == "KAVERI ELECTRICALS"
    assert india.name_key("Sharma Bidi Works Pvt. Ltd.") == india.name_key("SHARMA BIDI WORKS PRIVATE LIMITED")


def test_classification_from_nic_and_text():
    assert classify.nic_rule("12002") == ("Manufacturer", ["Bidi"])
    assert classify.nic_rule("16004") == ("Manufacturer", ["Cigarettes"])  # NIC 2004 code of an older company
    assert classify.nic_rule("46307") == ("Wholesaler", ["Tobacco"])
    assert classify.nic_rule("13111") is None
    assert classify.products_from_text("Distributors of cigarettes, beedi and pan masala") == ["Cigarettes", "Bidi", "Pan Masala"]
    assert classify.type_from_text("C & F agent for ITC") == "Distributor"
    assert classify.type_from_text("Exporters of FCV tobacco") == "Exporter / Importer"
    assert classify.products_from_text("tea leaf merchants") == []


def test_sector_is_the_majority_sector_of_the_products():
    sector_file = REPO_DIR / "sector.json"
    assert classify.sector_for(["Bidi", "Cigarettes"], sector_file) == "Tobacco & Related Products"
    assert classify.sector_for(["Unknown thing"], sector_file, default="X") == "X"
