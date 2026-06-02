# Hướng dẫn sử dụng — Daily Video Reporter

Tài liệu này giải thích **dữ liệu báo cáo đến từ đâu**, **vì sao mỗi ngày giọng đọc
lại khác nhau**, và **cách chạy / cấu hình / lên lịch** hệ thống.

---

## 1. Task & nội dung được lấy từ đâu? (Câu hỏi quan trọng nhất)

> **Nguồn dữ liệu duy nhất hiện tại: Git commit của ngày hôm đó.**

Mỗi ngày, hệ thống chạy lệnh sau trên repo mục tiêu:

```bash
git log --since="today" --author="Thienpham" --no-merges -i --pretty=format:%s
```

- Mỗi dòng commit message (phần `%s` = subject) → **một task**.
- Commit được **phân loại tự động** theo tiền tố (conventional commits):

| Tiền tố commit | Nhóm | Ví dụ |
|---|---|---|
| `feat:` / `feature:` | 🚀 Tính năng (features) | `feat: Add login validation` → "Add login validation" |
| `fix:` / `bug:` | 🐛 Sửa lỗi (fixes) | `fix: Fix button alignment` → "Fix button alignment" |
| `docs:` `refactor:` `test:` `chore:` `style:` `perf:` | 🧹 Chất lượng (quality) | `refactor: extract helper` → "Extract helper" |

- Commit `Merge branch...` bị **lọc bỏ** (không tính là task).
- Nếu **không có commit nào** hôm đó → báo "No commits recorded today".

👉 **Không có "description" riêng** — vì git commit chỉ có 1 dòng tiêu đề (subject).
Tiêu đề commit *chính là* nội dung task. (Xem mục 5 nếu bạn muốn nội dung phong phú hơn.)

---

## 2. Vì sao mỗi ngày TTS (giọng đọc) lại khác nhau?

Vì toàn bộ luồng dữ liệu là **động theo commit trong ngày**:

```
Commit hôm nay  →  payload.json  →  kịch bản tiếng Việt  →  report.wav (giọng nhân bản)
   (khác mỗi ngày)     (khác)            (khác)                  (khác)
```

### Ví dụ minh hoạ

**Ngày A** — bạn commit:
```
feat: Thêm đăng nhập Google
fix: Sửa lỗi tràn bộ nhớ
```
→ Kịch bản sinh ra:
> *"Chào mọi người, đây là báo cáo công việc ngày 2026-06-01 của Thienpham. Hôm nay tôi đã hoàn thành **1 tính năng**, sửa **1 lỗi** và cập nhật 0 tác vụ nâng cao chất lượng code. Các tính năng đã hoàn thành: 1. Thêm đăng nhập Google. Các lỗi đã được sửa: 1. Sửa lỗi tràn bộ nhớ. ..."*

**Ngày B** — bạn commit:
```
feat: Trang thống kê doanh thu
feat: Xuất báo cáo PDF
refactor: Tách module thanh toán
```
→ Kịch bản **hoàn toàn khác**:
> *"...Hôm nay tôi đã hoàn thành **2 tính năng**, sửa **0 lỗi** và cập nhật **1 tác vụ** nâng cao chất lượng code. Các tính năng đã hoàn thành: 1. Trang thống kê doanh thu. 2. Xuất báo cáo PDF. ..."*

→ Vì kịch bản khác → OmniVoice tạo ra **file `report.wav` khác** → **video khác** mỗi ngày.
Hệ thống hoàn toàn tự động, bạn **không cần sửa gì** — chỉ cần commit như bình thường.

---

## 3. Cấu hình nguồn dữ liệu

Tất cả qua biến môi trường (file `.env`, copy từ `.env.example`):

```bash
# Repo nào sẽ được quét commit?
REPORTER_TARGET_REPO=/Users/thienuser/Documents/report-daily

# Lọc commit theo tác giả (không phân biệt hoa thường)
REPORTER_GIT_AUTHOR=Thienpham

# Khoảng thời gian lấy commit. Sản xuất: "today". Test: "6 months ago"
REPORTER_SINCE=today

# Tên người báo cáo (đọc trong kịch bản)
REPORTER_NAME=Thienpham
```

> 💡 Muốn báo cáo cho **repo khác** (vd dự án chính), đổi `REPORTER_TARGET_REPO`
> hoặc chạy `--repo /đường/dẫn/repo`.

---

## 4. Cách chạy

```bash
cd /Users/thienuser/Documents/report-daily

# Chạy đầy đủ: lấy commit → kịch bản → giọng đọc → video → đăng DevZone
.venv/bin/python daily_reporter.py

# Chạy thử, KHÔNG đăng lên DevZone
.venv/bin/python daily_reporter.py --dry-run

# Chỉ lấy task + tạo kịch bản (bỏ qua TTS & video) để xem nhanh
.venv/bin/python daily_reporter.py --skip-tts --skip-video --skip-upload

# Báo cáo cho ngày / repo cụ thể
.venv/bin/python daily_reporter.py --date 2026-06-01 --repo /path/to/project
```

### Kết quả tạo ra ở đâu

| File | Nội dung |
|---|---|
| `_bmad-output/temp/payload.json` | Danh sách task đã phân loại (JSON) |
| `_bmad-output/temp/script.txt` | Kịch bản tiếng Việt sẽ được đọc |
| `_bmad-output/temp/report.wav` | Giọng đọc (OmniVoice voice cloning) |
| `_bmad-output/temp/report.md` | Nội dung Markdown đăng lên DevZone |
| `_bmad-output/videos/report-YYYY-MM-DD.mp4` | **Video báo cáo 1080p** |
| `_bmad-output/logs/scheduler.log` | Nhật ký chạy (thành công/lỗi, thời gian, document ID) |

---

## 5. (Tùy chọn) Muốn nội dung phong phú hơn commit message?

Git commit chỉ cho 1 dòng tiêu đề. Nếu muốn task có **mô tả chi tiết (description)**,
có 2 hướng:

**a) Dùng cả phần thân commit (commit body):** viết commit nhiều dòng, dòng đầu là
tiêu đề, các dòng sau là mô tả. (Cần mở rộng `git_extractor.py` để lấy `%b`.)

**b) Lấy task từ DevZone Tasks API** thay cho git: theo `project-context.md`, DevZone
có sẵn endpoint task với cả `title`, `description`, `status`:
```
GET /workspace/projects/wozONU8U79scVlep/tasks?status=done
```
→ Có thể lấy các task **trạng thái `done`** trong ngày, mỗi task có mô tả đầy đủ để đọc.

> Hiện tại Epic 1 chỉ định **nguồn = git commit**. Nếu bạn muốn chuyển/bổ sung nguồn
> DevZone Tasks, báo mình — đây là một thay đổi nhỏ ở tầng trích xuất dữ liệu.

---

## 6. Lên lịch tự động 17:00 hằng ngày

```bash
./scripts/install_scheduler.sh        # cài đặt launchd agent
launchctl start com.vietnix.dailyreporter   # chạy thử ngay
```

> ⏰ launchd chạy theo **giờ máy**. Để đúng 17:00 giờ Việt Nam (ICT, UTC+7),
> máy phải đặt múi giờ `Asia/Ho_Chi_Minh`. Có cả phương án cron (script in ra sẵn).

Mỗi ngày đến 17:00, hệ thống tự động: lấy commit → đọc → render video → đăng DevZone,
và ghi log. Nếu lỗi → hiện thông báo trên macOS.

---

## 7. Giọng đọc tham chiếu (voice cloning)

OmniVoice **nhân bản giọng** từ 1 clip mẫu ngắn:

- Đặt file giọng thật của bạn tại `ref/reference.wav` + lời thoại tại `ref/reference.txt`.
- Hoặc tạo clip mẫu thử nghiệm: `./scripts/make_reference.sh` (dùng giọng tiếng Việt
  "Linh" của macOS — **nên thay bằng giọng thật của bạn** để clone đúng giọng).

> Giọng trong video = giọng trong `ref/reference.wav`. Đổi file này = đổi giọng đọc.
```
