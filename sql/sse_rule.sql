-- ============================================================================
-- 上交所官网「规则」栏目 采集结果表 DDL
-- 爬虫: spiders/law/law_regulations/sse_rules_spider.py  (data_table = 'sse_rule')
-- 库  : crawl_data (config/dev.ini [MYSQL])
-- 字段与爬虫 yield 的 item 一一对应；spider_name / crawl_time 由 Pipeline 处理
-- 去重: md5_value = md5(标题 + 发布日期 + 链接), UNIQUE
-- ============================================================================
CREATE TABLE IF NOT EXISTS `sse_rule` (
  `id`           int unsigned NOT NULL AUTO_INCREMENT,
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `md5_value`    char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '去重md5(title+日期+url)',
  `title`        varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '规则/法规/指南 标题',
  `publish_time` date DEFAULT NULL COMMENT '发布日期',
  `rule_status`  varchar(20) DEFAULT NULL COMMENT '法规状态: 现行有效/已废止/废止公告/已下线',
  `rule_type`    varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '规则类型(A型:基本业务规则/自律监管指引/业务指引/业务细则/业务通知/两板通用规则; B型:栏目名; 已废止规则文本=年份)',
  `url`          varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '原文/附件链接',
  `source`       varchar(50) DEFAULT NULL COMMENT '数据源(上交所)',
  `channel_id`   varchar(20) DEFAULT NULL COMMENT '栏目ID(全站菜单SSE_MENU_28)',
  `channel_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '所属栏目名(最细一级)',
  `tag_path`     varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '完整层级路径, 如 规则/本所业务规则/股票/发行上市审核/首发',
  `level_1`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '一级标签(规则)',
  `level_2`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '二级标签(法律法规/部门规章/本所业务规则/本所业务指南与流程/公开征求意见/制度规则汇编)',
  `level_3`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '三级标签',
  `level_4`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '四级标签',
  `level_5`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '五级标签',
  `level_6`      varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '六级标签',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_md5_value` (`md5_value`) USING BTREE,
  KEY `idx_publish_time` (`publish_time`),
  KEY `idx_tag_path` (`tag_path`(190)),
  KEY `idx_level2` (`level_2`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='上交所规则栏目采集(规则/法律法规/部门规章/指南/征求意见/汇编)';
