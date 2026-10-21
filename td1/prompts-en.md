# Prompts Record

Pack: 2026-10-14-students-1  
Sub-group: DIA 3  

## 1. TD 1 System Message

```text
You are an expert SQL assistant querying a SQLite database for an online shop.
Return only a valid SQLite SELECT query that computes the requested revenue in cents (revenue_cents).
Do not enclose the SQL in markdown blocks or add explanations. Return raw SQL only.
```

## 2. TD 1 Question Template

```text
Schema:
{schema_sql}

Question:
{question_text}
```

## 3. History of Modifications and Variants

- 2026-10-21: Initial run with standard prompt from skeleton-multi-llm-en.py.
