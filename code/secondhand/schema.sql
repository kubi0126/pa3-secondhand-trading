-- 校园二手交易系统 SQLite DDL
-- 对应实验二数据设计（MySQL 8.0）的 8 张表；SQLite 不支持 ENUM 与生成列，
-- 改用 CHECK 约束与部分唯一索引表达同样的业务约束。

CREATE TABLE IF NOT EXISTS user (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    phone           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    nickname        TEXT,
    role            TEXT    NOT NULL DEFAULT 'USER'
                            CHECK (role IN ('USER', 'ADMIN')),
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
);

CREATE TABLE IF NOT EXISTS category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    enabled     INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS item_condition (
    condition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    enabled      INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS item (
    item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id    INTEGER NOT NULL REFERENCES user (user_id) ON DELETE RESTRICT,
    category_id  INTEGER NOT NULL REFERENCES category (category_id) ON DELETE RESTRICT,
    condition_id INTEGER NOT NULL REFERENCES item_condition (condition_id) ON DELETE RESTRICT,
    title        TEXT    NOT NULL CHECK (length(title) BETWEEN 1 AND 60),
    description  TEXT,
    price        NUMERIC NOT NULL CHECK (price > 0),
    image_url    TEXT,
    status       TEXT    NOT NULL DEFAULT 'DRAFT'
                         CHECK (status IN ('DRAFT', 'PENDING_REVIEW', 'PUBLISHED',
                                           'RESERVED', 'SOLD', 'DELISTED',
                                           'REJECTED', 'VIOLATION_DELISTED')),
    version      INTEGER NOT NULL DEFAULT 0,
    published_at TEXT,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_item_browse ON item (status, category_id, published_at);
CREATE INDEX IF NOT EXISTS idx_item_price ON item (status, price);
CREATE INDEX IF NOT EXISTS idx_item_seller ON item (seller_id, status, updated_at);

CREATE TABLE IF NOT EXISTS reservation (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id        INTEGER NOT NULL REFERENCES item (item_id) ON DELETE RESTRICT,
    buyer_id       INTEGER NOT NULL REFERENCES user (user_id) ON DELETE RESTRICT,
    status         TEXT    NOT NULL DEFAULT 'PENDING_CONFIRM'
                           CHECK (status IN ('PENDING_CONFIRM', 'CONFIRMED',
                                             'CANCELLED', 'REJECTED',
                                             'EXPIRED', 'COMPLETED')),
    version        INTEGER NOT NULL DEFAULT 0,
    request_id     TEXT,
    cancel_reason  TEXT,
    created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    confirmed_at   TEXT,
    completed_at   TEXT,
    expire_at      TEXT    NOT NULL
);

-- 同一商品同一时刻最多一条有效预约
CREATE UNIQUE INDEX IF NOT EXISTS uk_active_item
    ON reservation (item_id)
    WHERE status IN ('PENDING_CONFIRM', 'CONFIRMED');

-- 同一买家对同一商品最多一条进行中预约
CREATE UNIQUE INDEX IF NOT EXISTS uk_active_buyer_item
    ON reservation (buyer_id, item_id)
    WHERE status IN ('PENDING_CONFIRM', 'CONFIRMED');

CREATE UNIQUE INDEX IF NOT EXISTS uk_reservation_request
    ON reservation (request_id)
    WHERE request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_res_item ON reservation (item_id, status);
CREATE INDEX IF NOT EXISTS idx_res_buyer ON reservation (buyer_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_res_buyer_item ON reservation (buyer_id, item_id, created_at);
CREATE INDEX IF NOT EXISTS idx_res_expire ON reservation (status, expire_at);

CREATE TABLE IF NOT EXISTS audit_record (
    audit_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id    INTEGER NOT NULL REFERENCES item (item_id) ON DELETE RESTRICT,
    admin_id   INTEGER NOT NULL REFERENCES user (user_id) ON DELETE RESTRICT,
    result     TEXT    NOT NULL CHECK (result IN ('APPROVED', 'REJECTED')),
    reason     TEXT,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    CHECK (result = 'APPROVED' OR reason IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_audit_item ON audit_record (item_id, created_at);

CREATE TABLE IF NOT EXISTS operation_log (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id   INTEGER REFERENCES user (user_id) ON DELETE RESTRICT,
    operator_type TEXT    NOT NULL DEFAULT 'USER'
                          CHECK (operator_type IN ('USER', 'SYSTEM')),
    target_type   TEXT    NOT NULL CHECK (target_type IN ('ITEM', 'RESERVATION')),
    target_id     INTEGER NOT NULL,
    action        TEXT    NOT NULL,
    result        TEXT    NOT NULL CHECK (result IN ('SUCCESS', 'FAILED')),
    detail        TEXT,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_log_time ON operation_log (created_at);
CREATE INDEX IF NOT EXISTS idx_log_operator ON operation_log (operator_id, created_at);
CREATE INDEX IF NOT EXISTS idx_log_target ON operation_log (target_type, target_id, created_at);

CREATE TABLE IF NOT EXISTS request_log (
    request_id  TEXT    PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES user (user_id) ON DELETE RESTRICT,
    endpoint    TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK (status IN ('PROCESSING', 'SUCCESS', 'FAILED')),
    result_json TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_req_user_time ON request_log (user_id, created_at);
