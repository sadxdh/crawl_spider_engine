import pytest

from collectors.group_runner import configured_collectors


def test_configured_collectors_preserves_order_and_removes_duplicates():
    assert configured_collectors('market_quote,tg_news,market_quote') == [
        'market_quote', 'tg_news'
    ]


def test_configured_collectors_rejects_unknown_names():
    with pytest.raises(ValueError, match='unknown collectors'):
        configured_collectors('market_quote,missing')
