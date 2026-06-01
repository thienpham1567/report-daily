# Epic 1: Daily Video Report Automation

This epic covers the automation of a daily video report that extracts completed tasks, generates a TTS voiceover using OmniVoice, renders a slide-based video using HeyGen Hyperframes, and uploads it to Devzone.

## Epic Description
To improve visibility and tracking, the system will automatically compile daily completed tasks at 17:00, convert them into a spoken Vietnamese voiceover using OmniVoice (cloned voice), design visual slides, render a report video using HeyGen Hyperframes, and post the report to the DevZone knowledge base (`https://devzone.vietnix.dev`).

---

## Story 1.1: Environment Setup and Tooling Investigation

### Description
Investigate and set up the local development environments (Python 3.10+ and Node.js 18+) on Mac. Install PyTorch, OmniVoice, Hyperframes, and FFmpeg.

### Acceptance Criteria
- **AC 1.1.1**: Local Node.js and Python 3 environments are verified.
- **AC 1.1.2**: PyTorch is installed and optimized for Apple Silicon (MPS) or CPU.
- **AC 1.1.3**: OmniVoice repository is cloned and set up with initial pre-trained model weights.
- **AC 1.1.4**: HeyGen Hyperframes package is installed and verified via CLI check.
- **AC 1.1.5**: FFmpeg is installed and accessible via shell command line (`ffmpeg -version`).

---

## Story 1.2: Task Extraction and Parsing Logic

### Description
Create a Python parser module inside `daily_reporter.py` that extracts today's Git commits, filters out merge commits, and groups them into structured categories.

### Acceptance Criteria
- **AC 1.2.1**: Runs `git log --since="today" --author="Thienpham" --oneline` inside the target workspace.
- **AC 1.2.2**: Filters out standard merge commits (e.g., starting with `Merge branch...`).
- **AC 1.2.3**: Parses commit messages and groups them into:
  - **Features**: Commits starting with `feat:` or `feature:`
  - **Fixes**: Commits starting with `fix:` or `bug:`
  - **Chore/Quality**: Commits starting with `docs:`, `refactor:`, `test:`, or `chore:`
- **AC 1.2.4**: Generates a JSON payload containing the grouped tasks:
  ```json
  {
    "date": "YYYY-MM-DD",
    "categories": {
      "features": ["Add login validation"],
      "fixes": ["Fix button alignment"],
      "quality": ["Update README.md"]
    }
  }
  ```
- **AC 1.2.5**: If no commits are found, fallback to a mock task checklist or report "No commits recorded today".

---

## Story 1.3: Text-to-Speech Synthesis Module via OmniVoice

### Description
Implement a Python TTS module that takes the parsed task payload, synthesizes a natural Vietnamese report script, and calls OmniVoice to generate a WAV audio file.

### Acceptance Criteria
- **AC 1.3.1**: Generates a Vietnamese report script following this layout:
  - "Chào mọi người, đây là báo cáo công việc ngày YYYY-MM-DD của Thienpham. Hôm nay tôi đã hoàn thành [X] tính năng, sửa [Y] lỗi và cập nhật [Z] tác vụ nâng cao chất lượng code."
  - Followed by reading out each task title.
- **AC 1.3.2**: Invokes the `OmniVoice` CLI/API with the generated script and a target reference voice file to perform voice cloning.
- **AC 1.3.3**: Outputs a clear, high-quality audio file named `report.wav` inside `_bmad-output/temp/`.

---

## Story 1.4: HeyGen Hyperframes Video Generation

### Description
Design the layout structure and configure HeyGen Hyperframes to compile visual slides representing the task categories, overlaying the generated WAV audio track.

### Acceptance Criteria
- **AC 1.4.1**: Create a Hyperframes configuration file defining the slide design system:
  - Dark mode aesthetic with Vietnix green/blue accents.
  - Large, readable typography (e.g. Inter or Roboto).
- **AC 1.4.2**: Render slides representing:
  - Slide 1: Daily Progress Report Title + Date
  - Slide 2: Completed Features
  - Slide 3: Bug Fixes & Refactoring
- **AC 1.4.3**: Integrate the `report.wav` audio track so that the slide changes are timed with the voice narration.
- **AC 1.4.4**: Compile the final output video as `_bmad-output/videos/report-YYYY-MM-DD.mp4` with a minimum resolution of 1080p.

---

## Story 1.5: DevZone Knowledge Upload Integration

### Description
Implement the REST client inside `daily_reporter.py` to post the report log as a Document to DevZone ERP and save the video file locally.

### Acceptance Criteria
- **AC 1.5.1**: Reads API Key (`dc9343c5cea6f6bbd0957d17bd49022d`) and Project ID (`wozONU8U79scVlep`) from `project-context.md` or env variables.
- **AC 1.5.2**: Sends a HTTP POST request to `https://api.devzone.vietnix.dev/workspace/projects/wozONU8U79scVlep/documents`.
- **AC 1.5.3**: Uses header `X-API-Key` for authentication.
- **AC 1.5.4**: Submits a JSON body containing:
  - `title`: "Báo cáo ngày YYYY-MM-DD"
  - `type`: "doc"
  - `content`: Markdown formatted string containing the structured tasks, git commit list, and a link to the generated local video file: `_bmad-output/videos/report-YYYY-MM-DD.mp4`.
- **AC 1.5.5**: Logs the response document ID upon a successful `201 Created` status.

---

## Story 1.6: Scheduling Automation

### Description
Configure a local scheduler using Antigravity's `schedule` tool or a local system cron daemon to trigger the entire pipeline every day at 17:00.

### Acceptance Criteria
- **AC 1.6.1**: The scheduler triggers daily at 17:00 (5:00 PM) Vietnam time.
- **AC 1.6.2**: The scheduler executes `python3 daily_reporter.py`.
- **AC 1.6.3**: Writes execution logs (success/failure, execution time, document ID) to `_bmad-output/logs/scheduler.log`.
- **AC 1.6.4**: In case of failures, sends a notification prompt to Antigravity.
