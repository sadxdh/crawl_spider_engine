-- ============================================================================
-- 北交所官网「规则」栏目 采集结果表 DDL
-- 爬虫: spiders/law/law_regulations/bse_rules_spider.py  (data_table = 'bse_rule')
-- 库  : crawl_data (config/dev.ini [MYSQL])
-- 状态: rule_status/implement_date/issue_number/rule_category/rule_level
--       仅业务规则详情页有（-a fetch_detail=1 抓取），其余栏目为空
-- 去重: md5_value = md5(标题 + 发布日期 + 链接), UNIQUE
-- ============================================================================
CREATE TABLE IF NOT EXISTS `bse_rule` (
  `id`             int unsigned NOT NULL AUTO_INCREMENT,
  `created_time`   datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time`   datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `md5_value`      char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '去重md5(title+日期+url)',
  `title`          varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '规则/法规/指南 标题',
  `publish_time`   date DEFAULT NULL COMMENT '发布日期',
  `rule_status`    varchar(50) DEFAULT NULL COMMENT '时效性(现行有效/已废止/已失效/已修改等, 仅业务规则)',
  `implement_date` date DEFAULT NULL COMMENT '实施日期',
  `issue_number`   varchar(100) DEFAULT NULL COMMENT '发文字号, 如 北证公告〔2025〕8号',
  `rule_category`  varchar(100) DEFAULT NULL COMMENT '规则类别, 如 发行融资',
  `rule_level`     varchar(100) DEFAULT NULL COMMENT '业务规则层级, 如 业务细则/业务指引/业务指南',
  `url`            varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '详情页链接',
  `file_url`       varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '附件下载链接(pdf/docx)',
  `source`         varchar(50) DEFAULT NULL COMMENT '数据源(北交所)',
  `channel_id`     varchar(20) DEFAULT NULL COMMENT '栏目节点id(#curNodeId)',
  `channel_name`   varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '栏目名(最细一级)',
  `tag_path`       varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '完整层级路径, 如 规则/业务规则/股票/发行上市审核',
  `level_1`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '一级标签(规则)',
  `level_2`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '二级标签(法律规则/业务规则)',
  `level_3`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '三级标签',
  `level_4`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '四级标签',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_md5_value` (`md5_value`) USING BTREE,
  KEY `idx_publish_time` (`publish_time`),
  KEY `idx_rule_status` (`rule_status`),
  KEY `idx_level2` (`level_2`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='北交所规则栏目采集(法律规则/业务规则)';
