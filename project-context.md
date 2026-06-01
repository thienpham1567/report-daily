# DevZone Project Context

**Project**: ERP
**Project ID**: wozONU8U79scVlep
**API Key**: dc9343c5cea6f6bbd0957d17bd49022d
**Base URL**: https://api.devzone.vietnix.dev

### Authentication
All API requests require header:
```
X-API-Key: dc9343c5cea6f6bbd0957d17bd49022d
```

### Available Endpoints

---

#### Documents

**`GET /workspace/projects/wozONU8U79scVlep/documents`** — List documents
Query params:
- `page` (number, default: 1)
- `limit` (number, default: 25)
- `search` (string, optional) — search by title/content
- `sorts` (string, optional) — e.g. `-createdAt`, `name`
- `type` (string, optional) — filter by type: `epic`, `user-story`, `doc`, `mindmap`
- `parentId` (string, optional) — filter by parent document

**`GET /workspace/projects/wozONU8U79scVlep/documents/:id`** — Get document detail

**`POST /workspace/projects/wozONU8U79scVlep/documents`** — Create document
Body (JSON):
```json
{
  "title": "string (required)",
  "type": "epic | user-story | doc | mindmap (required)",
  "content": "string (optional)",
  "parentId": "string (optional)",
  "position": "number (optional)"
}
```

**`PUT /workspace/projects/wozONU8U79scVlep/documents/:id`** — Update document
Body (JSON): same as create, all fields optional

**`DELETE /workspace/projects/wozONU8U79scVlep/documents/:id`** — Delete document

---

#### Tasks

**`GET /workspace/projects/wozONU8U79scVlep/tasks`** — List tasks
Query params:
- `page` (number, default: 1)
- `limit` (number, default: 25)
- `search` (string, optional)
- `sorts` (string, optional) — e.g. `-createdAt`, `position`
- `status` (string, optional) — `draft`, `todo`, `doing`, `pending`, `done`, `archived`
- `assigneeId` (string, optional)
- `documentId` (string, optional) — filter tasks by document

**`GET /workspace/projects/wozONU8U79scVlep/tasks/:id`** — Get task detail

**`POST /workspace/projects/wozONU8U79scVlep/tasks`** — Create task
Body (JSON):
```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "status": "draft | todo | doing | pending | done (optional, default: draft)",
  "documentId": "string (optional) — link to a document",
  "position": "number (optional)"
}
```

**`PUT /workspace/projects/wozONU8U79scVlep/tasks/:id`** — Update task
Body (JSON):
```json
{
  "title": "string (optional)",
  "description": "string (optional)",
  "status": "draft | todo | doing | pending | done | archived (optional)",
  "assigneeId": "string (optional)",
  "documentId": "string (optional)",
  "checklist": [{ "id": "string", "title": "string", "done": false }]
}
```

**`DELETE /workspace/projects/wozONU8U79scVlep/tasks/:id`** — Delete task

---

#### Messages (on tasks)

**`GET /workspace/projects/wozONU8U79scVlep/tasks/:taskId/messages`** — List messages
Query params:
- `page` (number, default: 1)
- `limit` (number, default: 25)
- `sorts` (string, optional)

**`POST /workspace/projects/wozONU8U79scVlep/tasks/:taskId/messages`** — Send message
Body (JSON):
```json
{
  "content": "string (required)",
  "type": "number (optional, default: 0) — 0=default, 1=reply",
  "referenceId": "string (optional) — reply to message id"
}
```
