You are an accreditation coordinator preparing a comprehensive curriculum review for an upcoming university accreditation visit. Your job is to audit the institution's courses against accreditation requirements, find supporting scholarly literature, and document everything in a structured compliance matrix and an accreditation report.

Start by fetching the accreditation requirements from the accreditation portal at http://localhost:30238/api/accreditation_requirements.json. This document specifies minimum thresholds for course counts, faculty ratios, assessment types, and scholarly integration that the institution must meet.

Next, connect to the learning management system and retrieve a list of all courses offered by the institution. For each course, gather the course name, the number of enrolled students, the number of assignments, the number of quizzes the course has (use 0 if it has none), and the number of discussion topics. Also determine how many faculty members (teachers and teaching assistants combined) are associated with each course. Use the course's enrollment count (total students) directly for the number of enrolled students, and derive the faculty count from each course's enrollment records, where faculty are enrollments of type TeacherEnrollment or TaEnrollment.

Using this data, evaluate each course against the accreditation requirements. A course is considered compliant if the student to faculty ratio does not exceed the maximum specified in the requirements and the course has at least one form of assessment (quiz or assignment). Note which courses are compliant and which are not.

Then search the scholarly literature for research supporting the pedagogical approaches used in the curriculum. Search for papers on the following topics: active learning in higher education, assessment best practices in education, online learning effectiveness, curriculum design frameworks, and student engagement strategies. For each topic, find at least one relevant paper and note its title, authors, and relevance to the curriculum.

Create an Excel file called Curriculum_Review.xlsx in your workspace with three sheets. The first sheet should be called "Course Compliance" with columns for Course_Name, Assignment_Count, Quiz_Count, Discussion_Count, Student_Count, Faculty_Count, Student_Faculty_Ratio, and Compliant (Yes or No based on whether the course meets the accreditation criteria). Include all courses.

The second sheet should be called "Literature Support" with columns for Search_Topic, Paper_Title, Authors, and Relevance_Note. Include at least five rows covering the five pedagogical topics listed above.

The third sheet should be called "Summary" with columns for Metric and Value. Include rows for total courses, compliant courses, non-compliant courses, compliance rate (as a percentage), total faculty across all courses, average student to faculty ratio, and the number of supporting papers found.

Finally, create a page in the team's knowledge base (Notion) titled "Accreditation Review Report" (the page title must contain this exact phrase) that summarizes the curriculum audit findings. The page should mention the overall compliance rate, highlight any courses that fail to meet requirements, reference the scholarly literature that supports the institution's pedagogical approach, and note any recommendations for improvement before the accreditation visit.

When you have completed all tasks, call claim_done.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, use one parallel source wave and one parallel writer wave. Canvas and scholarly search are read-only. The main agent fetches the accreditation JSON and freezes the course manifest; writers consume only the merged canonical packet.

Before Wave 1, the main agent fetches http://localhost:30238/api/accreditation_requirements.json once and freezes the literal student-faculty-ratio maximum and assessment-presence rule. It then calls canvas_list_courses(include_ended=true) once, validates unique IDs/codes/full names, and freezes the complete 22-course manifest. Partition that manifest into two disjoint shards covering every course_id exactly once: shard A = course_id 1-11 (AAA-2013J through DDD-2013B) and shard B = course_id 12-22 (DDD-2014B through GGG-2014B). Pass each owner its literal ID list, codes, and full names.

1. Wave 1 — dispatch exactly 3 explore sub-agents in parallel:

   1. explore 0 (enterprise-data-analyst 0): Course-metrics owner for shard A (course_id 1-11). For each assigned course, collect the exact full name, enrolled-student count from the course enrollment total, assignment count, quiz count (0 if none), discussion-topic count, and faculty count (TeacherEnrollment plus TaEnrollment only), then mark it compliant when the student-faculty ratio stays within the frozen accreditation maximum and the course has at least one quiz or assignment. Faculty counts must come from actual enrollment records, never inferred from grade rows or current-user metadata; a course lacking source-visible student plus TeacherEnrollment/TaEnrollment coverage gets CONTRACT_BLOCKER_MISSING_ROLE_COMPLETE_ENROLLMENTS and no Faculty_Count, Student_Faculty_Ratio, or Compliant value. Return assigned versus observed course IDs plus the compact per-course rows. Make no writes.
   2. explore 1 (enterprise-data-analyst 1): Course-metrics owner for shard B (course_id 12-22) — same literal recipe, only that shard's course identities substituted.
   3. explore 2 (academic-literature-researcher 0): Literature owner for the five fixed pedagogy topics: active learning in higher education; assessment best practices in education; online learning effectiveness; curriculum design frameworks; and student engagement strategies. Find one genuinely relevant paper per topic and return title, authors, and a curriculum-relevance note for each. Read-only; do not write the workbook or Notion page.

After Wave 1, the main agent requires both shards together to cover every frozen course_id exactly once, rejects duplicate/missing IDs, and freezes one canonical packet: all 22 Course Compliance rows, at least five Literature Support rows, and the Summary metrics (total courses, compliant courses, non-compliant courses, compliance rate as a percentage, total faculty across all courses, average student-faculty ratio, supporting-paper count).

2. Wave 2 — dispatch exactly 2 coder sub-agents in parallel, both consuming the canonical packet with no recomputation from Canvas or scholarly search:

   1. coder 0 (office-report-builder 0): Sole writer of Curriculum_Review.xlsx. Create exactly Course Compliance, Literature Support, and Summary with the task's exact headers, all 22 course rows, at least five literature rows, and the frozen summary metrics as literal values. Read every populated range back.
   2. coder 1 (external-workflow-operator 0): Sole Notion owner of a page whose title contains the exact phrase Accreditation Review Report. Search exact title first, create at most once on zero matches, block on duplicates, and write a summary of the overall compliance rate, non-compliant courses, scholarly literature supporting the pedagogical approach, and recommendations before the visit. Read the retained page and its child-block text back.

After Wave 2, the main agent reconciles workbook ranges and the Notion read-back against the same packet, then calls claim_done. Do not dispatch an aggregation or verification agent.