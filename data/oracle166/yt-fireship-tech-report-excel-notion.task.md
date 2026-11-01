You are a tech lead at a software company. Your manager has asked you to compile a technology trend report based on the most popular recent videos from a well-known programming education channel called Fireship on the video platform. You need to analyze the top 10 most-viewed videos from 2024 to 2025, summarize technology trends, publish findings to the team knowledge base, schedule a recurring review meeting, and notify the team by email.

Your workflow should proceed as follows.

First, search the video platform for the Fireship channel and retrieve its videos. Sort the videos by popularity and select the top 10 by view count. For each of those videos, collect the following details: the video identifier, the title, the publication date, the duration in seconds, the view count, the like count, and the primary technology topic derived from the video tags or title keywords.

Second, create a spreadsheet file named Tech_Trend_Report.xlsx. Inside this file, create a sheet named Videos containing one row per video with the following columns in order: Video_ID, Title, Published_Date, Duration_Seconds, View_Count, Like_Count, Primary_Topic. Then create a second sheet named Topic_Summary. In Topic_Summary, aggregate the data by topic and include these columns: Topic, Video_Count, Total_Views, Avg_Duration. Each row should represent one distinct technology topic found across the top 10 videos. Ensure the averages and totals are correctly computed.

Third, create a new page in the team knowledge base titled "Fireship Tech Trends Q1 2026". Add a brief introductory heading and a paragraph summarizing the overall findings. Then add a table or structured block listing the top 5 technology topics by total view count, with their video counts and total views.

Fourth, check the shared calendar for any existing Tech Review events in March 2026. Then create a new weekly recurring meeting event titled "Tech Review Meeting" scheduled for Monday March 9 2026 from 14:00 to 15:00. Use the UTC timezone.

Fifth, send an email to techteam@company.com. The subject should reference the tech trend report. The body should summarize which technology topics appeared most in the top videos, mention the new meeting scheduled, and inform the team that the full report is available in Tech_Trend_Report.xlsx.

The channel configuration file in your workspace is named channel_config.json and contains guidance on which channel to use, the date range of interest, how many videos to include, and the report title. An email template is also provided in email_template.txt to help you format the outgoing message.

When all outputs are complete, claim the task as done.

Task-Solving Rationable with Sub-task Decomposition:
To solve this task efficiently, keep the Fireship catalog on explore, then parallelize the independent workbook, Notion, and calendar artifacts. The email stays with the main agent. A wave must finish and return all stated handoffs before the next wave begins.

Before Wave 1, the main agent reads `channel_config.json` and `email_template.txt` in read-only mode and freezes the channel, 2024-2025 date range, top-10 count, and report title.

1. Wave 1 — dispatch exactly 1 explore sub-agent:

   1. explore 0 (web-domain-researcher 0): Locate the Fireship channel and retrieve its full video list; filter to videos published between 2024-01-01 and 2025-12-31 inclusive, sort by view count descending, and select the top 10 (or all available if fewer than 10). For each selected video collect `video_id`, `title`, `published_date` (YYYY-MM-DD), `duration_seconds`, `view_count`, `like_count`, and a concise `primary_topic` technology label derived from the video tags or, if tags are unavailable, the title keywords. Return the compact ten-row table plus channel/page/date/count controls. Do not write files or create deliverables.

After Wave 1, the main agent verifies the date window and ranking, aggregates Topic_Summary (`Topic, Video_Count, Total_Views, Avg_Duration`), and freezes one canonical packet of the top-10 video rows and topic totals. Missing catalog coverage is a blocker.

2. Wave 2 — dispatch exactly 3 coder sub-agents in parallel:

   1. coder 0 (office-report-builder 0): Sole writer of `Tech_Trend_Report.xlsx`. Read only the frozen packet. Create a `Videos` sheet holding exactly 10 data rows (one per video, in the given order) with columns `Video_ID, Title, Published_Date, Duration_Seconds, View_Count, Like_Count, Primary_Topic` in that order, and a `Topic_Summary` sheet with one row per distinct `Primary_Topic` giving `Video_Count`, `Total_Views`, and `Avg_Duration` (rounded to at most 2 decimals) computed from the frozen Videos data. If the video data is incomplete, build the workbook with the valid rows. Write literal values and read every populated range back.
   2. coder 1 (external-workflow-operator 0): Sole Notion owner of a page titled exactly `Fireship Tech Trends Q1 2026`. Search the exact title first, create at most once on zero matches, and block on duplicates. Include an `Overview` heading with a summary paragraph covering the 10 videos analyzed in 2024-2025, the most frequent topic(s) by video count, and the top topic by total views. Add a `Top 5 Technology Topics by Total Views` section with a table of Topic, Video_Count, and Total_Views for the top 5 topics sorted by Total_Views descending. Read the page back.
   3. coder 2 (external-workflow-operator 1): Sole calendar owner. Search existing `Tech Review` events in March 2026, then create a weekly recurring event titled `Tech Review Meeting` starting Monday 2026-03-09 from 14:00 to 15:00 UTC, repeating every Monday at that time. If an identical event (same title, start time, and weekly recurrence) already exists, treat it as the deliverable instead of creating a duplicate. Read the retained event back.

After Wave 2, the main agent reconciles the workbook, Notion page, and calendar event against the same packet. In that same response, search Sent mail for exact To `techteam@company.com` with a subject that references the tech trend report, send at most once using `email_template.txt` and the frozen findings (most frequent topics, the new meeting, and that the full report is in `Tech_Trend_Report.xlsx`), then read it back. Do not dispatch more sub-agents.