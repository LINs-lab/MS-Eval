I am a wellness researcher studying the nutritional value of traditional Chinese cooking. A nutrition reference file called nutrition_reference.json is available in the workspace, containing calorie and macronutrient data for common Chinese cooking ingredients.

Please browse the recipe database and select 5 dishes from at least 3 different categories. Then search for academic papers related to Chinese diet and health or traditional Asian cuisine nutrition. I expect to find about 4 relevant papers. For each selected dish, estimate its nutritional content using the ingredient data from the reference file.

Create an Excel spreadsheet called Health_Diet_Analysis.xlsx with the following three sheets. The first sheet should be named "Recipe Nutrition" with columns Dish_Name, Category, Estimated_Calories, Protein_g, Fat_g, Carbs_g, and Health_Rating. The Health_Rating should be Low, Medium, or High based on the calorie density of the dish. The second sheet should be named "Research Summary" with columns Paper_Title, Authors, Year, Citation_Count, and Key_Finding. The third sheet should be named "Combined Analysis" with columns Dish_Name, Health_Rating, and Supporting_Research, linking the dishes to relevant research findings.

Also create a Word document called Chinese_Cuisine_Health_Report.docx. The document should have the title "Nutritional Analysis of Traditional Chinese Cuisine" and include the following sections: Introduction, Recipe Analysis, Literature Review, and Conclusions.

Notes on expected output format:
- All numeric values in the spreadsheet (Estimated_Calories, Protein_g, Fat_g, Carbs_g, Citation_Count, Year) must be written as literal numbers, not as Excel formulas.
- "About 4 papers" is flexible: a Research Summary with 3 to 5 papers is acceptable. Only include papers that are genuinely related to Chinese diet and health or Asian cuisine nutrition.
- Assign Health_Rating as Low, Medium, or High based on the calorie density of each dish (e.g., Low for low-calorie dishes, Medium for moderate, High for calorie-dense dishes).

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, run the three genuinely independent read branches (nutrition reference, recipe database, scholarly literature) in one parallel wave, then the two independent artifact writers in a second wave. No planning sub-agent.

Wave 1 — dispatch exactly 3 explore sub-agents in parallel:

1. explore 0 (enterprise-data-analyst 0): The nutrition-reference explorer lists the workspace to confirm nutrition_reference.json, reads and parses it completely, and returns its exact ingredient schema (per-100g calories, protein, fat, carbs keys) plus the count of covered ingredients and any missing/ambiguous entries. Read-only; do not write artifacts.
2. explore 1 (web-domain-researcher 0): The recipe explorer browses the Chinese recipe database via the howtocook tools (getAllRecipes / getRecipesByCategory; categories such as 水产, 早餐, 调料, 甜品, 饮品, 荤菜, 素菜, 汤羹), selects exactly five suitable dishes from at least three different categories, and returns each dish's full Chinese name, category, and complete ingredient list with quantities, plus category/count controls. Read-only; do not write artifacts.
3. explore 2 (academic-literature-researcher 0): The literature explorer searches the scholarly tools (search-arxiv / search-google-scholar) for papers on Chinese diet and health or traditional Asian cuisine nutrition, targets about 4 relevant papers (3-5 acceptable, ONLY genuinely diet/nutrition/health-related), and returns exact title, authors, year, citation count, key finding, identifier, and relevance evidence for each paper. Read-only; do not write artifacts.

After Wave 1, the main agent reconciles all three handoffs in one pass: joins the five dishes to the nutrition reference to compute per-dish calories, protein, fat and carbohydrates (per-100g basis with quantity scaling, calculation notes retained), and assigns source-supported Low/Medium/High calorie-density ratings. It freezes one canonical packet of five dish rows, the nutrition schema, and the paper list.

Wave 2 — dispatch exactly 2 coder sub-agents in parallel:

1. coder 0 (office-report-builder 0): The workbook coder sole-writes Health_Diet_Analysis.xlsx in the workspace (python openpyxl preferred, Excel MCP tools as fallback) with EXACTLY three sheets in order — the dish nutrition table (dish, category, calories, protein, fat, carbs, calorie-density rating), the paper evidence table, and a summary sheet — using literal numeric values from the frozen packet, then reads the file back and returns sheet names, row counts and validation.
2. coder 1 (office-report-builder 1): The document coder sole-writes Chinese_Cuisine_Health_Report.docx in the workspace (python-docx preferred, Word MCP tools as fallback) with the required title, methodology, per-dish findings, literature support and conclusion sections, citing only frozen papers, then reads the document text/outline back and returns validation.

After Wave 2, the main agent reconciles both read-backs against the same canonical packet and calls claim_done. Do not dispatch any further agent and do not add a verification wave.
