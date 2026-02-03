from scraper_laptops import ProxyManager


def test_proxy_rotation_and_failure():
    proxies = ['p1', 'p2', 'p3']
    m = ProxyManager(proxies)
    assert m.has_proxies()
    seen = set()
    for _ in range(6):
        p = m.get_proxy()
        seen.add(p)
    assert seen == set(proxies)

    # report failures to remove a proxy
    m.report_failure('p2')
    m.report_failure('p2')
    m.report_failure('p2')
    m.report_failure('p2')  # after >3 it should be removed
    assert 'p2' not in m.proxies