I need to create a comprehensive grade report for our department heads.

Data source: pull course, enrollment, and grade data from the learning management system (Canvas LMS) for all courses. For each course, use the enrollment records and each student's overall final score — the `final_score` value inside the enrollment's `grades` data. Include every student who has a recorded final score; students without a recorded final score are excluded from that course's totals.

In the workspace, use the terminal to create a Python script called grade_reporter.py that reads grade_data.json (create it first — it should hold the course name and the list of final scores for every student in every course), calculates the grade distributions, pass rates, and course averages, and writes grade_report.json. Use the standard grade scale: A: 90+, B: 80-89, C: 70-79, D: 60-69, F: below 60. Pass means grade C or above. Round Pass_Rate_Pct and Course_Avg to 1 decimal place. The datasets are large (thousands of enrollments per course); it is fine to build grade_data.json incrementally, one course at a time, as you pull each course's enrollment data from the LMS rather than relying on a single large dump.

Create a Google Sheet titled "Department Grade Dashboard" with two sheets. The first sheet Grade_Distribution should have columns Course_Name, A_Count, B_Count, C_Count, D_Count, F_Count, Total_Students, Pass_Rate_Pct (round to 1 decimal, pass means C or above), and Course_Avg (round to 1 decimal), sorted by Course_Name. Use the full course name as shown in the LMS for the Course_Name column. The second sheet Department_Summary should have Metric and Value columns with Total_Courses, Total_Students, Overall_Pass_Rate (round to 1 decimal), Overall_Avg_Grade (round to 1 decimal), Highest_Avg_Course, and Lowest_Avg_Course.

Also read the Course_Policies.pdf in the workspace which has the grade scale and academic policies, and make sure the grade thresholds you use match those defined in the policy document.

Send an email to dept-heads@university.edu with subject "Q1 2026 Grade Distribution Report" including a summary of the overall pass rate, the highest and lowest performing courses, and a note that courses with pass rates below 70% require review.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, use one course-owner source wave; the main agent owns the canonical script, then dispatches the Google Sheet and email writers. Canvas is read-only. Resolve the runtime workspace dynamically and read Course_Policies.pdf and reporting_guide.md completely, freezing grade bands, C-or-above passing threshold, below-70 review rule and report requirements.

Call canvas_list_courses(include_ended=true) once and freeze all 22 exact course IDs/codes/full names.

Wave 1 — dispatch exactly 22 explore sub-agents in parallel, one per literal course below:

   1. explore 0 (enterprise-data-analyst 0): Course owner for course_id=1 (AAA-2013J). Call canvas_get_course_grades(course_id=1,page=1,per_page=100,type=["StudentEnrollment"]), then issue all remaining literal pages from total_pages in native-parallel batches and verify every page identity. Retain only numeric non-null grades.final_score with literal enrollment row.id, reject duplicates, write one compact JSON with exact full course name, all final scores and page/count controls, read it back, and return only path/hash and controls. Do not use current_score or a reconstructed course label.
   2. explore 1 (enterprise-data-analyst 1): Course owner for course_id=2 (AAA-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   3. explore 2 (enterprise-data-analyst 2): Course owner for course_id=3 (BBB-2013J) — same literal recipe, only the course identity and unique JSON path substituted.
   4. explore 3 (enterprise-data-analyst 3): Course owner for course_id=4 (BBB-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   5. explore 4 (enterprise-data-analyst 4): Course owner for course_id=5 (BBB-2013B) — same literal recipe, only the course identity and unique JSON path substituted.
   6. explore 5 (enterprise-data-analyst 5): Course owner for course_id=6 (BBB-2014B) — same literal recipe, only the course identity and unique JSON path substituted.
   7. explore 6 (enterprise-data-analyst 6): Course owner for course_id=7 (CCC-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   8. explore 7 (enterprise-data-analyst 7): Course owner for course_id=8 (CCC-2014B) — same literal recipe, only the course identity and unique JSON path substituted.
   9. explore 8 (enterprise-data-analyst 8): Course owner for course_id=9 (DDD-2013J) — same literal recipe, only the course identity and unique JSON path substituted.
   10. explore 9 (enterprise-data-analyst 9): Course owner for course_id=10 (DDD-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   11. explore 10 (enterprise-data-analyst 10): Course owner for course_id=11 (DDD-2013B) — same literal recipe, only the course identity and unique JSON path substituted.
   12. explore 11 (enterprise-data-analyst 11): Course owner for course_id=12 (DDD-2014B) — same literal recipe, only the course identity and unique JSON path substituted.
   13. explore 12 (enterprise-data-analyst 12): Course owner for course_id=13 (EEE-2013J) — same literal recipe, only the course identity and unique JSON path substituted.
   14. explore 13 (enterprise-data-analyst 13): Course owner for course_id=14 (EEE-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   15. explore 14 (enterprise-data-analyst 14): Course owner for course_id=15 (EEE-2014B) — same literal recipe, only the course identity and unique JSON path substituted.
   16. explore 15 (enterprise-data-analyst 15): Course owner for course_id=16 (FFF-2013J) — same literal recipe, only the course identity and unique JSON path substituted.
   17. explore 16 (enterprise-data-analyst 16): Course owner for course_id=17 (FFF-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   18. explore 17 (enterprise-data-analyst 17): Course owner for course_id=18 (FFF-2013B) — same literal recipe, only the course identity and unique JSON path substituted.
   19. explore 18 (enterprise-data-analyst 18): Course owner for course_id=19 (FFF-2014B) — same literal recipe, only the course identity and unique JSON path substituted.
   20. explore 19 (enterprise-data-analyst 19): Course owner for course_id=20 (GGG-2013J) — same literal recipe, only the course identity and unique JSON path substituted.
   21. explore 20 (enterprise-data-analyst 20): Course owner for course_id=21 (GGG-2014J) — same literal recipe, only the course identity and unique JSON path substituted.
   22. explore 21 (enterprise-data-analyst 21): Course owner for course_id=22 (GGG-2014B) — same literal recipe, only the course identity and unique JSON path substituted.

After the wave, require all 22 receipts, every advertised page and disjoint enrollment IDs. The main agent is sole owner of exact files grade_data.json, grade_reporter.py and grade_report.json. Write all exact full course names/final scores to grade_data.json; write and run the script once to compute A/B/C/D/F, Total_Students, C-or-above pass rate, one-decimal course averages, weighted overall pass rate and overall average; then read all three files back and reconcile 22 courses, totals, buckets, extrema and rounding.

Then dispatch the two independent external branches in one native-parallel response:

- coder 0 (external-workflow-operator 0): Search/reuse-or-create the exact Google spreadsheet Department Grade Dashboard at most once, block duplicate exact titles/tabs, own exactly Grade_Distribution and Department_Summary, write 22 alphabetical rows and six exact summary metrics, then read both ranges back.
- coder 1 (external-workflow-operator 1): Paginate Sent mail and read candidates for exact recipient dept-heads@university.edu and subject Q1 2026 Grade Distribution Report. Send at most once with canonical overall pass rate, full highest/lowest course names and below-70 review statement, then read the retained message back.

Do not dispatch page, aggregation or audit agents. Final acceptance compares the exact three files, external sheet ranges and retained email to the course receipts.
