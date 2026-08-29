"""软件违规-工信部 → entity_software_description
参照旧项目 data_crawl_server MiitViolationsSpider:
  list: wap.miit.gov.cn API → 解析列表 → 详情页
"""
import scrapy
import os
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.file_kit import extract_pdf_table, extract_docx_table
from utils.mysql_tools import select_data
from utils.tools import *
from spire.doc import Document as dc
from spire.doc import FileFormat
import tempfile
# 经营风险  软件违规  抓取新更新的数据

class MiitSoftwareViolationSpider(BaseSpider):
    name = 'economy_miit_violation'
    data_table = 'entity_software_description'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Host': 'wap.miit.gov.cn',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'Accept': '*/*',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://wap.miit.gov.cn/jgsj/xgj/fwjd/index.html',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    @staticmethod
    def str_replace(data):
        if not data:
            return ''
        if isinstance(data, list):
            data = data[0] if data else ''
        return data.strip().replace('\xa0', '').replace('\n', '').replace(' ', '')

    @staticmethod
    def pdf_file(content):
        """pdf文件解析"""
        end_dict = {}
        last_num = None
        tables = extract_pdf_table(content)
        for table in tables:
            for row in table:
                if row[0] and '序' not in row[0]:
                    num = row[0]
                    if not num and last_num:
                        if row[2]:
                            end_dict[last_num]['entity_name'] += row[2].replace('\n', '')
                        if row[-1]:
                            end_dict[last_num]['issues_involved'] += ',' + row[-1].replace('\n', '')
                    else:
                        end_dict[num] = {
                            'software_name': row[1].replace('\n', ''),
                            'entity_name': row[2].replace('\n', ''),
                            'version_number': row[4].replace('\n', ''),
                            'issues_involved': row[-1].replace('\n', '')
                        }
                        last_num = num
        if not end_dict:
            return None
        return end_dict

    @staticmethod
    def html_file(details_element):
        """网页表格解析"""
        table = details_element.xpath('//table/tbody/tr')
        if not table:
            logger.exception(f'html数据文件类型错误，不能提取数据')
            return None
        end_dict = {}
        for tr in table[1:]:
            num = tr.xpath('./td[1]/p/span/text()')[0]
            software_name = tr.xpath('./td[2]/p/span/text()')
            entity_name = tr.xpath('./td[3]/p/span/text()')
            regex = re.compile(r'[\u4e00-\u9fa5]')
            version = tr.xpath('./td[5]/p/span/text()')
            if version:
                if not regex.search(version[0]):
                    version_number = version[0]
                else:
                    version_number = tr.xpath('./td[4]/p/span/text()')[0]
            else:
                version_number = ''
            issues_involved = tr.xpath('./td[6]/p/span/text()')

            if software_name:
                end_dict[num] = {
                    'software_name': software_name[0].replace('\n', ''),
                    'entity_name': entity_name[0].replace('\n', ''),
                    'version_number': version_number.replace('/', ''),
                    'issues_involved': issues_involved[0].replace('\n', '')
                }
                last_num = num
            else:
                issues_involved = tr.xpath('./td/p/span/text()')[0]
                end_dict[last_num]['issues_involved'] += ',' + issues_involved
        if not end_dict:
            return None
        return end_dict

    @staticmethod
    def docx_file(content):
        """docx文件解析"""
        # 打开.docx文件
        for i in range(5):
            tb = extract_docx_table(content)
            # 遍历文档的第一个表格的行
            end_dict = {}
            for r in tb[0].rows[1:]:
                row_cnt = [cell.text for cell in r.cells]
                try:
                    seq_num = int(row_cnt[0])
                except ValueError:
                    continue

                if str(seq_num) in end_dict:
                    end_dict[str(seq_num)]['issues_involved'] += ',' + row_cnt[-1]
                else:
                    regex = re.compile(r'[\u4e00-\u9fa5]')
                    version = row_cnt[4].replace('\n', '')
                    if not regex.search(version):
                        version_number = version
                    else:
                        version_number = row_cnt[3].replace('\n', '')
                    end_dict[str(seq_num)] = {
                        'software_name': row_cnt[1].replace('\n', ''),
                        'entity_name': row_cnt[2].replace('\n', ''),
                        'version_number': version_number,
                        'issues_involved': row_cnt[-1].replace('\n', '')
                    }
            if end_dict:
                return end_dict
            else:
                logger.exception(f'文档解析失败，重试次数{i + 1}')
        return None

    def doc_to_docx(self, content):
        # 创建一个临时文件来存储 .doc 内容
        with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as temp_doc:
            temp_doc_path = temp_doc.name
            temp_doc.write(content)
        # 创建一个临时文件路径来存储 .docx 内容
        temp_docx_path = temp_doc_path + "x"
        try:
            doc = dc()
            # 加载 .doc 文件
            doc.LoadFromFile(temp_doc_path)
            # 保存为 .docx 文件
            doc.SaveToFile(temp_docx_path, FileFormat.Docx)
            # 读取 .docx 文件内容
            with open(temp_docx_path, 'rb') as temp_docx:
                docx_content = temp_docx.read()
        finally:
            # 删除临时文件
            os.remove(temp_doc_path)
            os.remove(temp_docx_path)
        return self.docx_file(docx_content)

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = 'https://wap.miit.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit'
            params = {
                'webId': '8d828e408d90447786ddbe128d495e9e',
                'pageId': '3e9c77c85a4c41889c4f93e38882e5a3',
                'parseType': 'buildstatic',
                'pageType': 'column',
                'tagId': '当前栏目_list',
                'tplSetId': '209741b2109044b5b7695700b2bec37e',
                'paramJson': json.dumps({"pageNo": page, "pageSize": 24}),
            }
            request_url = f'{url}?{urlencode(params)}'
            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        details_html = response.json()['data']['html']
        details_element = etree.HTML(details_html)
        li_list = details_element.xpath('//div[@id="当前栏目_list"]/div/ul/li')
        for li in li_list:
            self.title = self.str_replace(li.xpath('./a/@title'))  # 标题
            self.date_time = self.str_replace(li.xpath('./span/text()'))  # 发布时间
            # 只抓取包含的指定标题
            if re.search(r'总第|APP通报|侵害用户权益行为的APP', self.title):
                details_href = 'https://wap.miit.gov.cn' + li.xpath('./a/@href')[0]
                yield scrapy.Request(
                    url=details_href,
                    method='GET',
                    headers=self.headers,
                    callback=self.get_details
                )

    def get_details(self, response):
        """请求详情页,返回解析后的数据"""
        try:
            details_element = etree.HTML(response.body)
            # 提取内容并去除“附件：”之后的部分
            self.details_content = self.str_replace(
                ''.join(details_element.xpath('//div[@id="con_con"]//text()'))
            ).split('附件：')[0]
            try:
                pdffile_url = 'https://wap.miit.gov.cn' + details_element.xpath('//iframe/@fileurl')[0]
            except:
                for p_data in details_element.xpath('//div[@id="con_con"]/p'):
                    try:
                        pdffile_url = 'https://wap.miit.gov.cn' + p_data.xpath('.//a/@href')[0]
                        break
                    except:
                        pdffile_url = None
            file_type = ''
            if pdffile_url:
                # 下载文件
                file_type = pdffile_url.split('.')[-1]
                file_response = common_request(url=pdffile_url, headers=self.headers, proxies_type=True)
                content = file_response.content
            # 判断文件,调用对应的解析函数
            if file_type == 'docx':
                file_return_data = self.docx_file(content)
            elif file_type == 'pdf':
                file_return_data = self.pdf_file(content)
            elif file_type == 'doc':
                file_return_data = self.doc_to_docx(content)  # self.doc_file(file_name)
            else:
                file_return_data = self.html_file(details_element)
        except Exception as e:
            msg = f'请求详情页失败失败{e}，url：{response.url}'
            self.log_error(msg)
            file_return_data = None

        if file_return_data:
            yield from self.parse_detail(file_return_data, response.url)
        else:
            self.log_error(f'附件解析失败，url：{response.url}')

    def parse_detail(self, file_data, details_href):
        """解析字段"""
        for end_data_key, end_data_value in file_data.items():
            entity_name = end_data_value['entity_name'].replace('\u3000', '')  # entity_name	公司名称
            software_name = end_data_value['software_name'].replace('\u3000', '')  # software_name	软件名称
            version_number = end_data_value['version_number'].replace('\\', '').replace('u3000',
                                                                                        '')  # version_number	版本号
            release_time = self.date_time  # release_time	发布时间
            issues_involved = end_data_value['issues_involved'].replace('\u3000', '')  # issues_involved	所涉问题
            title = self.title  # title	标题
            content = self.details_content  # content	内容
            url = details_href  # url	来源url
            source = '信息通信管理局'  # source	数据来源
            mysql_result = select_data(table='wentao_basedata.entity_info',
                                       data=['entity_id'],
                                       condition=f'entity_name = "{entity_name}";')
            if mysql_result:
                entity_id = mysql_result[0]['entity_id']
            else:
                entity_id = None
            md5_value = hash_md5(entity_name + software_name + version_number)
            items = {}
            items['md5_value'] = md5_value
            items['entity_name'] = entity_name
            items['software_name'] = software_name
            items['version_number'] = version_number
            items['release_time'] = release_time
            items['issues_involved'] = issues_involved
            items['title'] = title
            items['content'] = content
            items['url'] = url
            items['source'] = source
            items['entity_id'] = entity_id
            # insert_data(table='entity_software_description', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
