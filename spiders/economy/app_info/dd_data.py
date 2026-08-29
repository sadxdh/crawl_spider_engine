import demjson3
from utils.tools import *
from utils.decrypt import decrypt_diandian_data_spider
from loguru import logger

class DdDataSpider():
    spider_name = 'app_info_dd_spider'
    ACCOUNT_REDIS_KEY = 'dd_data:account_info'
    COOKIE_REDIS_KEY = 'dd_data:cookie_pool'

    def __init__(self):
        super().__init__()

    @staticmethod
    def generate_k(e, path, n, r='get'):
        """
        :param e: 请求参数
        :param path: /va/rank
        :param n: aes加密参数
        :param r: 请求类型 默认get
        """
        return decrypt_diandian_data_spider(e, path, n, r)

    def get_aes_param(self, session=None, *args, **kwargs):
        # 获取aes加密参数
        # {s:"9f35b87803880beb8c11bf2010db8813",k:"4480c01cf2e55fb5",l:"0213e93fd959afa3"}
        if session:
            response = session.request(*args, **kwargs)
        else:
            response = common_request(*args, **kwargs)
        if response:
            try:
                result = match_text(response.text, pattern=r'u:(\{.*?\})')
                if result:
                    result = result.replace(',d:b', '').replace(',d:c', '')
                    aes_param = demjson3.decode(result, strict=False)
                    logger.info(f'{self.spider_name} 解析aes加密参数: {aes_param}')
                    return aes_param
            except Exception as e:
                msg = f"{self.spider_name} 解析aes加密参数错误: {e}"
                logger.error(msg)
                # send_dd_msg(self.spider_name, '解析失败', msg)
        return {}
