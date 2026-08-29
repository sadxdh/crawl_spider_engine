"""法律类爬虫基类（示例）"""
from spiders.base_spider import BaseSpider

class LawBaseSpider(BaseSpider):
    """
    法律类爬虫基类
    目标：裁判文书网、行政处罚等
    """
    def build_law_item(self, **kwargs):
        item = {}
        for k, v in kwargs.items():
            item[k] = v
        return item
