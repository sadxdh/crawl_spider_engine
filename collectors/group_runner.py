"""Run a regional collector group in one process to reduce memory overhead."""

import importlib
import os
import signal
import threading
import time

from loguru import logger


COLLECTORS = {
    'flash_news': ('collectors.flash_news_collector', 'FlashNewsCollector'),
    'tg_news': ('collectors.tg_collector', 'TgNewsCollector'),
    'market_quote': ('collectors.market_collector', 'MarketCollector'),
    'onchain_quote': ('collectors.onchain_collector', 'OnchainCollector'),
    'sentiment_metrics': ('collectors.sentiment_collector', 'SentimentCollector'),
    'gate_micro': ('collectors.gate_micro_collector', 'GateMicroCollector'),
    'deribit_options': ('collectors.deribit_collector', 'DeribitCollector'),
    'liquidation_data': ('collectors.liquidation_collector', 'LiquidationCollector'),
    'gold_market': ('collectors.gold_collector', 'GoldCollector'),
    'hyperliquid_data': ('collectors.hyperliquid_collector', 'HyperliquidCollector'),
    'taker_flow': ('collectors.taker_flow_collector', 'TakerFlowCollector'),
    'etherscan_tx': ('collectors.etherscan_address_collector', 'EtherscanAddressCollector'),
    'coinglass_data': ('collectors.coinglass_collector', 'CoinglassCollector'),
    'okx_microstructure': ('collectors.okx_microstructure_collector', 'OkxMicrostructureCollector'),
    'macro_prices': ('collectors.macro_prices_collector', 'MacroPricesCollector'),
    'fomc_captions': ('collectors.fomc_captions_collector', 'FomcCaptionsCollector'),
    'market_kline': ('collectors.market_kline_collector', 'MarketKlineCollector'),
    'prediction_market': ('collectors.prediction_market_collector', 'PredictionMarketCollector'),
}


def configured_collectors(value: str | None = None) -> list[str]:
    raw = value if value is not None else os.getenv('COLLECTOR_GROUP', '')
    names = [item.strip() for item in raw.split(',') if item.strip()]
    unknown = sorted(set(names) - set(COLLECTORS))
    if unknown:
        raise ValueError('unknown collectors: ' + ','.join(unknown))
    return list(dict.fromkeys(names))


class CollectorGroup:
    def __init__(self, names: list[str]):
        if not names:
            raise ValueError('COLLECTOR_GROUP must contain at least one collector')
        self.names = names
        self.stop_event = threading.Event()
        self.instances = {}
        self.threads = []

    def _run_one(self, name: str):
        module_name, class_name = COLLECTORS[name]
        while not self.stop_event.is_set():
            instance = None
            try:
                cls = getattr(importlib.import_module(module_name), class_name)
                instance = cls()
                self.instances[name] = instance
                logger.info('[collector-group] 启动 {}', name)
                instance.start()
            except Exception:
                logger.exception('[collector-group] {} 异常退出', name)
            finally:
                self.instances.pop(name, None)
            if not self.stop_event.wait(5):
                logger.warning('[collector-group] 重启 {}', name)

    def start(self):
        for name in self.names:
            thread = threading.Thread(
                target=self._run_one,
                args=(name,),
                daemon=True,
                name=f'collector-{name}',
            )
            thread.start()
            self.threads.append(thread)
        while not self.stop_event.wait(5):
            if not any(thread.is_alive() for thread in self.threads):
                raise RuntimeError('all collector threads stopped')

    def stop(self, *_args):
        self.stop_event.set()
        for instance in list(self.instances.values()):
            try:
                instance.stop()
            except Exception:
                logger.exception('[collector-group] stop failed')
        for thread in self.threads:
            thread.join(timeout=15)


def main():
    group = CollectorGroup(configured_collectors())
    signal.signal(signal.SIGTERM, group.stop)
    signal.signal(signal.SIGINT, group.stop)
    logger.info('[collector-group] collectors={}', ','.join(group.names))
    group.start()


if __name__ == '__main__':
    main()
