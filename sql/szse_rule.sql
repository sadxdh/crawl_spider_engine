-- ============================================================================
-- 深交所官网「法律规则」栏目 采集结果表 DDL
-- 爬虫: spiders/law/law_regulations/szse_rules_spider.py  (data_table = 'szse_rule')
-- 库  : crawl_data (config/dev.ini [MYSQL])
-- 状态: rule_status = 现行有效 / 已废止 / 废止公告 / 空(指南、征求意见)
--        invalid_reason = 已废止规则的失效依据(替代规则标题, 抓详情页获得)
-- 去重: md5_value = md5(标题 + 发布日期 + 链接), UNIQUE
-- ============================================================================
CREATE TABLE IF NOT EXISTS `szse_rule` (
  `id`             int unsigned NOT NULL AUTO_INCREMENT,
  `created_time`   datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time`   datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `md5_value`      char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '去重md5(title+日期+url)',
  `title`          varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '规则/法规/指南 标题',
  `publish_time`   date DEFAULT NULL COMMENT '发布日期',
  `rule_status`    varchar(20) DEFAULT NULL COMMENT '法规状态: 现行有效/已废止/废止公告/空',
  `invalid_reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '失效依据(已废止规则的替代规则标题)',
  `url`            varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '原文/附件链接',
  `source`         varchar(50) DEFAULT NULL COMMENT '数据源(深交所)',
  `channel_id`     varchar(100) DEFAULT NULL COMMENT '栏目channelCode(currentMenuId)',
  `channel_name`   varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '栏目名(最细一级)',
  `navigation`     varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '网站面包屑,如 本所业务规则-固收类-资产支持证券',
  `tag_path`       varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '完整层级路径, 如 法律规则/本所业务规则/股票类/发行上市审核',
  `level_1`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '一级标签(法律规则)',
  `level_2`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '二级标签(法律法规/部门规章/本所业务规则/业务指南与流程/公开征求意见)',
  `level_3`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '三级标签',
  `level_4`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '四级标签',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_md5_value` (`md5_value`) USING BTREE,
  KEY `idx_publish_time` (`publish_time`),
  KEY `idx_rule_status` (`rule_status`),
  KEY `idx_level2` (`level_2`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='深交所法律规则栏目采集(法律法规/部门规章/本所业务规则/指南/征求意见)';
