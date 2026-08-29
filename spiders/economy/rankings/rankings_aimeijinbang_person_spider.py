"""艾媒金榜榜单爬虫 → rankings_information"""
import hashlib, scrapy
from urllib.parse import urlencode

from spiders.base_spider import BaseSpider
from utils.tools import *
import requests as reqs
from utils.proxy_kit import ScrapyProxy

class RankingsAimeijinbangPersonSpider(BaseSpider):
    name = 'economy_rankings_aimeijinbang_person'
    data_table = 'personal_rankings'
    allowed_domains = ['ranking.iimedia.cn']
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,'
                  'image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://ranking.iimedia.cn/tree'
    }

    def extract_ranking_title_id_name(self, ranking_title_list):
        result = {}
        for item in ranking_title_list:
            url = 'https://ranking.iimedia.cn/ranking/' + str(item['id'])
            result.update({item['name']: url})
        return result

    def parse_data(self, data):
        object_map = data['data']['objectMap']
        ranking_data = data['data']['rankingData']
        # 创建一个空列表来存储组合后的数据
        combined_data = []
        # 遍历 object_map 和 ranking_data，将对应的数据组合在一起
        for key, obj_value in object_map.items():
            obj_id = obj_value.get('id')
            if obj_id is None:
                continue  # 如果没有 'id' 字段，跳过当前对象
            for rank_item in ranking_data:
                for rank_key, rank_value in rank_item.items():
                    if str(rank_value) == str(obj_id):
                        combined_item = {**obj_value, **rank_item}
                        combined_data.append(combined_item)
                        break  # 匹配成功后跳出内层循环
                else:
                    continue  # 如果内层循环没有被 break，继续下一个 rank_item
                break  # 匹配成功后跳出中间层循环
        return combined_data

    def get_url_list(self, response):
        """获取当前所有榜单的所有年限url"""
        data = response.json()
        all_ranking_title_lists = []
        for childs in data["data"]:
            for child in childs["children"]:
                if child.get("rankingTitleList"):
                    all_ranking_title_lists.extend(child["rankingTitleList"])

        name_url_list = self.extract_ranking_title_id_name(all_ranking_title_lists)
        url_dicts = {k: v for k, v in name_url_list.items() if
                     k in ['商业领袖影响力榜', '创业者百强榜']}
        urls = url_dicts.values()
        return set(urls)

    def get_position(self, data):
        # 匹配所有中文
        chinese_pattern = re.compile(r'[^\d\W]')
        all_chinese_chars = []
        for key, value in list(data.items())[1:]:
            if key != 'name' and isinstance(value, str):
                chinese_chars = chinese_pattern.findall(value)
                all_chinese_chars.extend(chinese_chars)
        # 将提取的中文字符合并成一个字符串
        position = ''.join(all_chinese_chars)
        return position

    def start_requests(self):
        url = "https://ranking.iimedia.cn/api/ranking/getCatTree"
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=b"",
            callback=self.parse_url,
            errback=self.errback,
            dont_filter=True
        )

    def parse_url(self, response):
        urls_lists = self.get_url_list(response)
        for url in urls_lists:
            title_id = url.split('/')[-1]
            params = {
                'titleId': title_id,
                'isShow': '1'
            }
            get_id = f'https://ranking.iimedia.cn/api/ranking/getTableTimeById'
            url = f'{get_id}?{urlencode(params)}'

            yield scrapy.Request(
                url=url,
                method='POST',
                headers=self.headers,
                body=b'',
                callback=self.parse_id_data,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'title_id': title_id, 'url': url}
            )

    def parse_id_data(self, response, title_id, url):
        id_values = []
        id_data = response.json()
        if id_data['code'] == 200:
            id_values = [item['id'] for item in id_data['data']]

        for value in id_values:
            new_url = f'https://ranking.iimedia.cn/api/ranking/getDataByCondition?tableId={value}&searchKey='
            url_title = f'https://ranking.iimedia.cn/ranking/{title_id}/{value}'
            yield scrapy.Request(
                url=url_title,
                headers=self.headers,
                method='GET',
                callback=self.get_title,
                cb_kwargs={'new_url': new_url, 'url': url}
            )

    def get_title(self, response, new_url, url):
        try:
            etree_xpath = etree.HTML(response.body)
            title1 = etree_xpath.xpath('//div[@class="title-content"]/h1/text()')[0].strip()
            title2 = etree_xpath.xpath('//p[@class="d-content"]/text()')[0].strip()
            title2 = re.search(r'《(.*?)》', title2)
            title = title2.group(1) if title2 else title1
        except:
            title = None
        # 最后的请求-api榜单数据
        yield scrapy.Request(
            url=new_url,
            headers=self.headers,
            method='GET',
            callback=self.parse_detail,
            cb_kwargs={'title': title, 'url': url}
        )

    def parse_detail(self, response, title, url):
        data = response.json()
        if data['code'] == 200:
            combined_data = self.parse_data(data)
            for data_data in combined_data:
                yield self.parse_itme(data_data, title, url)
        else:
            self.log_info(f'请求失败,状态码: {response.status_code}, url: {url}')

    def parse_itme(self, data_data, title, url):
        name = data_data.get('name')
        group_num = data_data.get('groupNum')
        position = self.get_position(data_data)
        items = {}
        items['md5_value'] = hash_md5(title + name)
        items['position'] = position
        items['rankings_title'] = title
        items['ranking'] = group_num
        items['name'] = name
        self.log_info(items)
        return items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
