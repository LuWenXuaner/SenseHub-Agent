"""LLM 多模型路由（OpenAI 兼容 API）."""

from __future__ import annotations

import json
from typing import Any

import httpx

from sensehub.settings import get_settings
from sensehub.config.user_settings import get_provider_credentials, get_role_model


class LLMRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.models_cfg = self.settings.models_config

    def _resolve_role(self, role: str) -> tuple[str, str, str]:
        roles = self.models_cfg.get("roles", {})
        role_cfg = roles.get(role, roles.get("planner", {}))
        provider = role_cfg.get("provider", "siliconflow")
        model = role_cfg.get("model", "Qwen/Qwen3-8B")
        base, key = get_provider_credentials(provider)

        override_model = get_role_model(role)
        if override_model:
            model = override_model

        return base.rstrip("/"), key, model

    async def chat(
        self,
        role: str,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 2048,
    ) -> str:
        base_url, api_key, model = self._resolve_role(role)
        if not api_key:
            raise RuntimeError(f"未配置 {role} 对应提供商的 API Key")

        roles_cfg = self.models_cfg.get("roles", {}).get(role, {})
        temp = temperature if temperature is not None else roles_cfg.get("temperature", 0.3)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
        }

        timeout = float(self.models_cfg.get("defaults", {}).get("timeout_seconds", 60))
        async with httpx.AsyncClient(timeout=timeout + 30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
            return "".join(parts).strip()
        return content.strip()

    async def chat_vision_json(
        self,
        role: str,
        system: str,
        user: str,
        image_b64: str,
        *,
        media_type: str = "image/png",
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": user},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
            },
        ]
        text = await self.chat(
            role,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
        return self._parse_json_text(text)

    @staticmethod
    def _parse_json_text(text: str) -> dict:
        import re

        text = text.strip()
        # Strip Qwen3 reasoning blocks if present
        text = re.sub(
            r"<\s*think\s*>.*?<\s*/\s*think\s*>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()
        if text.startswith("```"):
            lines = text.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[1:end])
        return json.loads(text)

    async def chat_json(self, role: str, system: str, user: str) -> dict[str, Any]:
        text = await self.chat(
            role,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return self._parse_json_text(text)

    async def chat_json_turn(self, role: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        text = await self.chat(role, messages)
        return self._parse_json_text(text)

    async def chat_with_tools_turn(
        self,
        role: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """原生 function calling；失败时 fallback 到 JSON 模式."""
        base_url, api_key, model = self._resolve_role(role)
        if not api_key:
            raise RuntimeError(f"未配置 {role} 对应提供商的 API Key")

        roles_cfg = self.models_cfg.get("roles", {}).get(role, {})
        temp = roles_cfg.get("temperature", 0.3)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": 2048,
            "tools": tools,
            "tool_choice": "auto",
        }
        timeout = float(self.models_cfg.get("defaults", {}).get("timeout_seconds", 60))
        try:
            async with httpx.AsyncClient(timeout=timeout + 30) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code >= 400:
                    text = await self.chat_json_turn(role, messages)
                    return {"mode": "json", "json": text}
                data = resp.json()
            choice = data["choices"][0]["message"]
            tool_calls = choice.get("tool_calls") or []
            if tool_calls:
                return {"mode": "fc", "message": choice}
            content = str(choice.get("content") or "").strip()
            if content:
                try:
                    return {"mode": "json", "json": self._parse_json_text(content)}
                except Exception:
                    from sensehub.cognition.tool_call_repair import extract_json_tool_call, promote_to_tool_calls

                    repaired = extract_json_tool_call(content)
                    if repaired:
                        finish, calls = promote_to_tool_calls(repaired)
                        if calls:
                            choice["tool_calls"] = calls
                            choice["content"] = ""
                            return {"mode": "fc", "message": choice}
                        if finish:
                            return {"mode": "json", "json": {"action": "finish", "answer": finish}}
            return {"mode": "json", "json": await self.chat_json_turn(role, messages)}
        except Exception:
            text = await self.chat_json_turn(role, messages)
            return {"mode": "json", "json": text}

