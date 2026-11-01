The product team wants to analyze customer review quality across product categories to prioritize product improvement efforts. Query WooCommerce product review data and link it to product categories to understand how different categories perform with customers.

Create an Excel file called Product_Review_Analysis.xlsx with two sheets. The first sheet should be called "Category Analysis" with columns: Category, Product_Count, Review_Count, Avg_Rating (rounded to 2 decimal places), Five_Star_Count, and Five_Star_Rate (the percentage of reviews that are 5 stars, rounded to 1 decimal). Sort by Category alphabetically. The second sheet should be called "Top Products" and list the top 10 highest-rated products that have at least 3 reviews, with columns: Product_Name (truncated to 50 characters if needed), Category, Review_Count, and Avg_Rating (rounded to 2 decimal places). Sort by Avg_Rating descending, then Review_Count descending.

Create a Notion database called "Product Review Insights" with properties for Category (title), Product_Count (number), Review_Count (number), Avg_Rating (number), and Five_Star_Rate (number). Populate it with one entry per category from the Category Analysis sheet.

Email the analysis to product_team@store.com with subject "Product Review Analysis Report" and include a summary of which categories have the highest and lowest ratings in the email body.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, use two genuine dependency waves with exactly three sub-agents total. The first agent computes the complete store join once; the two artifact writers then run in parallel from one canonical category table.

1. Wave 1 — dispatch exactly 1 Explore sub-agent:

   1. explore 0 (enterprise-data-analyst 0): Use one Explore sub-agent to retrieve the complete product and review endpoints read-only using `perPage=100` and increasing pages until each has a short or empty terminal page. Omit the optional review `status` argument, preserve every observed status, and filter only as the original task requires. Join strictly by Product_ID; a product contributes to each observed category exactly according to its source categories. Compute the compact per-category Product_Count, Review_Count, rating sum/average, Five_Star_Count/Rate, and the eligible products with at least three reviews. Rank Top Products by average rating descending, review count descending, then stable Product_ID. Return the full compact category and top-ten tables directly, plus endpoint page/row/status controls, join/category coverage, and duplicate/tie checks. Do not modify the store or create deliverables.

After Wave 1, the main agent independently checks the counts, rates, rankings, and tie order, then freezes one immutable category/top-product handoff for both writers.

2. Wave 2 — dispatch exactly 3 Coder sub-agents in parallel:

   1. coder 0 (office-report-builder 0): Use one Coder sub-agent as the sole writer of `Product_Review_Analysis.xlsx`. Create the exact two sheets once from the frozen tables, with exact headers, truncation, sorting, row limits, rounding, and literal values. Read both sheets back and return the path plus complete row/value controls.

   2. coder 1 (external-workflow-operator 0): Use one Coder sub-agent as the sole owner of the exact-title `Product Review Insights` database. Search exact title once first and reuse an exact match, otherwise create the database once with the exact property types; then create exactly one page per frozen category, sending each page in a SINGLE create call that carries all its properties together — never update properties one at a time, never re-read pages between inserts, and do not verify row-by-row. When all rows are inserted, issue ONE final database query to confirm the row count, and return the database ID, property names and final row count. Do not write the workbook.

   3. coder 2 (external-workflow-operator 1): Use one Coder sub-agent as the sole owner of the summary email to product_team@store.com with the exact task subject: body built ONLY from the frozen tables — the total product/review counts, the highest-rated and lowest-rated categories with their average ratings and five-star rates, and the complete per-category breakdown. Paginate Sent search and match the exact recipient/subject before an at-most-once send, then read the retained message back and return its ID. Do not write the workbook or database.

After all three writers return, reconcile every category across source, workbook, database and the sent message against the same frozen tables. Read back all three outputs. Repairs belong only to the original writer, and there is no separate validation wave.

After the final wave completes, do not invoke the agent-dispatch tool again — not even an empty or exploratory dispatch attempt (a dispatch that returns zero agents is wasted work). Any remaining checks, emails or small writes are main-agent direct work completed in one pass.