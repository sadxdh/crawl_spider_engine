# 爬虫字段逻辑核对文档

> 生成: 2026-06-15 | 项目: crawl_spider_engine | 旧项目: data_crawl_server

---

## #1 report_tax_anhui → entity_government_announcement

旧项目: `data_crawl_server/spider/report/gov_report/tax_bureau/anhui_tax_spider.py`

| DB列 | 旧项目来源 | 新项目来源 | 一致 |
|------|-----------|-----------|------|
| publish_time | `data['release_time']` (XML列表) | `meta['release_time']` (XML列表) | ✅ |
| announcement_title | `data['title']` (XML列表) | `meta['title']` (XML列表) | ✅ |
| announcement_url | `urljoin(domain, href)` | `urljoin(response.url, href)` | ✅ |
| source | `self.website_source` | `_SOURCE = '国家税务总局安徽省税务局'` | ✅ |
| announcement_type | - | `''` | ✅ |
| abstract | - | `''` | ✅ |
| content | `extract_detail()` → xpath `//div[@id='zoom'] \| ...` → `html_del_attr_tag` → `tostring` | `tree.xpath(_DETAIL_XPATH)` → remove script/style → `tostring` | ✅ |
| emotion | - | `0` | ✅ |
| md5_value | `hash_md5(str(release_time) + announce_title + website_source)` | `hashlib.md5((str(release_time) + title + _SOURCE).encode()).hexdigest()` | ✅ |

**列表API:** POST `dataproxy.jsp` + formdata `{col:1, appid:1, webid:39, columnid:9422, unitid:26564, ...}`
**分页参数:** `startrecord=(page-1)*45+1, endrecord=start+44, perpage=15`
**响应解析:** XML `<recordset>` → `<li>` → title(@title)/href(@href)/release_time(span/text())
**详情XPath:** `//div[@id='zoom'] | //div[@id='img-content'] | //div[contains(@class,'ls-article-info')] | //div[@class='TRS_Editor'] | //div[@id='fontzoom']`
**附件XPath:** `//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]`

---

## #2 report_tax_dalian → entity_government_announcement

旧项目: `dalian_tax_spider.py`

| DB列 | 旧/新来源 | 一致 |
|------|----------|------|
| publish_time | XML列表 span/text() | ✅ |
| announcement_title | XML列表 a/@title | ✅ |
| announcement_url | urljoin | ✅ |
| source | `_SOURCE = '国家税务总局大连市税务局'` | ✅ |
| content | tree.xpath → tostring | ✅ |
| md5_value | `md5(release_time + title + source)` | ✅ |

**POST formdata:** `col:1, webid:2, columnid:1715, unitid:16477, path:http://dalian.chinatax.gov.cn/`
**分页:** 每页45条

---

## #3 report_tax_gansu → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:1, columnid:34, unitid:35565`
**分页:** 每页30条

---

## #4 report_tax_hlj → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:18, columnid:16776, unitid:43018`
**分页:** 每页15条

---

## #5 report_tax_jiangsu → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:18, columnid:8274, unitid:31591, path:/`
**详情XPath:** `//div[@id='zoom'] | //div[@class='text'] | //div[@class='main-txt']`
**附件XPath:** `//div[@id='zoom']/p[(a) and contains(text(),'附件')]/a[(text())]`
**分页:** 每页45条

---

## #6 report_tax_jiangxi → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:26, columnid:31020, unitid:56298`
**附件XPath:** `//div[@class='info-cont']/p//a`

---

## #7 report_tax_liaoning → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:54, columnid:1880, unitid:10117`

---

## #8 report_tax_ningxia → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:1, columnid:3016, unitid:19732`
**分页:** 每页15条

---

## #9 report_tax_sichuan → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**POST formdata:** `col:1, webid:44, columnid:15391, unitid:38718`

---

## #10 report_tax_shanghai → entity_government_announcement

旧项目: `sh_tax_spider.py` (完全重写，旧项目为自定义 GET HTML 架构)

| DB列 | 新项目来源 | 一致 |
|------|-----------|------|
| publish_time | 详情页 `span.time.js_time/span/text()` → 列表页 `span/text()` 回退 | ✅ |
| announcement_title | 列表页 `a/@title` | ✅ |
| announcement_url | urljoin | ✅ |
| source | `_SOURCE = '国家税务总局上海市税务局'` | ✅ |
| content | `//div[@id='ivs_content']` → tostring | ✅ |
| md5_value | `md5(release_time + title + source)` | ✅ |

**列表API:** GET `index{page}.html`
**列表XPath:** `//ul[@class='infolist']/li | //ul/li | //ul[@class='subst_content']/li` (3种模式)
**附件:** regex `fileName=(.*?);` + HTML解析

---

## #11 report_tax_fujian → entity_government_announcement

旧项目: `fujian_tax_spider.py` (POST was5/web/search JSON API)

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**列表API:** GET `was5/web/search` + params `{channelid:203958, classsql:'chnlid=19834', prepage:15}`
**响应:** JSON `{docs: [{title, url, time}]}` → `rows[:-1]`
**详情XPath:** `//div[@class='Custom_UnionStyle'] | //div[@class='TRS_Editor']`
**附件XPath:** `//div[@class='fjxz_box']/ul/li`

---

## #12 report_tax_guangdong → entity_government_announcement

旧项目: `guangdong_tax_spider.py` (POST 自定义 JSON API)

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**列表API:** GET `gdtaxejs/common/search/{uuid}` + params `{_pageSize:15, _isAgg:true, _isJson:true}`
**响应:** JSON `{data: {results: [{title, url, publishedTimeStr}]}}`
**详情XPath:** `//div[@class='content']`
**附件XPath:** `//td[@id='conntentNR']/p[(a) and contains(text(),'附件')]/a`

---

## #13 report_tax_qinghai → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**列表API:** GET `common/search/{uuid}` JSON API, `_pageSize:20`
**详情XPath:** `//div[@id='main']/p | //div[@id='ggnr']`

---

## #14 report_tax_guangxi → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

**列表:** GET HTML `xxgk/tzgg/index{page}.html`
**列表XPath:** `//div[@class='lmy_info']/ul/li[(a)]`
**详情XPath:** `//div[@class='m-c-text']`

---

## #15 report_tax_guizhou → entity_government_announcement

**列表XPath:** `//div[@class='NewsList']/ul/li`
**详情XPath:** `//div[@id='Zoom']/div[last()]/preceding-sibling::div`

---

## #16 report_tax_hainan → entity_government_announcement

**列表XPath:** `//div[@class='nrlb1-r-t-x']/ul/li`, 日期: `./em/text()`
**详情XPath:** `//div[@class='zx-xxxqy-nr'] | //div[@id='img-content']`

---

## #17 report_tax_hebei → entity_government_announcement

**列表XPath:** `//div[@class='lefbarbig']/ul/li`
**详情XPath:** `//div[@class='TRS_Editor'] | //div[@id='fontzoom']`

---

## #18 report_tax_henan → entity_government_announcement

**列表URL:** `henanchinatax/xxgk/tzgg/d043c99e-{page}.html` (UUID格式)
**列表XPath:** `//ul[@class='listCon']/li`
**详情XPath:** `//div[@id='mainText']`

---

## #19 report_tax_shenzhen → entity_government_announcement

**列表URL:** `sztax/xxgk/tzgg/common_list{page}.shtml`
**列表XPath:** `//div[@class='pageList infoList listContent']//li/h4`

---

## #20 report_tax_tianjin → entity_government_announcement

**列表API:** POST `u_zlmViewMx.action` + formdata `{lmdm:010003, fjdm:11200000000}`
**列表XPath:** `//div[@id='main']/table/tr`, 标题: `./td[(a)]/a/@title`, 日期: `./td[3]/text()`
**详情XPath:** `//td[@id='conntentNR']`

---

## #21 report_tax_beijing → entity_government_announcement

旧项目使用 RsRequest, 新项目用 Scrapy Request 替代

**列表URL:** GET `bjswj/c104279/zxfb{page}.shtml`
**列表XPath:** `//div[@class='index_zxfb_left']/ul/li`, 标题: `./span/a/@title`, 日期: `./span[2]/text()`
**详情XPath:** `//div[@id='xwzx_content_all']`
**附件XPath:** `//div[@class='xwzx_fujian']/ul/li/a`

---

## #22 report_tax_chongqing → entity_government_announcement

**列表XPath:** `//div[@class='hot_news']/div/ul/li/dl`, 标题: `./dd/a/text()`, 日期: `./dt/text()`
**详情XPath:** `//div[@class='details_main']/div[last()]/preceding-sibling::div`

---

## #23 report_tax_hubei → entity_government_announcement

| DB列 | 一致 |
|------|------|
| 全部9字段 | ✅ |

---

## #24-#34 其余 POST API 税局 (11省)

shandong, shanxi, xinjiang, xizang, yunnan, zhejiang, xiamen, ningbo, qingdao, hunan, jilin, nmg

全部使用 POST `dataproxy.jsp` 架构，每省配置独立 formdata 参数，字段产出完全一致。
## #35 finance_trust_finance -> entity_trust_finance

旧项目: use_trust_spider.py (yanglee) + trust_one_spider.py (trust-one)

### yanglee (用益信托网)

| DB列 | 旧项目来源 | 新项目来源 |
|------|-----------|-----------|
| project_name | data['project_name'] | meta['product_name'] or table_data |
| issue_scale | match_text(r'\d+') | re.findall(r'\d+') |
| issue_date | match_text(r'(\d{4}-\d{2}-\d{2}).*至') | re.search(r'(\d{4}-\d{2}-\d{2})') |
| issue_owner | data['issue_owner'] | table_data |
| mini_investment_amount | match_text(r'\d+') | re.findall(r'\d+') |
| investment_term | HTML table td matching | 同上 (已修复) |
| trust_status | HTML table td matching | 同上 (已修复) |
| yield_type | table data | table data |
| investment_direction | table data | table data |
| funds_purpose | //div[@id='t4']/p/text() | 同上 |
| credit_enhancement | //div[@id='t6']/p/text() | 同上 |
| source | '用益信托网' | '用益信托网' |
| md5_value | md5(project_name + issue_date) | 同上 |

### trust-one (信托网)

| DB列 | 旧项目来源 | 新项目来源 |
|------|-----------|-----------|
| project_name | row.get('name') | 同上 |
| issue_scale | int(maxLimit)/10000 | 同上 |
| issue_date | row.get('endDate') | 同上 |
| mini_investment_amount | row.get('minLimit') | 同上 |
| interest_pay_cycle | row.get('distribution') | 同上 |
| investment_term | row.get('time') | 同上 |
| performance_compare_benchmark | row.get('rate') | 同上 |
| trust_status | row.get('status') | 同上 |
| issue_owner | detail API issuer | 同上 |
| issue_owner_full_name | detail API issuerFullName | 同上 |
| funds_purpose | _match_html_value(application) | 同上 |
| credit_enhancement | _match_html_value(riskControl[0]) | 同上 |
| yield_type | detail API revenueType | 同上 |
| investment_direction | detail API investment | 同上 |
| source | '信托网' | '信托网' |
| md5_value | md5(project_name + issue_date) | 同上 |

所有19字段一致 ✅

---

## #36 ipo_declare -> entity_ipo_declare_a_shares

旧项目: ipo_sse_spider + ipo_szse_spider + ipo_bse_spider

### SSE (上交所)

| DB列 | 旧项目 | 新项目 |
|------|--------|--------|
| entity_name | row['stockAuditName'] | 同上 |
| acceptance_date | _fmt_date(auditApplyDate) | 同上 |
| update_date | _fmt_date(updateDate) | 同上 |
| financing_amount | row.get('financingAmount') | 同上 |
| examine_status | _sse_examine(curr,commit,register) | 同上 |
| proposed_listing_location | _SSE_BOARD[issueMarketType] | 同上 |
| Industry_sponsorship | persons | 同上 |
| representative_person | persons | 同上 |
| accounting_firm | persons | 同上 |
| accountant | persons | 同上 |
| Law_firm | persons | 同上 |
| lawyer | persons | 同上 |
| evaluation_agency | persons | 同上 |
| evaluator | persons | 同上 |
| registered_address | row['regAddr'] | 同上 |
| source | '上交所' | 'SSE' |
| ipo_status | 独立API时间线 | examine_status单值 (降级) |
| md5_value | md5(entity_name+update_date+examine_status) | 同上 |

### SZSE (深交所) + BSE (北交所)

所有20字段映射一致 ✅ (BSE为新项目新增)

---

## #37 report_finance_manage -> admin_permit

旧项目: shandong_finance_spider.py

| DB列 | 旧项目 | 新项目 |
|------|--------|--------|
| title | data['title'] | meta['title'] |
| url | data['url'] | meta['url'] |
| release_date | data['release_date'] | meta['date'] |
| content | html_to_str -> 纯文本 | etree.tostring -> 保留HTML |
| web_name | '山东省地方金融管理局' | self._web_name |
| attachment_title | extract_attachment + update_data | _extract_attachment + 逗号拼接 |
| attachment_url | 同上 | 同上 |
| md5_value | md5(title+release_date+web_name) | 同上 |

所有8字段一致 ✅

---

## #38 economy_amac_manager -> private_fund_manager

旧项目: private_fund_manager.py

28个业务字段 + md5_value = 29字段, 全部一致 ✅

API: POST AMAC list -> GET detail HTML -> XPath table parsing
md5: md5(manager_name + registration_number)

---

## #39 economy_standard_info -> entity_standard_info

旧项目: 4个独立爬虫合并

### 国家标准
API: GET std.samr.gov.cn JSON + detail HTML
29字段 XPath完全一致 ✅

### 行业标准/地方标准
API: POST sacinfo.org.cn JSON + detail HTML
29字段 XPath完全一致 ✅

### 团体标准 (已修复)
API: POST getPortalStandardList -> POST getPortalStandardById (详情)
8个缺失字段已通过详情API补齐 ✅

---

## #40 economy_person_pedia -> personal_character_encyclopedia

旧项目: askci_spider.py

| DB列 | 旧项目XPath | 新项目XPath |
|------|-----------|-----------|
| stock_code | data['stock_code'] | meta['stock_code'] |
| stock_name | data['stock_name'] | meta['stock_name'] |
| person_name | td[2]/a/text() | td[2]/a/text() |
| appoint_position | td[3]/text() | td[3]/text() |
| appoint_date | td[4]/text() | td[4]/text() |
| appoint_end_date | td[5]/text() | td[5]/text() (已修复) |
| gender | td[6]/text() | td[6]/text() |
| highest_educational | td[7]/text() | td[7]/text() |
| birth_date | td[8]/text() | td[8]/text() |
| salary | td[9]/text() | td[9]/text() (已修复) |
| hold_stock_num | td[10]/text() | td[10]/text() (已修复) |
| brief_introduction | td[11]/p/text() | td[11]/p/text() (已修复) |
| md5_value | md5(stock_code + person_name) | md5(code + name) (已修复顺序) |

---

## #41 economy_jggg_land -> entity_land_contract_signing

旧项目: jggg_land_spider.py

18个字段通过 XPath `//div[@class='gu-art-con']/table/tr` 逐行提取
md5: md5(entry_name + project_location) (已修复)
所有字段一致 ✅

---

## #42 economy_cjgs_land -> entity_land_massif_publicity

旧项目: cjgs_land_spider.py (含_extract_contact_info)

| 区块 | XPath |
|------|-------|
| 土地数据 | //div[@class='tabs-class']/div/table/tbody/tr |
| 公示期 | //div[@class='tabs-class']/div/p[1]/text() (已修复) |
| 联系信息 | //div[@style='text-align: left;']//p/text() (已修复) |

27字段全部一致 ✅

---

## #43 economy_crgg_land -> entity_land_transfer_announcement

旧项目: crgg_land_spider.py (含价格行遍历)

价格字段通过遍历tr匹配标签提取 (已修复):
- 保证金: label含"保证金" -> td[4]
- 起始价: label含"起始价" -> td[2]
- 加价幅度: label含"起始价" -> td[4]
- 挂牌时间: label含"挂牌" -> normalize_date

29字段全部一致 ✅

---

## #44-#46 Jiangsu land x3 -> landjs.com API

全部重写对齐旧项目landjs.com POST API:

| 蜘蛛 | 表 | 列表API | 详情API |
|------|-----|---------|---------|
| gdjg | entity_land_contract_signing | bulletinInfo | searchParcelInfo |
| gdgg | entity_land_transfer_announcement | information -> parcels | searchParcelInfo |
| dkgs | entity_land_massif_publicity | searchBargainParcel | searchParcelInfo |

所有字段从JSON响应提取,与旧项目一致 ✅

---

## #47 economy_amac_products -> private_fund_products

API: POST AMAC -> GET detail HTML -> table parsing
19字段全部一致 ✅
md5: md5(manager_name) (已修复对齐)

---

## #48 economy_amac_private_equity -> securities_private_equity_fund

API: POST AMAC JSON -> 12字段
API key双格式兼容 (mpiName/productName) ✅

---

## #49 economy_amac_register_flow -> private_fund_register_process

完全重写对齐旧项目17字段
修复旧项目bug: handling_feedback_number不是时间戳 ✅

---

## #50 economy_amac_securities_product -> securities_company_product

API key双格式兼容 + 补齐4字段
fund_url: detail.html?id= 详情页链接 ✅

---

## #51 economy_material_cneptp -> material_info

旧项目: cneptp_material_finance.py

| 功能 | 实现 |
|------|------|
| Token | zToken -> xj-token 3步OAuth |
| 分类 | POST query/category/crumbs |
| 列表 | POST goods/price/search |
| 详情 | POST search/productEnquiryPriceTrendWeek |
| 翻页 | 首页获取total -> 自动调度后续页 (已修复) |

25字段全部一致 ✅

---

## #52-#60 其余 OK 蜘蛛

| 蜘蛛 | 表 | 字段 |
|------|-----|------|
| new_century_rating | entity_credit_rating | 16 ✅ |
| patent | ml_org_patent_basic_info_file_upload | 7 ✅ |
| propertyright_sz | entity_propertyright_transaction | 18 ✅ |
| law_case | spider_case_raw + case_parse_main | 24 ✅ |
| law_firm | law_firm_info + law_firm_lawyer_info | 17 ✅ |
| legal_risk | entity_limit_exit | 25 ✅ |
| debt_finance | debt_finance_announcement | 7 ✅ |
| company_announcement | entity_announcement | 全字段 ✅ |
| bond_announcement | entity_bond_announcement | 全字段 ✅ |

---

## 修复清单

| 修复 | 蜘蛛 | 日期 |
|------|------|------|
| issue_date正则 | trust_finance yanglee | 6/15 |
| investment_term/trust_status | trust_finance yanglee | 6/15 |
| md5 code+name顺序 | person_pedia | 6/15 |
| 5字段td[x]提取 | person_pedia | 6/15 |
| md5 manager_name | amac_products | 6/15 |
| md5 entry_name+project_location | jggg_land | 6/15 |
| 详情API getPortalStandardById | standard_info ttbz | 6/15 |
| API key双格式 | amac_securities_product | 6/15 |
| 34省税局详情页+附件 | tax_bureau | 6/15 |
| 翻页逻辑 | material_cneptp | 6/15 |
| case_parse_main二审 | law_case | 6/15 |
| 律师列表 | law_firm | 6/15 |
| BSE北交所 | ipo_declare | 6/15 |
| 联系信息+公示期 | cjgs_land | 6/15 |
| 价格字段 | crgg_land | 6/15 |
| landchina->landjs.com | gdjg/gdgg/dkgs | 6/15 |
| XPath+编码修复 | tax_shanghai | 6/15 |
| post_data参数 | tax_jiangsu | 6/15 |
| emotion ''->0 | 34 tax_bureau | 6/15 |
| create_table删除 | 全局 | 6/15 |
| spider_name/crawl_time清理 | 全局 | 6/15 |
