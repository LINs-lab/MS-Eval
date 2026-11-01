Hi there, I am an academic administrator and I need to put together an enrollment overview for all courses in our learning management system. This will be shared with the provost next week so it needs to be comprehensive.

Please pull data for every course available in the system. For each course, I need the course name, course code, total number of enrollments, and a breakdown of enrollments by type (how many are students, how many are teachers, how many are teaching assistants). Also break down by enrollment status showing how many are active and how many are completed.

Create an Excel file called Enrollment_Overview.xlsx in the workspace with two sheets.

The first sheet should be called "Enrollment Details" and have columns Course_Name, Course_Code, Total_Enrollments, Students, Teachers, TAs, Active, and Completed. Sort the rows alphabetically by Course_Name.

The second sheet should be called "Summary" and have a two-column layout with Metric in column A and Value in column B. Include the following rows: Total_Courses (the number of courses), Total_Enrollments (sum across all courses), Total_Students, Total_Teachers, Total_TAs, Avg_Enrollment_Per_Course (average total enrollments per course rounded to 2 decimal places), Largest_Course (name of the course with the most enrollments), Largest_Course_Enrollments (its enrollment count), Smallest_Course (name of the course with the fewest enrollments), and Smallest_Course_Enrollments (its enrollment count).

Also create a PowerPoint presentation called Enrollment_Overview.pptx in the workspace. The first slide should have the title "Course Enrollment Overview" and a subtitle "Academic Dashboard Report - <today's date in YYYY-MM-DD format>". The second slide should be titled "Enrollment Summary" and show the total courses, total enrollments, total students, average enrollment per course, and which course is largest and smallest. The third slide should be titled "Top 5 Courses by Enrollment" and list the five courses with the highest enrollment counts, showing course name, code, and enrollment number. The fourth slide should be titled "Enrollment Distribution" and show the breakdown by enrollment type (students, teachers, TAs) and by status (active, completed) with percentages rounded to 1 decimal place.

Additionally, create a shared spreadsheet titled "Enrollment Dashboard" with a sheet called "Course Data" containing the same columns as the "Enrollment Details" sheet described above.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, first isolate each course's six compact counts, then fan out one canonical table to three independent artifact writers. Canvas remains read-only.

The main agent calls canvas_list_courses(include_ended=true), validates unique IDs/codes/names, and freezes the exact returned course inventory. It then dispatches one explicitly instantiated Explore prompt per literal course; every prompt must contain that course's exact ID, code, and full name rather than an ordinal, range, or grouped label.

1. Wave 1 — dispatch exactly 22 explore sub-agents in parallel, one per literal course below:

   1. explore 0 (enterprise-data-analyst 0): Course Explore agent for course_id=1 (AAA-2013J): issue these six independent canvas_get_course_grades calls natively in parallel, all with page=1 and per_page=1: unfiltered; type=["StudentEnrollment"]; type=["TeacherEnrollment"]; type=["TaEnrollment"]; enrollment_state=["active"]; enrollment_state=["completed"]. Return only {course_id:1, course_code:"AAA-2013J", course_name, total_enrollments, students, teachers, tas, active, completed, pagination_controls}, taking every count from the matching response's pagination.total_count. Do not fetch later pages, return enrollment rows, or modify Canvas.
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

After Wave 1, the main agent validates exactly one result per course and freezes a canonical table sorted by course_name with the eight required Enrollment Details columns. Compute Summary values, type/status percentages, and deterministic top-five/largest/smallest selections once; use course_code ascending as the tie-break. Freeze the runtime current date required by the presentation. No writer may recompute these facts.

2. Wave 2 — dispatch exactly 3 coder sub-agents in parallel:

   1. coder 0 (office-report-builder 0): One Coder is the sole writer of Enrollment_Overview.xlsx in the dynamically resolved task workspace. Create exactly Enrollment Details and Summary with the required headers, rows, literal numeric values and rounding, then read both populated ranges back.
   2. coder 1 (office-report-builder 1): One Coder is the sole writer of Enrollment_Overview.pptx in that workspace. Create exactly the four requested slides from the canonical summary/top-five/distribution payload and runtime date, then read back slide titles and all displayed values.
   3. coder 2 (external-workflow-operator 0): One Coder is the sole owner of the shared spreadsheet titled Enrollment Dashboard. Create or reuse one exact-title spreadsheet and write the canonical table only to sheet Course Data in the exact bounded range A1:H<row count>; do not write diagnostic cells. Read that range back.

After Wave 2, the main agent verifies all three artifacts against the canonical table, including total-enrollment arithmetic, exact type/state counts, percentages, top-five order, extrema and current-date subtitle. Do not dispatch a verification wave.
