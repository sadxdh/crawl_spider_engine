"""
资讯类爬虫基类（示例，含 LLM 内容抽取）
"""
from spiders.base_spider import BaseSpider

class NewsBaseSpider(BaseSpider):
    use_llm = False

    LLM_SCHEMA = {
        "title": "文章标题",
        "author": "作者",
        "pub_date": "发布时间（格式：YYYY-MM-DD）",
        "summary": "摘要（100字以内）",
        "keywords": "关键词列表（最多5个）",
        "category": "文章分类",
    }

    def extract_with_llm(self, content: str) -> dict:
        if not self.use_llm:
            return {}
        try:
            from utils.llm_client import llm_client
            return llm_client.extract(content, self.LLM_SCHEMA)
        except Exception as e:
            self.log_warning(f"LLM抽取失败: {e}")
            return {}

    def build_news_item(self, response, **extra):
        content = ' '.join(response.css('article *::text, .content *::text').getall()).strip()
        item = {}
        item['url'] = response.url
        item['source'] = self.name
        item['content'] = content
        if self.use_llm and content:
            llm_data = self.extract_with_llm(content[:3000])
            item.update(llm_data)
        item.update(extra)
        return item
