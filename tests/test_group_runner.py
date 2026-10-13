import pytest

from collectors.base_collector import redis_reporting_enabled
from collectors.group_runner import configured_collectors


def test_configured_collectors_preserves_order_and_removes_duplicates():
    assert configured_collectors('market_quote,tg_news,market_quote') == [
        'market_quote', 'tg_news'
    ]


def test_configured_collectors_rejects_unknown_names():
    with pytest.raises(ValueError, match='unknown collectors'):
        configured_collectors('market_quote,missing')


@pytest.mark.parametrize('value', ['0', 'false', 'NO', 'off'])
def test_redis_reporting_can_be_disabled(value):
    assert redis_reporting_enabled(value) is False


def test_redis_reporting_defaults_to_enabled():
    assert redis_reporting_enabled('1') is True
