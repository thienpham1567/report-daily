# Hướng dẫn sử dụng — Daily Video Reporter

Tài liệu này giải thích **dữ liệu báo cáo đến từ đâu**, **giọng đọc hoạt động
ra sao**, và **cách chạy / cấu hình / lên lịch** hệ thống.

> ℹ️ Hệ thống có **2 nguồn dữ liệu**: Git commit (tự động phân loại) và
> DevZone Tasks (theo dõi tiến độ task hàng ngày).

---

## 1. Task & nội dung được lấy từ đâu?

### 1A. Nguồn 1: Git commit (video báo cáo)

> **Git commit là nguồn chính cho kịch bản đọc và video.**

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
Tiêu đề commit *chính là* nội dung task.

### 1B. Nguồn 2: DevZone Tasks (theo dõi tiến độ)

Module `reporter/devzone_tasks.py` kết nối **DevZone ERP API** để lấy danh sách tasks
được gán cho bạn, lọc theo ngày và phân nhóm theo trạng thái:

| Trạng thái | Ý nghĩa |
|---|---|
| ✅ `done` | Đã hoàn thành trong ngày |
| 🔄 `doing` | Đang thực hiện |
| 📋 `todo` | Chưa bắt đầu |
| ⏳ `pending` | Chờ xử lý / blocked |
| 👀 `review` | Đang review |

**Cách chạy nhanh:**

```bash
# Xem tasks hôm nay
.venv/bin/python -m reporter.devzone_tasks

# Xuất JSON (tích hợp vào pipeline khác)
.venv/bin/python -m reporter.devzone_tasks --json

# Xem tasks ngày cụ thể
.venv/bin/python -m reporter.devzone_tasks --date 2026-06-01

# Xem tất cả tasks (không lọc ngày)
.venv/bin/python -m reporter.devzone_tasks --all-statuses
```

**Kết quả mẫu:**
```
============================================================
📋 BÁO CÁO TASKS NGÀY 2026-06-02 — Ngọc Thiên
============================================================

✅ Đã hoàn thành: 2 | 🔄 Đang thực hiện: 1 | 📋 Chưa bắt đầu: 1
📊 Tổng cộng: 4 tasks

--- ✅ ĐÃ HOÀN THÀNH (2) ---
  1. Test-prod v1.0
     └─ Story: 🔷 Phản hồi yêu cầu hỗ trợ
     └─ Hoàn thành lúc: 10:27 02/06
  2. Xử lý UI v1.0
     └─ Story: 🔷 Thiết lập bảo mật
     └─ Hoàn thành lúc: 10:56 02/06
```

> ⚠️ **Lưu ý về Bearer token:** Token JWT có thời hạn. Khi hết hạn, hệ thống
> tự fallback sang `X-API-Key`. Để cập nhật token mới: mở DevZone web →
> Inspect → Network tab → copy giá trị `authorization: Bearer …` → dán vào
> `DEVZONE_BEARER_TOKEN` trong `.env`.

---

## 2. Giọng đọc (TTS) hoạt động thế nào?

Hệ thống hỗ trợ **4 engine** chuyển đổi văn bản thành giọng nói:

| Engine | Cài đặt `.env` | Đặc điểm | Chi phí |
|---|---|---|---|
| **FPT.AI** ⭐ | `REPORTER_TTS_ENGINE=fpt` | Giọng Việt cực tự nhiên, nhiều giọng vùng miền | Miễn phí 100K ký tự/tháng |
| **edge-tts** | `REPORTER_TTS_ENGINE=edge` | Giọng neural Microsoft, ổn định | Hoàn toàn miễn phí |
| **Fish Audio** | `REPORTER_TTS_ENGINE=fish` | Chất lượng cao, giọng tự nhiên | Cần nạp tiền (API credits) |
| **OmniVoice** | `REPORTER_TTS_ENGINE=omnivoice` | Clone giọng nói thật của bạn | Miễn phí, cần GPU ≥ 18 GB |

### Đang sử dụng: FPT.AI (giọng `banmai` — nữ Bắc)

Các giọng FPT.AI có sẵn:
- `banmai` — nữ, miền Bắc ⭐
- `leminh` — nam, miền Bắc
- `lannhi` — nữ, miền Nam
- `myan` — nữ, miền Trung

### Cơ chế tự động dự phòng (Fallback)

Nếu engine chính (FPT.AI hoặc Fish Audio) bị lỗi (hết hạn API, mất mạng, hết
lượt miễn phí...), hệ thống **tự động chuyển sang edge-tts** để đảm bảo
luôn tạo được file âm thanh — không bao giờ dừng pipeline giữa chừng.

### Vì sao mỗi ngày giọng đọc lại khác nhau?

Vì toàn bộ luồng dữ liệu là **động theo commit trong ngày**:

```
Commit hôm nay  →  payload.json  →  kịch bản tiếng Việt  →  report.wav
   (khác mỗi ngày)     (khác)            (khác)                  (khác)
```

### Ví dụ minh hoạ

**Ngày A** — bạn commit:
```
feat: Thêm đăng nhập Google
fix: Sửa lỗi tràn bộ nhớ
```
→ Kịch bản sinh ra:
> *"Chào mọi người, đây là báo cáo công việc ngày 2026-06-01 của Ngọc Thiên. Hôm nay tôi đã hoàn thành **1 tính năng**, sửa **1 lỗi** và cập nhật 0 tác vụ nâng cao chất lượng code. Các tính năng đã hoàn thành: 1. Thêm đăng nhập Google. Các lỗi đã được sửa: 1. Sửa lỗi tràn bộ nhớ. ..."*

**Ngày B** — bạn commit:
```
feat: Trang thống kê doanh thu
feat: Xuất báo cáo PDF
refactor: Tách module thanh toán
```
→ Kịch bản **hoàn toàn khác**:
> *"...Hôm nay tôi đã hoàn thành **2 tính năng**, sửa **0 lỗi** và cập nhật **1 tác vụ** nâng cao chất lượng code. Các tính năng đã hoàn thành: 1. Trang thống kê doanh thu. 2. Xuất báo cáo PDF. ..."*

→ Vì kịch bản khác → TTS tạo ra **file `report.wav` khác** → **video khác** mỗi ngày.
Hệ thống hoàn toàn tự động, bạn **không cần sửa gì** — chỉ cần commit như bình thường.

---

## 3. Cấu hình

Tất cả qua biến môi trường (file `.env`, copy từ `.env.example`):

```bash
# ===== Git extraction =====
# Repo nào sẽ được quét commit?
REPORTER_TARGET_REPO=/Users/thienpham/Documents/vietnix-erp-frontend

# Lọc commit theo tác giả (không phân biệt hoa thường)
REPORTER_GIT_AUTHOR=Thienpham

# Khoảng thời gian lấy commit. Sản xuất: "today". Test: "6 months ago"
REPORTER_SINCE=today

# Tên người báo cáo (đọc trong kịch bản)
REPORTER_NAME=Ngọc Thiên

# ===== DevZone =====
DEVZONE_BASE_URL=https://api.devzone.vietnix.dev
DEVZONE_PROJECT_ID=wozONU8U79scVlep
DEVZONE_API_KEY=xxxxxxxxxxxxxxxx

# User ID của bạn trên DevZone (dùng để lọc tasks)
DEVZONE_USER_ID=P9YwjgnOD5ral1J

# Bearer token từ DevZone web app (có thời hạn, cần cập nhật khi hết hạn)
DEVZONE_BEARER_TOKEN=eyJhbGci...

# ===== TTS =====
# Engine: "fpt" (khuyến nghị), "edge" (miễn phí), "fish", "omnivoice"
REPORTER_TTS_ENGINE=fpt

# Giọng: "banmai" (nữ Bắc), "leminh" (nam Bắc), "lannhi" (nữ Nam), "myan" (nữ Trung)
REPORTER_TTS_VOICE=banmai

# API key FPT.AI (lấy tại https://console.fpt.ai)
FPT_API_KEY=xxxxxxxxxxxxxxxx
```

> 💡 Muốn báo cáo cho **repo khác** (vd dự án chính), đổi `REPORTER_TARGET_REPO`
> hoặc chạy `--repo /đường/dẫn/repo`.
>
> 💡 **Cách tìm `DEVZONE_USER_ID`:** Mở DevZone web → Inspect → Network tab →
> bấm vào bất kỳ request nào có `/tasks` → xem response JSON → tìm task của bạn
> → lấy giá trị `assigneeId`.

---

## 4. Cách chạy

```bash
cd /Users/thienpham/Documents/report-daily

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
| `_bmad-output/temp/report.wav` | Giọng đọc (FPT.AI / edge-tts) |
| `_bmad-output/temp/report.md` | Nội dung Markdown đăng lên DevZone |
| `_bmad-output/videos/report-YYYY-MM-DD.mp4` | **Video báo cáo 1080p** |
| `_bmad-output/logs/scheduler.log` | Nhật ký chạy (thành công/lỗi, thời gian, document ID) |

---

## 5. DevZone Tasks — Theo dõi tiến độ task hàng ngày

Ngoài Git commit, hệ thống còn kết nối **DevZone ERP API** để theo dõi trạng
thái các task được gán cho bạn.

### Module: `reporter/devzone_tasks.py`

**Chức năng:**
1. Gọi API `GET /workspace/projects/{id}/tasks?limit=9999` để lấy toàn bộ tasks
2. Lọc theo `assigneeId` hoặc `userId` = `DEVZONE_USER_ID` trong `.env`
3. Lọc theo ngày (dựa trên `updatedAt`, `completedAt`, `createdAt`)
4. Phân nhóm theo trạng thái: done / doing / todo / pending / review
5. Xuất báo cáo dạng text hoặc JSON

**Các lệnh CLI:**

```bash
# Báo cáo tasks hôm nay (dạng bảng đẹp)
.venv/bin/python -m reporter.devzone_tasks

# Xuất JSON payload (để tích hợp pipeline hoặc xử lý tiếp)
.venv/bin/python -m reporter.devzone_tasks --json

# Xem tasks ngày cụ thể
.venv/bin/python -m reporter.devzone_tasks --date 2026-06-01

# Xem TẤT CẢ tasks (không lọc ngày — hữu ích để kiểm tra tổng quan)
.venv/bin/python -m reporter.devzone_tasks --all-statuses
```

**Sử dụng trong code Python:**

```python
from reporter.devzone_tasks import get_daily_tasks, format_report

# Lấy payload tasks hôm nay
payload = get_daily_tasks()
print(format_report(payload))

# Hoặc truy cập dữ liệu trực tiếp
for task in payload["tasks_by_status"].get("done", []):
    print(f"✅ {task['title']} — Story: {task['story']}")
```

### Xác thực API

Module hỗ trợ 2 cách xác thực (ưu tiên Bearer token):

| Phương thức | Biến `.env` | Ghi chú |
|---|---|---|
| **Bearer token** ⭐ | `DEVZONE_BEARER_TOKEN` | JWT từ DevZone web, có thời hạn |
| **X-API-Key** | `DEVZONE_API_KEY` | Project API key, không hết hạn |

> ⚠️ Khi Bearer token hết hạn, cập nhật bằng cách: DevZone web → F12 →
> Network → copy `authorization: Bearer eyJ…` → dán vào `.env`.

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

## 7. Giọng đọc tham chiếu (cho OmniVoice — không cần nếu dùng FPT.AI / edge-tts)

OmniVoice **nhân bản giọng** từ 1 clip mẫu ngắn:

- Đặt file giọng thật của bạn tại `ref/reference.wav` + lời thoại tại `ref/reference.txt`.
- Hoặc tạo clip mẫu thử nghiệm: `./scripts/make_reference.sh` (dùng giọng tiếng Việt
  "Linh" của macOS — **nên thay bằng giọng thật của bạn** để clone đúng giọng).

> Giọng trong video = giọng trong `ref/reference.wav`. Đổi file này = đổi giọng đọc.
> **Nếu dùng FPT.AI hoặc edge-tts, bạn không cần file reference.**

---

## 8. Cấu trúc các module chính

```
report-daily/
├── daily_reporter.py          # Orchestrator — điều phối toàn bộ pipeline
├── reporter/
│   ├── config.py              # Đọc .env, thiết lập đường dẫn
│   ├── git_extractor.py       # Quét Git commit → phân loại → JSON payload
│   ├── script_builder.py      # Lắp ghép kịch bản đọc tiếng Việt
│   ├── tts.py                 # 4 engine TTS + cơ chế fallback tự động
│   ├── video.py               # Render HTML → MP4 1080p qua HyperFrames
│   ├── devzone.py             # Upload báo cáo Markdown lên DevZone
│   └── devzone_tasks.py       # ⭐ Lấy & lọc tasks từ DevZone API
├── .env                       # Cấu hình (không commit lên git)
├── .env.example               # Mẫu cấu hình
└── video/                     # Thư mục HyperFrames (index.html + assets)
```
