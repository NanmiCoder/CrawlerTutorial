create table symbol_content
(
    `id`             int          NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `symbol`         varchar(255) DEFAULT NULL COMMENT '货币',
    `name`           varchar(255) DEFAULT NULL COMMENT '名称',
    `price`          varchar(255) DEFAULT NULL COMMENT '价格盘中',
    `change_price`   varchar(255) DEFAULT NULL COMMENT '跌涨价格',
    `change_percent` varchar(255) DEFAULT NULL COMMENT '跌涨百分比',
    `market_price`   varchar(255) DEFAULT NULL COMMENT '市值',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='';;