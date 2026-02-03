import pytest
from scraper_laptops import extract_cpu_from_title, extract_ram_from_title, extract_ssd_from_title, extract_screen_from_title, parse_price


def test_extract_cpu():
    assert 'i7-1185G7' in extract_cpu_from_title('Dell XPS 13 i7-1185G7 16GB DDR4')
    assert 'M3 Pro' in extract_cpu_from_title('Apple MacBook Pro 14 M3 Pro 18GB')
    assert 'Ryzen' in extract_cpu_from_title('Lenovo ThinkPad Ryzen 7 5800U 16GB')


def test_extract_ram():
    cap, typ = extract_ram_from_title('16GB DDR4')
    assert cap == '16GB'
    assert typ and 'DDR' in typ.upper()

    cap, typ = extract_ram_from_title('18GB Unified')
    assert cap == '18GB'
    assert typ is not None


def test_extract_ssd():
    assert extract_ssd_from_title('512GB SSD') == '512GB'
    assert extract_ssd_from_title('1TB NVMe M.2') == '1TB'


def test_extract_screen():
    assert extract_screen_from_title('13.4" FHD') == '13.4"'
    assert extract_screen_from_title('14"') == '14"'


def test_parse_price():
    assert parse_price('$1,299.99') == 1299.99
    assert parse_price('CDN$ 2,499.99') == 2499.99
    assert parse_price('') is None
