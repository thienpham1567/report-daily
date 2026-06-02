# Architecture & Workflow — Daily Video Reporter

> High-level technical overview for AI / Software Engineers.
> Tất cả sơ đồ là Mermaid — mở trên GitHub hoặc VS Code (Markdown Preview) để xem hình.

---

## 1. Tổng quan hệ thống (System Overview)

Một pipeline tự động: **đọc git commit trong ngày → kể lại bằng giọng nói tiếng Việt
(cloned voice) → render thành video slide → đăng lên DevZone**, chạy tự động lúc 17:00.

```mermaid
flowchart LR
    subgraph TRIGGER["⏰ Scheduler (Story 1.6)"]
        CRON["launchd / cron<br/>17:00 hằng ngày"]
    end

    subgraph PIPELINE["🐍 daily_reporter.py (Orchestrator)"]
        direction TB
        S2["1.2 Git Extractor<br/>git log → JSON"]
        S3A["1.3 Script Builder<br/>JSON → kịch bản VN"]
        S3B["1.3 TTS / OmniVoice<br/>kịch bản → report.wav"]
        S4["1.4 Video / HyperFrames<br/>HTML → report.mp4 (1080p)"]
        S5["1.5 DevZone Client<br/>Markdown → POST document"]
        S2 --> S3A --> S3B --> S4 --> S5
    end

    subgraph EXT["🌐 External"]
        GIT[("Git repo<br/>commit history")]
        OV["OmniVoice model<br/>(k2-fsa, HuggingFace)"]
        HF["HyperFrames CLI<br/>(Node + Chrome + FFmpeg)"]
        DZ[("DevZone ERP<br/>REST API")]
    end

    CRON --> PIPELINE
    GIT -.input.-> S2
    OV -.voice clone.-> S3B
    HF -.render.-> S4
    S5 -.HTTP POST.-> DZ
```

---

## 2. Luồng dữ liệu & hình dạng dữ liệu (Data Flow)

Mấu chốt: **đầu ra của bước này là đầu vào của bước sau**. Mọi bước đều ghi artifact
ra đĩa (`_bmad-output/temp/`) nên dễ debug từng khâu.

```mermaid
flowchart TD
    A["git commits<br/>(raw subject lines)"] -->|classify by prefix| B["payload.json"]
    B -->|template VN| C["script.txt"]
    C -->|OmniVoice voice clone| D["report.wav<br/>(24kHz mono)"]
    B -->|build slides| E["index.html<br/>(HyperFrames composition)"]
    D -->|audio track| E
    E -->|hyperframes render| F["report-YYYY-MM-DD.mp4<br/>(1920x1080 H.264)"]
    B -->|markdown body + video link| G["report.md"]
    G -->|HTTP POST + X-API-Key| H["DevZone document<br/>(returns id)"]
```

**`payload.json`** — "nguồn sự thật" trung tâm, mọi bước sau đều đọc từ đây:

```json
{
  "date": "2026-06-01",
  "author": "Thienpham",
  "categories": {
    "features": ["Add login validation"],
    "fixes": ["Fix button alignment"],
    "quality": ["Update README"]
  },
  "commits": ["feat: Add login validation", "fix: Fix button alignment", "..."],
  "total": 3
}
```

---

## 3. Bản đồ codebase (Codebase Map)

```
report-daily/
├── daily_reporter.py          # 🎯 ORCHESTRATOR — CLI entrypoint, nối 5 bước, log, xử lý lỗi
├── reporter/                  # 📦 Package logic nghiệp vụ (mỗi file = 1 story)
│   ├── config.py              #    Config: đọc .env + project-context.md → dataclass Config
│   ├── git_extractor.py       #    [1.2] git log → phân loại → payload.json
│   ├── script_builder.py      #    [1.3] payload → kịch bản tiếng Việt (thuần text, dễ test)
│   ├── tts.py                 #    [1.3] OmniVoice wrapper → report.wav (import nặng = lazy)
│   ├── video.py               #    [1.4] sinh HTML composition + gọi HyperFrames CLI
│   └── devzone.py             #    [1.5] build Markdown + REST client (X-API-Key)
├── video/                     # 🎬 HyperFrames project (npx hyperframes init)
│   ├── index.html             #    Composition được GHI LẠI mỗi lần render (do video.py sinh)
│   └── assets/report.wav      #    Audio được copy vào đây để render
├── ref/                       # 🎤 Giọng tham chiếu cho voice cloning
│   ├── reference.wav          #    (đổi file này = đổi giọng đọc)
│   └── reference.txt          #    transcript của clip trên
├── scripts/                   # 🔧 Setup & scheduling (Story 1.1 + 1.6)
│   ├── setup.sh               #    Cài ffmpeg, venv, torch+omnivoice, hyperframes
│   ├── make_reference.sh      #    Tạo clip giọng mẫu (placeholder)
│   ├── run_daily.sh           #    Wrapper scheduler gọi (load .env, kích hoạt venv)
│   ├── install_scheduler.sh   #    Cài launchd agent
│   └── com.vietnix.dailyreporter.plist   # launchd config (17:00)
├── tests/test_pipeline.py     # ✅ Unit test logic thuần (extract, script, markdown)
├── _bmad-output/              # 📂 Artifact đầu ra (gitignored)
│   ├── temp/                  #    payload.json, script.txt, report.wav, report.md
│   ├── videos/                #    report-YYYY-MM-DD.mp4
│   └── logs/scheduler.log     #    nhật ký chạy
├── project-context.md         # 📄 DevZone API spec + credentials (nguồn fallback)
├── requirements.txt / .env.example
├── README.md / HUONG-DAN-SU-DUNG.md / ARCHITECTURE.md (file này)
```

### Nguyên tắc thiết kế (Design principles)

| Nguyên tắc | Lý do |
|---|---|
| **Pure logic tách khỏi I/O** | `git_extractor`, `script_builder`, `devzone.build_markdown` là hàm thuần → unit test không cần network/ML |
| **Lazy import cho dependency nặng** | `torch`/`omnivoice` chỉ import bên trong `tts.py` khi gọi → test & các bước khác chạy không cần GPU/model |
| **Artifact ra đĩa từng bước** | Debug được từng khâu; có thể chạy lại 1 bước mà không chạy lại cả pipeline |
| **Cờ `--skip-*` / `--dry-run`** | Cô lập từng story khi phát triển/kiểm thử |
| **Config qua env, fallback project-context.md** | Không hardcode secret; dễ trỏ sang repo/giọng/credentials khác |

---

## 4. Sequence diagram — một lần chạy (one run)

```mermaid
sequenceDiagram
    participant Sched as launchd (17:00)
    participant Orch as daily_reporter.py
    participant Git as git_extractor
    participant TTS as tts (OmniVoice)
    participant Vid as video (HyperFrames)
    participant DZ as devzone

    Sched->>Orch: run_daily.sh
    Orch->>Git: extract_tasks(repo, author, "today")
    Git-->>Orch: payload.json
    Orch->>Orch: build_script(payload) → script.txt
    Orch->>TTS: synthesize_report(script, ref_audio, ref_text)
    Note over TTS: load model (mps) → clone voice
    TTS-->>Orch: report.wav (24kHz)
    Orch->>Vid: render_video(payload, report.wav)
    Note over Vid: sinh index.html → npx hyperframes render
    Vid-->>Orch: report-DATE.mp4 (1080p)
    Orch->>DZ: upload_document(title, markdown)
    DZ-->>Orch: 201 Created + document id
    Orch->>Orch: log success → scheduler.log
```

---

## 5. Tech stack & ranh giới (boundaries)

```mermaid
flowchart TB
    subgraph PY["Python 3.12 venv"]
        ORCH[daily_reporter.py]
        REP[reporter/*]
        TORCH["torch 2.8 + omnivoice 0.1.5<br/>(MPS trên Apple Silicon)"]
        REQ[requests]
    end
    subgraph NODE["Node 22+ (npx)"]
        HFCLI["hyperframes CLI<br/>Chrome headless + FFmpeg"]
    end
    ORCH --> REP
    REP --> TORCH
    REP --> REQ
    REP -->|subprocess| HFCLI
```

- **Ranh giới ngôn ngữ:** Python orchestrate, gọi sang Node CLI qua `subprocess`
  (`reporter/video.py`). Hai bên giao tiếp qua **file** (`index.html`, `report.wav`, `.mp4`).
- **Điểm chạy chậm/nặng:** (1) tải & load model OmniVoice, (2) HyperFrames render (Chrome).
  Cả hai đều idempotent và cache lại (model ở `~/.cache/huggingface`, Chrome ở `~/.cache/hyperframes`).

---

## 6. Điểm mở rộng cho AI Engineer (Extension points)

| Muốn làm gì | Sửa ở đâu |
|---|---|
| Đổi nguồn task (vd DevZone Tasks API thay git) | `reporter/git_extractor.py` — giữ nguyên schema `payload` là các bước sau không đổi |
| Thêm/đổi cách phân loại commit | `_PREFIX_MAP` trong `git_extractor.py` |
| Đổi văn phong/ngôn ngữ kịch bản | `reporter/script_builder.py` (`build_script`) |
| Đổi model TTS / tham số giọng | `reporter/tts.py` (`OmniVoiceTTS`) |
| Đổi thiết kế slide / thêm slide | `reporter/video.py` (`build_composition_html`) |
| Đổi định dạng tài liệu DevZone | `reporter/devzone.py` (`build_markdown`) |
| Thêm bước mới vào pipeline | `daily_reporter.py` (`run()`) |

**Hợp đồng dữ liệu cần giữ (data contract):** miễn là một bước vẫn nhận/đẻ ra đúng
`payload` (mục 2) hoặc đúng đường file (`config.audio_path`, `config.video_path`),
bạn có thể thay thế hoàn toàn phần triển khai bên trong mà không ảnh hưởng bước khác.
```
