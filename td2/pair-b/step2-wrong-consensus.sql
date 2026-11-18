-- TD2 Step 2 (Pair B) - Wrong consensus on C09, from the real TD1 traces (td2/traces-td1.csv, nature = real)
-- Run: sqlite3 td2/data/boutique.sqlite < td2/pair-b/step2-wrong-consensus.sql
-- C09: revenue excl. VAT (cents) from customers aged exactly 25 on 2026-09-26, all their orders.
-- Correct birth window: 2000-09-27 <= birth_date <= 2001-09-26.

.headers on
.mode column

-- 1) Reference (reference-td1.csv) -> 487980
SELECT 'reference' AS q, COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE date(c.birth_date, '+25 years') <= '2026-09-26' AND date(c.birth_date, '+26 years') > '2026-09-26';

-- 2) Faulty query 1: cohere/north-mini-code:free (verbatim from traces, comments removed) -> 0
--    Bug: the "age" expression is birth_year - correction (about 2000-2001), never 2026 - birth_year.
--    Comparing it with 25 is false for every customer.
SELECT 'north-mini-code' AS q, COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN product p ON o.product_id = p.product_id
WHERE ( CAST(SUBSTR(c.birth_date, 1, 4) AS INTEGER)
        - CASE WHEN SUBSTR(c.birth_date, 6, 2) > '09' THEN 1
               WHEN SUBSTR(c.birth_date, 6, 2) = '09' AND SUBSTR(c.birth_date, 9, 2) > '26' THEN 1
               ELSE 0 END ) = 25
  AND SUBSTR(c.birth_date, 6, 5) <= '09-26';

-- 3) Faulty query 2: qwen/qwen3.8-27b (verbatim from traces) -> 0
--    Bug 1: it uses o.date (the order date) instead of the reference date 2026-09-26, which is the F2b logic, not F2.
--    Bug 2: strftime('%m-%d', date(birth, '+26 years')) is the birth month-day again, so the condition
--           "md >= birth_md AND md < birth_md" is a contradiction and keeps no row.
SELECT 'qwen3.8-27b' AS q, COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN product p ON o.product_id = p.product_id
WHERE (strftime('%Y', o.date) - strftime('%Y', c.birth_date)) = 25
  AND (strftime('%m-%d', o.date) >= strftime('%m-%d', c.birth_date))
  AND (strftime('%m-%d', o.date) < strftime('%m-%d', date(c.birth_date, '+26 years')));

-- 4) Delta query: customers counted by the reference and missed by both faulty queries.
--    Both faulty queries keep no row, so the delta is the whole reference set. The total must equal 487980 - 0.
SELECT c.customer_id, c.birth_date,
       COUNT(DISTINCT o.order_id)            AS n_orders,
       SUM(o.quantity_product * p.price)     AS revenue_cents,
       SUM(SUM(o.quantity_product * p.price)) OVER () AS total_gap_cents
FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN product p ON o.product_id = p.product_id
WHERE c.birth_date > '2000-09-26' AND c.birth_date <= '2001-09-26'
GROUP BY c.customer_id, c.birth_date
ORDER BY c.birth_date;

-- 5) Independent check: completed age computed arithmetically, with no date window -> 487980
SELECT 'independent' AS q, SUM(o.quantity_product * p.price) AS revenue_cents
FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN product p ON o.product_id = p.product_id
WHERE (2026 - CAST(substr(c.birth_date, 1, 4) AS INT) - (substr(c.birth_date, 6, 5) > '09-26')) = 25;

-- ---------------------------------------------------------------------------
-- Secondary case C10 (non-zero shared wrong value 119410: qwen3.8-27b + dots-3-note-preview)
-- Reference 558980. Delta = order lines where the customer is 25 at the order date, but the order
-- falls BEFORE the birthday in the calendar year of their 26th birthday (year diff = 26). Both faulty
-- queries only accept year diff = 25. qwen's second branch (year diff = 24) matches 0 rows.
SELECT c.customer_id, c.birth_date, o.order_id, date(o.date) AS order_day,
       SUM(o.quantity_product * p.price) AS revenue_cents,
       SUM(SUM(o.quantity_product * p.price)) OVER () AS total_gap_cents   -- expected 439570 = 558980 - 119410
FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN product p ON o.product_id = p.product_id
WHERE date(c.birth_date, '+25 years') <= date(o.date) AND date(c.birth_date, '+26 years') > date(o.date)
  AND NOT (CAST(strftime('%Y', o.date) AS INT) - CAST(strftime('%Y', c.birth_date) AS INT) = 25
           AND strftime('%m-%d', o.date) >= strftime('%m-%d', c.birth_date))
GROUP BY o.order_id
ORDER BY c.customer_id, order_day;
