-- cs-crew 가게 데이터. 모든 값은 가짜다. make seed가 매번 같게 다시 만든다.
PRAGMA foreign_keys = ON;

CREATE TABLE stores   (id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL);
CREATE TABLE users    (id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id),
                       role TEXT NOT NULL CHECK (role IN ('customer','staff','manager')),
                       name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, vip INTEGER NOT NULL DEFAULT 0);
CREATE TABLE products (id INTEGER PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id),
                       name TEXT NOT NULL, price_krw INTEGER NOT NULL, stock INTEGER NOT NULL);
CREATE TABLE orders   (id INTEGER PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id),
                       customer_id TEXT NOT NULL REFERENCES users(id),
                       status TEXT NOT NULL CHECK (status IN ('paid','shipped','delivered','cancelled')),
                       total_krw INTEGER NOT NULL, address TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id),
                       qty INTEGER NOT NULL, price_krw INTEGER NOT NULL);
CREATE TABLE shipments (order_id INTEGER PRIMARY KEY REFERENCES orders(id), carrier TEXT NOT NULL, tracking_no TEXT NOT NULL);
CREATE TABLE refunds  (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), amount_krw INTEGER NOT NULL,
                       reason TEXT NOT NULL, status TEXT NOT NULL, requested_by TEXT NOT NULL,
                       approved_by TEXT, approved_by_2 TEXT, created_at TEXT NOT NULL);
CREATE TABLE coupons  (id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES users(id), amount_krw INTEGER NOT NULL,
                       reason TEXT NOT NULL, status TEXT NOT NULL, approved_by TEXT, created_at TEXT NOT NULL);
-- 승인 대기열(6-1). run_state_json은 SDK RunState.to_json(), diff·risk·approvers는 학생의 crew/guards/approval.py가 채운다(6-4·6-5)
CREATE TABLE approvals (id INTEGER PRIMARY KEY, action TEXT NOT NULL, payload_json TEXT NOT NULL, run_state_json TEXT,
                       diff TEXT, risk TEXT NOT NULL DEFAULT 'unknown', status TEXT NOT NULL DEFAULT 'pending',
                       decided_by TEXT, decided_at TEXT, created_at TEXT NOT NULL,
                       run_id TEXT, user_id TEXT, store_id TEXT, summary TEXT, approvers INTEGER NOT NULL DEFAULT 1,
                       decided_by_2 TEXT, result TEXT);
CREATE TABLE delegations (token_id TEXT PRIMARY KEY, staff_id TEXT NOT NULL REFERENCES users(id), store_id TEXT NOT NULL,
                       scopes TEXT NOT NULL, purpose TEXT NOT NULL, expires_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE docs     (id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id),
                       visibility TEXT NOT NULL CHECK (visibility IN ('public','internal')),
                       trust TEXT NOT NULL CHECK (trust IN ('official','uploaded')), title TEXT NOT NULL, body TEXT NOT NULL);
CREATE VIRTUAL TABLE docs_fts USING fts5(id UNINDEXED, title, body, tokenize = 'trigram');
CREATE TABLE tickets  (id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES users(id),
                       channel TEXT NOT NULL CHECK (channel IN ('chat','email')), subject TEXT NOT NULL, body TEXT NOT NULL,
                       status TEXT NOT NULL DEFAULT 'open', assigned_agent TEXT, created_at TEXT NOT NULL);
CREATE TABLE memories (id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES users(id), text TEXT NOT NULL,
                       source TEXT NOT NULL CHECK (source IN ('customer','staff','agent')),
                       trust TEXT NOT NULL CHECK (trust IN ('confirmed','unverified')), created_at TEXT NOT NULL, expires_at TEXT,
                       run_id TEXT, reviewed_by TEXT);  -- 8-1~8-4: run_id는 어느 대화가 썼나(되돌리기), reviewed_by는 확인한 직원
CREATE TABLE outbox   (id INTEGER PRIMARY KEY, to_email TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE audit_log (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, run_id TEXT NOT NULL, user_id TEXT, agent TEXT NOT NULL,
                       action TEXT NOT NULL, detail TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE usage    (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, agent TEXT NOT NULL, model TEXT NOT NULL,
                       tokens_in INTEGER NOT NULL, tokens_out INTEGER NOT NULL, cost_usd REAL NOT NULL,
                       user_id TEXT, run_id TEXT);  -- 12-4: 사용자별 요금 차단
CREATE TABLE lab_flags (name TEXT PRIMARY KEY, value TEXT NOT NULL);
