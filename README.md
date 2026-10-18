# Autopaste Gallery MCP (OpenCode)

MCP-сервер, который находит картинку в интернете (или берёт готовый рендер Blender с диска), делает превью и **автоматически вставляет его в чат OpenCode через системный буфер обмена и Ctrl+V**. Это «clipboard-подход»: в отличие от `photo-upload-mcp`/`web-photo-mcp` (HTTP API), здесь нужен фокус на окне чата.

---

## Русский

### Что делает
- Инструмент **`search_web_ref(query)`** — ищет одну картинку (Qwant API, фолбэк DuckDuckGo), скачивает её в `gallery/originals/`, создаёт превью 300px в `gallery/thumbs/` и вставляет его в чат.
- Инструмент **`push_blender_render(file_path)`** — берёт локальный файл (например, рендер Blender из Blender MCP), копирует в галерею, делает превью и вставляет в чат.
- Вставка: файл кладётся в буфер Windows как `CF_HDROP`, затем эмулируется `Ctrl+V` (`pyautogui`).

### Параметры инструментов
| Инструмент | Параметр | Тип | Обязательный | Описание |
|---|---|---|---|---|
| `search_web_ref` | `query` | string | да | Поисковый запрос |
| `push_blender_render` | `file_path` | string | да | Абсолютный путь к файлу изображения |

### Требования
- **Windows** (буфер `CF_HDROP`, `pyautogui`, `win32clipboard`).
- **Python 3.x** с пакетами: `mcp`, `requests`, `duckduckgo_search`, `Pillow`, `pyautogui`, `pywin32`.
- **Фокус на окне чата OpenCode** в момент вызова — `Ctrl+V` уходит в активное окно.

### Установка / регистрация
1. Положите `server.py` в любую папку, например `C:/tests_model/my-image-mcp/`.
2. В `opencode.json` добавьте запись под ключом `mcp`:
   ```json
   {
     "mcp": {
       "autopaste-gallery": {
         "type": "local",
         "command": ["C:\\Python314\\python.exe", "C:/tests_model/my-image-mcp/server.py"],
         "enabled": true
       }
     }
   }
   ```
   (замените путь к `python.exe` и к `server.py` на свои)
3. Перезапустите OpenCode — инструменты станут доступны агенту.

### Использование
- `search_web_ref(query="blender low poly island")` — референс появится в чате как превью.
- `push_blender_render(file_path="C:/renders/scene.png")` — рендер влетит в чат.

---

## English

### What it does
- Tool **`search_web_ref(query)`** — finds one image (Qwant API, DuckDuckGo fallback), downloads it to `gallery/originals/`, builds a 300px preview in `gallery/thumbs/` and pastes it into the chat.
- Tool **`push_blender_render(file_path)`** — takes a local file (e.g. a Blender render), copies it to the gallery, builds a preview and pastes it into the chat.
- Paste mechanism: the file is placed on the Windows clipboard as `CF_HDROP`, then `Ctrl+V` is emulated (`pyautogui`).

### Tool parameters
| Tool | Parameter | Type | Required | Description |
|---|---|---|---|---|
| `search_web_ref` | `query` | string | yes | Search query |
| `push_blender_render` | `file_path` | string | yes | Absolute path to an image file |

### Requirements
- **Windows** (`CF_HDROP` clipboard, `pyautogui`, `win32clipboard`).
- **Python 3.x** with packages: `mcp`, `requests`, `duckduckgo_search`, `Pillow`, `pyautogui`, `pywin32`.
- **Focus on the OpenCode chat window** at call time — `Ctrl+V` goes to the active window.

### Installation / registration
1. Place `server.py` in any folder, e.g. `C:/tests_model/my-image-mcp/`.
2. Add an entry under the `mcp` key in `opencode.json`:
   ```json
   {
     "mcp": {
       "autopaste-gallery": {
         "type": "local",
         "command": ["C:\\Python314\\python.exe", "C:/tests_model/my-image-mcp/server.py"],
         "enabled": true
       }
     }
   }
   ```
   (replace the `python.exe` and `server.py` paths with your own)
3. Restart OpenCode — the tools become available to the agent.

### Usage
- `search_web_ref(query="blender low poly island")` — a reference preview appears in the chat.
- `push_blender_render(file_path="C:/renders/scene.png")` — the render lands in the chat.

---

## Files
- `server.py` — the MCP server.
- `.gitignore`
