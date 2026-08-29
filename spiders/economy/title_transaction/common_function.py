import json

from utils.db.redis_opt import hgetall
from utils.mysql_tools import select_data

COOKIE_REDIS_KEY = 'title_transaction:cookie_pool'



def query_entity_id(entity_name):
    """查询主体ID"""
    if entity_name:
        mysql_result = select_data(table='wentao_basedata.entity_info',
                                   data=['entity_id'],
                                   condition=f'entity_name="{entity_name}";',
                                   select_type='one')
        return mysql_result['entity_id'] if mysql_result else None
    return None


def query_person_id(person_name):
    """查询人物id"""
    if person_name:
        mysql_result = select_data(table='wentao_basedata.dim_basic_person_related_enterprise',
                                   data=['person_id'],
                                   condition=f'person_name="{person_name}";',
                                   select_type='one')
        return mysql_result['person_id'] if mysql_result else None
    return None


def get_none_content(table, nums):
    field = ['project_name', 'transferee_id', 'transferee', 'file_url', 'md5_value', 'source']
    condition = f'file_url is not null and content is null limit {nums}'
    datas = select_data(table, field, condition=condition)
    return datas


def get_cookies():
    cookies_dict = hgetall(COOKIE_REDIS_KEY)
    if cookies_dict:
        cookies = list(cookies_dict.values())[0]
        return json.loads(cookies)
    return None


# 处理HTML的xpath
HTML_NODE_XPATH = {
    '上海': {'content_xpath': '//div[@class="cpt-sticky-anchor"]', 'rm_node_xpath': ['//div[@class="cpt-anchor"]']},
    '深圳': {'content_xpath': '//div[@class="vab-main_content"]'},
    '产投': {'content_xpath': '//div[contains(@class,"AuthMask_mask_layout")]', 'rm_node_xpath': ['//div[@class="detail_finance_list__3fzl2"]']}
}