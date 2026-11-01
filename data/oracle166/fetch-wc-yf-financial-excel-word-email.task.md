I need help with a wc yf finance analysis. There is external benchmark data available that I need you to fetch the data from http://localhost:30333/api/data.json and extract the relevant metrics.

Then check our online store for current product and order data.

Use the terminal to create and run a Python script called wc_yf_finance_processor.py in the workspace that reads the collected data from JSON files you create, performs the analysis, and outputs wc_yf_finance_results.json.

Create an Excel file called Yf_Financial_Report.xlsx with three sheets. The first sheet Data_Analysis should contain the main comparison data with relevant columns. The second sheet Metrics should summarize key metrics. The third sheet Recommendations should list actionable items.

The Data_Analysis sheet should have columns: Category, Our_Avg_Price, Market_Avg_Price, Price_Gap_Pct. Sort the data alphabetically by Category. The Metrics sheet should have two columns Metric and Value summarizing total counts, averages, and key statistics. The Recommendations sheet should list priority actions based on the gap analysis. Also create a Word document called Yf_Financial_Analysis.docx with an executive summary, key findings, and recommendations sections. Send an email to team-lead@company.com with subject "Analysis Report Complete" summarizing the key findings.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, keep read-only source gathering on explore, keep the processor on one local writer, then parallelize the two independent final artifacts. A wave must finish and return all stated handoffs before the next wave begins. Explore sub-agents must not write files; the processor coder uniquely owns the JSON inputs and script.

1. Wave 1 — dispatch exactly 2 explore sub-agents in parallel:

   1. explore 0 (web-domain-researcher 0): One explore sub-agent fetches `http://localhost:30333/api/data.json` exactly once and returns the complete benchmark payload with field and count controls. Do not query WooCommerce, write files, or run the processor.
   2. explore 1 (enterprise-data-analyst 0): One explore sub-agent exhausts the required WooCommerce products and orders with `perPage` at most 100 and terminal-page checks. Paginate `woo_products_list` and `woo_orders_list` with increasing literal `page` until a short or empty terminal page proves exhaustion; omit the optional order `status` and preserve every observed status. Return compact product and order records plus page/count/null/duplicate controls. Do not modify the store, write files, or run the processor.

After Wave 1, the main agent must verify both source identities, schemas, and coverage, then freeze the two literal payloads. Missing or ambiguous source data is a blocker.

2. Wave 2 — dispatch exactly 1 coder sub-agent:

   1. coder 0 (office-report-builder 0): The coder sub-agent receives both frozen payloads and uniquely owns the required JSON inputs, `wc_yf_finance_processor.py`, and `wc_yf_finance_results.json`. Derive only source-supported category comparisons. Run and read back the processor result, then return its path/hash, source/page/count controls, eligible categories, exact metrics, and schema checks. It must not fetch localhost or WooCommerce and must not create Excel or Word outputs.

After Wave 2, the main agent must verify the source coverage and freeze the exact processor result. In the same response as Wave 3, it may start the nonduplicate `Analysis Report Complete` email branch using only those verified findings.

3. Wave 3 — dispatch exactly 2 coder sub-agents in parallel:

   1. coder 0 (office-report-builder 1): One coder sub-agent is the sole writer of `Yf_Financial_Report.xlsx`. Read only the verified processor result. Create exactly `Data_Analysis`, `Metrics`, and `Recommendations`: `Data_Analysis` has literal columns `Category, Our_Avg_Price, Market_Avg_Price, Price_Gap_Pct` sorted alphabetically by Category; `Metrics` has `Metric, Value` with source-reconciled counts, averages, and key statistics; `Recommendations` contains source-supported priority actions. Write literal values and read back every populated range.
   2. coder 1 (office-report-builder 2): One coder sub-agent is the sole writer of `Yf_Financial_Analysis.docx`. Read only the verified processor result. Create the required executive summary, key findings, and recommendations sections, ground every quantitative claim in the result, and read back its heading structure, tables, and full text.

After Wave 3, the main agent reconciles both reports to the same result hash and verifies exactly one email to `team-lead@company.com` with subject `Analysis Report Complete`. Do not dispatch more sub-agents.
