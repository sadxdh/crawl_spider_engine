-- ============================================================================
-- 市场监管总局官网「法律法规」栏目 采集结果表 DDL
-- 爬虫: spiders/law/law_regulations/samr_rules_spider.py  (data_table = 'samr_rule')
-- 库  : crawl_data (config/dev.ini [MYSQL])
-- 说明: 本站详情页无 时效性/状态 标记, 故无 rule_status 列(对账用 已下线 状态)
-- 去重: md5_value = md5(标题 + 发布日期 + 链接), UNIQUE
-- ============================================================================
CREATE TABLE IF NOT EXISTS `samr_rule` (
  `id`           int unsigned NOT NULL AUTO_INCREMENT,
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `md5_value`    char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '去重md5(title+日期+url)',
  `title`        varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '法规标题',
  `publish_time` date DEFAULT NULL COMMENT '发布日期',
  `url`          varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '原文链接',
  `source`       varchar(50) DEFAULT NULL COMMENT '数据源(市场监管总局)',
  `channel_id`   varchar(50) DEFAULT NULL COMMENT '栏目pageId(ColId)',
  `channel_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '栏目名(法律/行政法规)',
  `tag_path`     varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '完整层级路径, 如 市场监管总局/法律法规/法律',
  `rule_status`  varchar(20) DEFAULT NULL COMMENT '状态(对账时置 已下线)',
  `level_1`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '一级标签(市场监管总局)',
  `level_2`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '二级标签(法律法规)',
  `level_3`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '三级标签(法律/行政法规)',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_md5_value` (`md5_value`) USING BTREE,
  KEY `idx_publish_time` (`publish_time`),
  KEY `idx_level2` (`level_2`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='市场监管总局法律法规栏目采集(法律/行政法规)';
