from backend.tooling.web_search import _canonical_url, _normal_doi


def test_tracking_parameters_and_fragments_do_not_defeat_deduplication():
    assert _canonical_url("HTTPS://Example.COM/paper/?utm_source=x&b=2#a") == "https://example.com/paper?b=2"


def test_doi_prefixes_normalize_to_the_same_identity():
    assert _normal_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert _normal_doi("doi: 10.1000/abc") == "10.1000/abc"
