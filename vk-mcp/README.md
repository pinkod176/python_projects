# VK-Market MCP

Небольшой MCP-сервер: даёт Claude читать товары сообщества ВКонтакте. Магазину (`zeboogie-shop`) он **не нужен** — сайт сам ходит в VK API на сервере. MCP полезен для исследования каталога из чата.

```bash
pip install mcp
# демо-режим (по умолчанию, без сети):
python server.py
# Claude Code:
claude mcp add vk-market -- python /путь/к/vk-mcp/server.py
# реальный режим:
claude mcp add vk-market --env VK_API_DEMO=false --env VK_ACCESS_TOKEN=... --env VK_GROUP_ID=... -- python /путь/к/vk-mcp/server.py
```
Если в вашей сети нужен прокси, добавьте `--env HTTPS_PROXY=http://адрес:порт`. Токен хранится только в окружении процесса.
