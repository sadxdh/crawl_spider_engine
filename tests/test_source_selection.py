import os

from collectors.source_selection import optional_proxy, selected_sources


def test_selected_sources_defaults_to_all(monkeypatch):
    monkeypatch.delenv('TEST_SOURCES', raising=False)
    assert selected_sources('TEST_SOURCES', {'domestic', 'overseas'}) == {
        'domestic', 'overseas'
    }


def test_selected_sources_filters_unknown_values(monkeypatch):
    monkeypatch.setenv('TEST_SOURCES', 'overseas,unknown')
    assert selected_sources('TEST_SOURCES', {'domestic', 'overseas'}) == {'overseas'}


def test_optional_proxy_supports_explicit_direct_mode(monkeypatch):
    monkeypatch.setenv('TEST_PROXY', 'direct')
    assert optional_proxy('TEST_PROXY', 'socks5://default') == ''
