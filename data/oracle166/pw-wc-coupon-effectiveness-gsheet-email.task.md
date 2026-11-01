I need help with a wc coupons analysis. There is external benchmark data available that I need you to visit http://localhost:30309 and extract the relevant metrics.

Then check our online store for current product and order data.

Use the terminal to create and run a Python script called wc_coupons_processor.py in the workspace that reads the collected data from JSON files you create, performs the analysis, and outputs wc_coupons_results.json.

Create an Excel file called Coupon_Effectiveness_Report.xlsx with three sheets. The first sheet Data_Analysis should contain the main comparison data with relevant columns. The second sheet Metrics should summarize key metrics. The third sheet Recommendations should list actionable items.

The Data_Analysis sheet should have columns: Category, Product_Count, Our_Avg_Price, Total_Sales, Market_Avg_Price, Price_Gap_Pct. Sort the data alphabetically by Category. The Metrics sheet should have two columns Metric and Value summarizing total counts, averages, and key statistics. The Recommendations sheet should list priority actions based on the gap analysis. Send an email to team-lead@company.com with subject "Analysis Report Complete" summarizing the key findings. Create a Google Sheet called "Wc Coupons Tracker" with the key data points.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, keep read-only source gathering on explore, keep the processor on one local writer, then parallelize the independent local workbook and cloud spreadsheet. A wave must finish and return all stated handoffs before the next wave begins. Explore sub-agents must not write files; the processor coder uniquely owns the JSON inputs and script.

1. Wave 1 — dispatch exactly 2 explore sub-agents in parallel:

   1. explore 0 (web-domain-researcher 0): One explore sub-agent reads the complete benchmark at `http://localhost:30309` exactly once and returns the complete benchmark payload with field and count controls. Do not query WooCommerce, write files, or run the processor.
   2. explore 1 (enterprise-data-analyst 0): One explore sub-agent exhausts the required WooCommerce products and orders with `perPage` at most 100 and terminal-page checks. Paginate `woo_products_list` and `woo_orders_list` with increasing literal `page` until a short or empty terminal page proves exhaustion; omit the optional order `status` and preserve every observed status. Return compact product and order records plus page/count/null/duplicate controls. Do not modify the store, write files, or run the processor.

After Wave 1, the main agent must verify both source identities, schemas, and coverage, then freeze the two literal payloads. Missing or ambiguous source data is a blocker.

2. Wave 2 — dispatch exactly 1 coder sub-agent:

   1. coder 0 (office-report-builder 0): The coder sub-agent receives both frozen payloads and uniquely owns the required JSON inputs, `wc_coupons_processor.py`, and `wc_coupons_results.json`. Produce exact alphabetical category rows with `Product_Count`, `Our_Avg_Price`, `Total_Sales`, `Market_Avg_Price`, and `Price_Gap_Pct`, plus metrics and supported recommendations. Run and read back the result, then return its path/hash, source/page/count controls, eligible categories, and schema checks. It must not fetch localhost or WooCommerce and must not create the final Excel or Google Sheet.

After Wave 2, the main agent must verify and freeze the processor result. In the same response as Wave 3, it may start the nonduplicate `Analysis Report Complete` email branch using only verified findings.

3. Wave 3 — dispatch exactly 2 coder sub-agents in parallel:

   1. coder 0 (office-report-builder 1): One coder sub-agent is the sole writer of `Coupon_Effectiveness_Report.xlsx`. Read only the verified result. Create exactly `Data_Analysis`, `Metrics`, and `Recommendations`: `Data_Analysis` has literal columns `Category, Product_Count, Our_Avg_Price, Total_Sales, Market_Avg_Price, Price_Gap_Pct` sorted alphabetically by Category; `Metrics` has `Metric, Value`; `Recommendations` contains source-supported priority actions. Write literal values and read back every populated range.
   2. coder 1 (external-workflow-operator 0): One coder sub-agent is the sole owner of the Google Sheet `Wc Coupons Tracker`. Read only the verified result, exhaust `search_spreadsheets` for the exact title, create it once only when absent, and block on multiple exact matches. Write the exact alphabetical category rows with `Category, Product_Count, Our_Avg_Price, Total_Sales, Market_Avg_Price, Price_Gap_Pct` plus a compact verified metrics section, then read both ranges back.

After Wave 3, the main agent reconciles the Excel and Google Sheet to the same result hash and verifies exactly one email to `team-lead@company.com` with subject `Analysis Report Complete`. Do not dispatch more sub-agents.
