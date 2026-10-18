import asyncio
import os
import sys
import time
import requests
import hashlib
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.types as types
from duckduckgo_search import DDGS
from PIL import Image
import pyautogui


# Подключаем Windows API для нативной работы с буфером файлов
import win32clipboard
import win32con
import ctypes
from ctypes import wintypes


# Настройка структур Windows для копирования путей файлов (HDROP)
class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]


pyautogui.PAUSE = 0.05


LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_errors.log"))


def log_error(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINALS_DIR = os.path.join(BASE_DIR, "gallery", "originals")
THUMB_DIR = os.path.join(BASE_DIR, "gallery", "thumbs")


try:
    os.makedirs(ORIGINALS_DIR, exist_ok=True)
    os.makedirs(THUMB_DIR, exist_ok=True)
except Exception as e:
    log_error(f"Не удалось создать папки галереи: {e}")


def auto_paste_image(file_path):
    """
    Копирует файл изображения в буфер обмена как системный объект (HDROP)
    и эмулирует нажатие Ctrl+V для вставки в чат OpenCode.
    """
    try:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            log_error(f"Файл для авто-вставки не найден: {abs_path}")
            return False


        # Формируем структуру данных файла для буфера обмена Windows (широкие символы Unicode)
        path_bytes = (abs_path + "\0\0").encode("utf-16le")
        dropfiles = DROPFILES()
        dropfiles.pFiles = ctypes.sizeof(DROPFILES)
        dropfiles.fWide = True


        # Выделяем глобальную память в Windows под структуру
        # Важно: на x64 хэндлы 64-битные — без restype/argtypes хэндл усечается,
        # GlobalLock возвращает NULL и memmove падает с access violation
        k32 = ctypes.windll.kernel32
        k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        k32.GlobalAlloc.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        k32.GlobalUnlock.restype = ctypes.c_void_p

        data = bytes(dropfiles) + path_bytes
        hGlobal = k32.GlobalAlloc(win32con.GHND, len(data))
        pGlobal = k32.GlobalLock(hGlobal)
        if not pGlobal:
            k32.GlobalFree(hGlobal)
            log_error("GlobalLock вернул NULL при выделении памяти под HDROP")
            return False
        ctypes.memmove(pGlobal, data, len(data))
        k32.GlobalUnlock(hGlobal)


        # Записываем файл в системный буфер обмена Windows
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, hGlobal)
        win32clipboard.CloseClipboard()


        # Даем Electron-окружению OpenCode 300 мс на реакцию и прожимаем Ctrl+V
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        
        return True
    except Exception as e:
        log_error(f"Ошибка авто-вставки: {e}")
        return False


def process_and_inject_image(source_path_or_url, is_url=False):
    try:
        filename = ""
        if is_url:
            hashed = hashlib.md5(source_path_or_url.encode()).hexdigest()
            clean_url = source_path_or_url.split("?")[0]
            ext = clean_url.split(".")[-1].lower() if "." in clean_url else "jpg"
            if len(ext) > 4 or not ext.isalnum():
                ext = "jpg"
            filename = f"web_{hashed}.{ext}"
            full_path = os.path.join(ORIGINALS_DIR, filename)
            if not os.path.exists(full_path):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                res = requests.get(source_path_or_url, timeout=10, headers=headers)
                if res.status_code == 200:
                    with open(full_path, "wb") as f:
                        f.write(res.content)
                else:
                    log_error(f"Сайт вернул код {res.status_code} для {source_path_or_url}")
                    return False
        else:
            if not os.path.exists(source_path_or_url):
                log_error(f"Локальный файл не найден: {source_path_or_url}")
                return False
            filename = os.path.basename(source_path_or_url)
            full_path = os.path.join(ORIGINALS_DIR, filename)
            if os.path.abspath(source_path_or_url) != os.path.abspath(full_path):
                import shutil
                shutil.copy2(source_path_or_url, full_path)


        thumb_path = os.path.join(THUMB_DIR, filename)
        if not os.path.exists(thumb_path):
            with Image.open(full_path) as img:
                img.thumbnail((300, 300))
                if img.mode in ("RGBA", "P") and filename.lower().endswith(("jpg", "jpeg")):
                    img = img.convert("RGB")
                img.save(thumb_path)


        return auto_paste_image(thumb_path)
    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")
        return False


server = Server("opencode-autopaste-mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_web_ref",
            description="Ищет одну картинку в DuckDuckGo и автоматически вставляет её превью в чат через Ctrl+V.",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Поисковый запрос"}},
                "required": ["query"],
            },
        ),
        types.Tool(
            name="push_blender_render",
            description="Берет готовый рендер Blender по пути файла и автоматически вбрасывает его в чат OpenCode.",
            inputSchema={
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Абсолютный путь к файлу"}},
                "required": ["file_path"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}


    if name == "search_web_ref":
        query = arguments.get("query")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://qwant.com",
            }
            qwant_url = f"https://api.qwant.com/v3/search/images?q={requests.utils.quote(query)}&count=1&locale=ru&format=json"
            res = requests.get(qwant_url, headers=headers, timeout=5)
            img_url = None
            title = "Референс"
            if res.status_code == 200:
                data = res.json()
                items = data.get("data", {}).get("result", {}).get("items", [])
                if items:
                    img_url = items[0].get("media")
                    title = items[0].get("title", title)
            if not img_url:
                with DDGS() as ddgs:
                    ddgs.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
                    results = list(ddgs.images(query, max_results=1))
                    if results:
                        img_url = results[0]["image"]
                        title = results[0]["title"]
            if img_url:
                success = process_and_inject_image(img_url, is_url=True)
                if success:
                    return [types.TextContent(
                        type="text",
                        text=f"🔍 Референс «{title}» найден и подготовлен к отправке."
                    )]
            return [types.TextContent(type="text", text="Все поисковые каналы временно перегружены лимитами.")]
        except Exception as e:
            log_error(f"Ошибка в инструменте search_web_ref: {e}")
            return [types.TextContent(type="text", text=f"Ошибка поиска: {str(e)}")]


    elif name == "push_blender_render":
        file_path = arguments.get("file_path")
        success = process_and_inject_image(file_path, is_url=False)
        if success:
            return [types.TextContent(
                type="text", text="📸 Рендер успешно передан в окно чата OpenCode!"
            )]
        return [types.TextContent(type="text", text="Ошибка: файл рендера недоступен.")]


    raise ValueError("Unknown tool")


async def main():
    from mcp.server.stdio import stdio_server
    try:
        async with stdio_server() as (r, w):
            await server.run(
                r, w,
                InitializationOptions(
                    server_name="opencode-autopaste-mcp",
                    server_version="1.19.3",
                    capabilities=server.get_capabilities(NotificationOptions(), {}),
                ),
            )
    except Exception as e:
        log_error(f"Критическая ошибка запуска stdio сервера: {e}")


if __name__ == "__main__":
    asyncio.run(main())
