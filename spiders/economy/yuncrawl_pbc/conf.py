confs = [
    {
        'website_name': '中国人民银行上海市分行',
        'channel': '行政处罚',
        'url': 'http://shanghai.pbc.gov.cn/fzhshanghai/113577/114832/114918/14681/index1.html',
        'end_page': 4,
        'rows_xpath': '//table[@class=" portlet"]//table[position() >= 4 and position() < last()]',
        'content_href_xpath': '//div[@id="zoom"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行北京市分行',
        'channel': '行政处罚',
        'url': 'http://beijing.pbc.gov.cn/beijing/132030/132052/132059/19192/index1.html',
        'end_page': 3,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[4]//tr//table',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()',
    },
    {
        'website_name': '中国人民银行天津市分行',
        'channel': '行政处罚',
        'url': 'http://tianjin.pbc.gov.cn/fzhtianjin/113682/113700/113707/10983/index1.html',
        'end_page': 7,
        'rows_xpath': '//table[@opentype="page"]/tbody/tr/td/ul/li/table',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()',
    },
    {
        'website_name': '中国人民银行河北省分行',
        'channel': '行政处罚',
        'url': 'http://shijiazhuang.pbc.gov.cn/shijiazhuang/131442/131463/131472/5490497/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行山西省分行',
        'channel': '行政处罚',
        'url': 'http://taiyuan.pbc.gov.cn/taiyuan/133960/133981/133988/5482386/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()',
    },
    {
        'website_name': '中国人民银行内蒙古自治区分行',
        'channel': '行政处罚',
        'url': 'http://huhehaote.pbc.gov.cn/huhehaote/129797/129815/129822/5483143/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行辽宁省分行',
        'channel': '行政处罚',
        'url': 'http://shenyang.pbc.gov.cn/shenyfh/108074/108127/108208/5491693/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行吉林省分行',
        'channel': '行政处罚',
        'url': 'http://changchun.pbc.gov.cn/changchun/124680/124698/124705/5491211/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[position() >= 4 and position() <= last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行黑龙江省分行',
        'channel': '行政处罚',
        'url': 'http://haerbin.pbc.gov.cn/haerbin/112693/112776/112783/5500243/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[position() >= 4 and position() <= last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行江苏省分行',
        'channel': '行政处罚',
        'url': 'http://nanjing.pbc.gov.cn/nanjing/117542/117560/117567/5499233/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[3]//table[position()>=1 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()',
    },
    {
        'website_name': '中国人民银行浙江省分行',
        'channel': '行政处罚',
        'url': 'http://hangzhou.pbc.gov.cn/hangzhou/125268/125286/125293/5508277/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td//table[position()>=4 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行安徽省分行',
        'channel': '行政处罚',
        'url': 'http://hefei.pbc.gov.cn/hefei/122364/122382/122389/5487101/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td//table[position()>=4 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行福建省分行',
        'channel': '行政处罚',
        'url': 'http://fuzhou.pbc.gov.cn/fuzhou/126805/126823/126830/5508082/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td//table[position()>=4 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行江西省分行',
        'channel': '行政处罚',
        'url': 'http://nanchang.pbc.gov.cn/nanchang/132372/132390/132397/5501364/index.html',
        'end_page': 1,
        'rows_xpath': '//*[@id="b5ba51bdeb94461b8c8ce4501377e4d7"]/tbody/tr/td/table[4]/tbody/tr/td/table',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()',
    },
    {
        'website_name': '中国人民银行山东省分行',
        'channel': '行政处罚',
        'url': 'http://jinan.pbc.gov.cn/jinan/120967/120985/120994/5487618/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行河南省分行',
        'channel': '行政处罚',
        'url': 'http://zhengzhou.pbc.gov.cn/zhengzhou/124182/124200/124207/5515771/88a88c8d/index1.html',
        'end_page': 2,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td//table[position()>=4 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行湖北省分行',
        'channel': '行政处罚',
        'url': 'http://wuhan.pbc.gov.cn/wuhan/123472/123493/123502/5514615/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td//table[position()>=4 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
    },
    {
        'website_name': '中国人民银行湖南省分行',
        'channel': '行政处罚',
        'url': 'http://changsha.pbc.gov.cn/changsha/130011/130029/130036/5492109/273394c2/index1.html',
        'end_page': 2,
        'rows_xpath': '//table[@class="zwgk1 portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()',
    },
    {
        'website_name': '中国人民银行广东分行',
        'channel': '行政处罚',
        'url': 'http://guangzhou.pbc.gov.cn/guangzhou/129142/129159/129166/5495288/c10f866d/index1.html',
        'end_page': 2,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行广西壮族自治区分行',
        'channel': '行政处罚',
        'url': 'http://nanning.pbc.gov.cn/nanning/133346/133364/133371/5512959/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="zwgk1 portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行海南省分行',
        'channel': '行政处罚',
        'url': 'http://haikou.pbc.gov.cn/haikou/132982/133000/133007/5485279/52efe36c/index1.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[4]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行重庆市分行',
        'channel': '行政处罚',
        'url': 'http://chongqing.pbc.gov.cn/chongqing/107680/107897/107909/5525107/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行四川省分行',
        'channel': '行政处罚',
        'url': 'http://chengdu.pbc.gov.cn/chengdu/129320/129341/129350/5498158/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="border1 portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行贵州省分行',
        'channel': '行政处罚',
        'url': 'http://guiyang.pbc.gov.cn/guiyang/113288/113306/113313/5503826/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行云南省分行',
        'channel': '行政处罚',
        'url': 'http://kunming.pbc.gov.cn/kunming/133736/133760/133767/5505423/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_xpath': '//td[@class="hei14jj"]/table/tbody/tr//text()'
    },
    {
        'website_name': '中国人民银行西藏自治区分行',
        'channel': '行政处罚',
        'url': 'http://lasa.pbc.gov.cn/lasa/120480/120504/120511/5517088/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行陕西省分行',
        'channel': '行政处罚',
        'url': 'http://xian.pbc.gov.cn/xian/129428/129449/129458/5518196/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行甘肃省分行',
        'channel': '行政处罚',
        'url': 'http://lanzhou.pbc.gov.cn/lanzhou/117067/117091/117098/5518435/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行青海省分行',
        'channel': '行政处罚',
        'url': 'http://xining.pbc.gov.cn/xining/118239/118263/118270/5513655/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行宁夏回族自治区分行',
        'channel': '行政处罚',
        'url': 'http://yinchuan.pbc.gov.cn/yinchuan/119983/120001/120008/5521152/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="fywz portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行新疆维吾尔自治区分行',
        'channel': '行政处罚',
        'url': 'http://wulumuqi.pbc.gov.cn/wulumuqi/121755/121777/121784/5521433/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class="fywz portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行深圳市分行',
        'channel': '行政处罚',
        'url': 'http://shenzhen.pbc.gov.cn/shenzhen/122811/122833/122840/index1.html',
        'end_page': 29,
        'rows_xpath': '//table[@class="fywz portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行大连市分行',
        'channel': '行政处罚',
        'url': 'http://dalian.pbc.gov.cn/dalian/123812/123830/123837/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]/tbody/tr[1]/td/table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行宁波市分行',
        'channel': '行政处罚',
        'url': 'http://ningbo.pbc.gov.cn/ningbo/127076/127098/127105/index.html',
        'end_page': 2,
        'rows_xpath': '//table[@class="fywz portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行青岛市分行',
        'channel': '行政处罚',
        'url': 'http://qingdao.pbc.gov.cn/qingdao/126166/126184/126191/index.html',
        'end_page': 4,
        'rows_xpath': '//table[@class="fywz portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]/tbody/tr[1]/td/table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
    {
        'website_name': '中国人民银行厦门市分行',
        'channel': '行政处罚',
        'url': 'http://xiamen.pbc.gov.cn/xiamen/127703/127721/127728/index.html',
        'end_page': 1,
        'rows_xpath': '//table[@class=" portlet"]/tbody/tr/td/table[position()>=4 and position()<=last()]//table',
        'content_href_xpath': '//td[@class="hei14jj"]/p/a/@href'
    },
]
