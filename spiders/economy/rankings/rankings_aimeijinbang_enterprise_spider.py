"""艾媒金榜榜单爬虫 → rankings_information"""
import hashlib, scrapy
from urllib.parse import urlencode

from spiders.base_spider import BaseSpider
from utils.tools import *
import requests as reqs
from utils.proxy_kit import ScrapyProxy

class RankingsAimeijinbangEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_aimeijinbang_enterprise'
    data_table = 'rankings_information'
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
                     k not in ['功能性食品带货主播排行榜', '带货主播百强榜', '商业领袖影响力榜', '创业者百强榜',
                               '虚拟主播排行榜', '超写实虚拟人榜', '虚拟人百强榜', '演唱会歌手热度榜',
                               '人工智能产业地区榜', '各省预制菜产业发展水平榜']}
        urls = url_dicts.values()
        return set(urls)

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
        pcImg = data_data.get('baseInfo').split('"', 4)[-2]
        items = {}
        items['md5_value'] = hash_md5(title + name)
        items['source'] = '艾媒金榜'
        items['rankings_title'] = title
        items['ranking'] = group_num
        items['rankings_name'] = name
        items['url'] = url
        items['announcement_title'] = name + '.png'
        items['announcement_url'] = pcImg
        self.log_info(items)
        return items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
