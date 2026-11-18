-- Prototype orchestrator, ESILV "Next-Generation AI" (task 1572).
-- Three tables, exactly as specified. Prices are euro cents excluding VAT.
-- orders.date and customers.insert_date: UTC timestamps 'YYYY-MM-DD HH:MM:SS'.
-- customers.birth_date: date 'YYYY-MM-DD'.
CREATE TABLE product (
    product_id TEXT PRIMARY KEY,
    price INTEGER NOT NULL CHECK (price >= 0)
);
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    insert_date TEXT NOT NULL,
    birth_date TEXT NOT NULL
);
CREATE TABLE orders (
    date TEXT NOT NULL,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    product_id TEXT NOT NULL REFERENCES product(product_id),
    quantity_product INTEGER NOT NULL CHECK (quantity_product > 0),
    PRIMARY KEY (order_id, product_id)
);
