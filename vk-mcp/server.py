"""MCP-сервер для работы с товарами сообщества ВКонтакте (дополнение к магазину).

Позволяет Claude читать каталог сообщества: список товаров и один товар.
Режимы:
  VK_API_DEMO=true  (по умолчанию) — тестовые данные из zeboogie-shop/src/lib/vk/demo/market.json
                    в формате ответов VK API; сеть не используется.
  VK_API_DEMO=false — реальные запросы к VK API (нужны VK_ACCESS_TOKEN и VK_GROUP_ID).

Токен читается из переменной окружения и никогда не возвращается в ответах инструментов.
Прокси (если нужен в вашей сети) задаётся стандартной переменной HTTPS_PROXY.
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

mcp = _Server("VK-Market")

IS_DEMO = os.getenv("VK_API_DEMO", "true").lower() == "true"
API = os.getenv("VK_API_BASE", "https://api.vk.com/method")
VERSION = os.getenv("VK_API_VERSION", "5.199")
DEMO_FILE = Path(
    os.getenv("VK_DEMO_FILE", Path(__file__).resolve().parent.parent / "zeboogie-shop/src/lib/vk/demo/market.json")
)


def _demo() -> dict:
    return json.loads(DEMO_FILE.read_text(encoding="utf-8"))


def _call(method: str, **params) -> dict:
    token = os.getenv("VK_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("VK_ACCESS_TOKEN не задан (или включите VK_API_DEMO=true)")
    params["v"] = VERSION
    req = urllib.request.Request(
        f"{API}/{method}",
        data=urllib.parse.urlencode(params).encode(),
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:  # HTTPS_PROXY учитывается автоматически
        data = json.load(resp)
    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"VK API {method}: [{err.get('error_code')}] {err.get('error_msg')}")
    return data["response"]


@mcp.tool()
def vk_list_market_items(offset: int = 0, count: int = 20) -> dict:
    """Список товаров сообщества. Возвращает {count, items} как market.get (цены — в копейках)."""
    count = max(1, min(count, 200))
    if IS_DEMO:
        items = _demo()["items"]
        return {"count": len(items), "items": items[offset : offset + count], "demo": True}
    owner = -int(os.environ["VK_GROUP_ID"])
    return _call("market.get", owner_id=owner, offset=offset, count=count, extended=1)


@mcp.tool()
def vk_get_market_item(item_id: int) -> dict:
    """Один товар по числовому id (как в поле id товара VK)."""
    if IS_DEMO:
        for item in _demo()["items"]:
            if item["id"] == item_id:
                return {**item, "demo": True}
        raise ValueError(f"Товар {item_id} не найден в демо-данных")
    owner = -int(os.environ["VK_GROUP_ID"])
    res = _call("market.getById", item_ids=f"{owner}_{item_id}", extended=1)
    return res["items"][0]


if __name__ == "__main__":
    mcp.run()
