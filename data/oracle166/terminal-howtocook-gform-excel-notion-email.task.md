You are a corporate wellness coordinator responsible for launching an employee lunch program. Your goal is to create a dietary preference survey, select recipes that match common employee preferences, plan a weekly menu, build a recipe knowledge base, and communicate the program to staff.

Start by reading the Cafeteria_Budget.pdf in your workspace, which describes the budget per meal and expected headcount. Also review the dietary_requirements.json file that lists common dietary restrictions and allergen considerations for the employee population.

Create a dietary preference survey using the forms platform. The survey should be titled "Employee Lunch Program Preferences" and include the following five questions: a multiple choice question asking about preferred cuisine type with options Chinese Meat Dishes, Chinese Vegetable Dishes, Chinese Staple Foods, Soups, and Seafood; a multiple choice question about spice tolerance with options Mild, Medium, and Spicy; a multiple choice question about dietary restrictions with options Vegetarian, No Pork, No Seafood, Gluten Free, and No Restrictions; a short text question asking how important variety is in their lunch options (rate on a scale of 1 to 5); and a short text question for any additional food preferences or allergies.

Query the recipe database to find recipes across different categories. Search for at least two meat dishes, two vegetable dishes, one staple food, one soup, and one seafood dish. For each recipe retrieved, note the recipe name, category, difficulty level, and ingredients list.

Write a Python script called menu_planner.py in your workspace and execute it using command-line tools. The script should select five recipes for a Monday through Friday weekly menu, choosing recipes that balance different categories (no two consecutive days with the same category) and keeping difficulty at 4 or below for cafeteria feasibility. The script should estimate a cost per serving of 8 dollars for meat and seafood dishes, 5 dollars for vegetable dishes, 6 dollars for staple foods, and 4 dollars for soups, then compute the total weekly cost assuming 50 servings per day.

Create an Excel workbook called Meal_Program_Plan.xlsx in your workspace with four sheets.

The first sheet should be named Survey_Questions and contain columns for question_num, text, and type. Include one row for each of the five survey questions.

The second sheet should be named Recipe_Selection and contain columns for recipe_name, category, and difficulty. Include one row for each recipe you retrieved from the recipe database, with at least seven recipes total. Record the recipe name and category exactly as returned by the recipe database.

The third sheet should be named Weekly_Menu and contain columns for day, lunch_recipe, and estimated_cost. Include five rows, one for each weekday Monday through Friday, with the assigned recipe and estimated cost per serving. Enter all cost figures as literal numbers (for example, 8), not as spreadsheet formulas.

The fourth sheet should be named Program_Summary and contain columns for metric and value. Include rows for total_weekly_cost (sum of daily cost times 50 servings), avg_daily_cost_per_person, survey_question_count (5), recipes_evaluated (total recipes retrieved), and menu_days (5).

Set up a database in the team wiki system called "Recipe Knowledge Base" with properties for Recipe Name (title), Category (select with options for the main recipe categories), Difficulty (number), and Suitable For (multi-select with options Lunch, Dinner, Quick Meal). Add one entry for each recipe you included in the weekly menu.

Send an email to all_staff@company.com with the subject "New Employee Lunch Program - Take Our Survey" describing the new lunch program, mentioning that the weekly menu has been planned with a variety of dishes, and encouraging employees to fill out the dietary preference survey to help improve future menu selections.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, keep recipe search on explore, keep the form write on the workflow operator, keep `menu_planner.py` on one local writer, then parallelize the workbook, Notion, and email. A wave must finish and return all stated handoffs before the next wave begins.

Before Wave 1, the main agent reads `Cafeteria_Budget.pdf` and `dietary_requirements.json` in read-only mode and freezes the per-meal budget, headcount, and dietary restrictions.

1. Wave 1 — dispatch exactly 2 sub-agents in parallel:

   1. explore 0 (web-domain-researcher 0): Recipe owner. Retrieve at least 7 recipes from the recipe database — at least 2 Chinese Meat Dishes, 2 Chinese Vegetable Dishes, 1 Chinese Staple Foods, 1 Soups, and 1 Seafood — recording each recipe's name, category, difficulty, and ingredients exactly as returned. Return the compact recipe rows plus category/count controls. Do not write files, create the form, or run the planner.
   2. coder 0 (external-workflow-operator 0): Sole owner of the Google Form `Employee Lunch Program Preferences`. Search the exact title first, create it once only when absent, and block on duplicates. Add, in order, three multiple-choice questions — preferred cuisine type (Chinese Meat Dishes / Chinese Vegetable Dishes / Chinese Staple Foods / Soups / Seafood), spice tolerance (Mild / Medium / Spicy), and dietary restrictions (Vegetarian / No Pork / No Seafood / Gluten Free / No Restrictions) — and two short-text questions on the importance of variety (rate 1 to 5) and any other food preferences or allergies. Retrieve the form to verify the title, question wording, options, and question types. Do not query recipes or write the planner.

After Wave 1, the main agent freezes the retrieved recipe list and the form ID/title/URL. Missing recipes or an ambiguous form create is a blocker.

2. Wave 2 — dispatch exactly 1 coder sub-agent:

   1. coder 0 (office-report-builder 0): Sole owner of `menu_planner.py`. It receives the frozen recipes, budget, and dietary restrictions. Write and run the script embedding this data and selecting exactly 5 recipes for Monday through Friday, with difficulty <= 4, no category repeating on consecutive days, and dietary restrictions honored where possible (avoid pork if No Pork, avoid seafood if No Seafood); apply frozen per-serving costs of 8 USD for meat and seafood dishes, 5 USD for vegetable dishes, 6 USD for staple foods, and 4 USD for soups. Return the selected weekly menu, per-day costs, and total weekly cost (sum of the 5 per-serving costs times 50 servings per day). Do not create the workbook, Notion database, form, or email.

After Wave 2, the main agent verifies and freezes the weekly menu and cost totals as the sole downstream source.

3. Wave 3 — dispatch exactly 3 coder sub-agents in parallel:

   1. coder 0 (office-report-builder 1): Sole writer of `Meal_Program_Plan.xlsx`. Read only the frozen recipes, menu, and survey question list. Create exactly four worksheets: `Survey_Questions` holds `question_num/text/type` with exactly the 5 survey questions; `Recipe_Selection` holds `recipe_name/category/difficulty` with at least 7 rows (2 meat, 2 vegetable, 1 staple, 1 soup, 1 seafood, names and categories exactly as retrieved); `Weekly_Menu` holds `day/lunch_recipe/estimated_cost` with exactly 5 rows for Monday-Friday, costs entered as literal numbers per the pricing (meat/seafood 8, vegetable 5, staple 6, soup 4 USD); `Program_Summary` holds metric/value rows — `total_weekly_cost` (sum of daily estimated_cost x 50 servings), `avg_daily_cost_per_person` (total / (5 days x 50 servings)), `survey_question_count` = 5, `recipes_evaluated` (count of Recipe_Selection rows), and `menu_days` = 5 — all as literal numbers rather than formulas. Read every populated range back.
   2. coder 1 (external-workflow-operator 1): Sole Notion owner of the database `Recipe Knowledge Base`. Search the exact title first, create it once only when absent, and reuse without duplicating. Require properties Recipe Name (title), Category (select: Chinese Meat Dishes, Chinese Vegetable Dishes, Chinese Staple Foods, Soups, Seafood), Difficulty (number), and Suitable For (multi-select: Lunch, Dinner, Quick Meal). Add exactly 5 entries — one per recipe from the frozen Monday-Friday weekly menu — with recipe name, category, and difficulty (<= 4) copied exactly and Suitable For including at least `Lunch`. Read back and require exactly 5 pages.
   3. coder 2 (external-workflow-operator 2): Sole email owner. Search Sent mail for exact To `all_staff@company.com` / subject `New Employee Lunch Program - Take Our Survey`, send at most once, then read it back. The body introduces the lunch program, mentions the planned weekly menu with dishes across meat, vegetable, staple, soup, and seafood categories, and encourages employees to complete `Employee Lunch Program Preferences`, including the survey link if available, otherwise referencing the survey by its exact title.

After Wave 3, the main agent reconciles the workbook, Notion five-page set, form, and email against the same frozen menu. Do not dispatch more sub-agents.