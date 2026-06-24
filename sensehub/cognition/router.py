"""LLM 多模型路由（OpenAI 兼容 API）."""

from __future__ import annotations

import json
from typing import Any

import httpx

from sensehub.settings import get_settings
from sensehub.config.user_settings import get_provider_credentials, resolve_role_binding
from sensehub.cognition.studio_models import provider_key_hint
from sensehub.cognition.chat_errors import ChatModelUnavailableError


class LLMRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.models_cfg = self.settings.models_config

    def _resolve_role(self, role: str) -> tuple[str, str, str, str]:
        provider, model = resolve_role_binding(role)
        base, key = get_provider_credentials(provider)
        return base.rstrip("/"), key, model, provider

    def _record_llm_usage(
        self,
        role: str,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        completion: str,
        api_usage: dict[str, Any] | None = None,
    ) -> None:
        try:
            from sensehub.cognition.token_meter import estimate_chat_tokens
            from sensehub.db.token_usage import record_llm_usage
            from sensehub.runtime.request_context import get_llm_usage_user

            user_id = get_llm_usage_user()
            if not user_id:
                return
            prompt_t, comp_t = estimate_chat_tokens(messages, completion, api_usage=api_usage)
            record_llm_usage(
                user_id=user_id,
                role=role,
                provider=provider or "unknown",
                model=model or "unknown",
                prompt_tokens=prompt_t,
                completion_tokens=comp_t,
            )
        except Exception:
            return

    def _provider_api_style(self, provider: str) -> str:
        catalog = self.models_cfg.get("providers") or {}
        meta = catalog.get(provider)
        if isinstance(meta, dict):
            return str(meta.get("api_style") or "openai")
        return "openai"

    def _openai_chat_url(self, base_url: str) -> str:
        """拼接 OpenAI 兼容 chat/completions URL（兼容 /v1 与火山 /api/v3）."""
        base = (base_url or "").rstrip("/")
        if not base:
            raise RuntimeError("未配置 API Base URL")
        if base.endswith("/v1") or base.endswith("/api/v3"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    async def _post_chat_completions(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        *,
        temperature: float,
        max_tokens: int,
        role: str = "",
        provider: str = "",
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        timeout = float(self.models_cfg.get("defaults", {}).get("timeout_seconds", 60))
        url = self._openai_chat_url(base_url)
        try:
            async with httpx.AsyncClient(timeout=timeout + 30) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise ChatModelUnavailableError() from exc
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ChatModelUnavailableError() from exc

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
            text_out = "".join(parts).strip()
        else:
            text_out = content.strip()
        if not text_out:
            raise ChatModelUnavailableError()
        if role:
            self._record_llm_usage(role, provider, model, messages, text_out, data.get("usage"))
        return text_out

    async def chat_provider(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ) -> str:
        """按指定提供商与模型名调用 Chat（使用用户/环境配置的 API Key）."""
        pid = (provider or "siliconflow").strip()
        api_style = self._provider_api_style(pid)
        if api_style != "openai":
            raise ChatModelUnavailableError()

        base_url, api_key = get_provider_credentials(pid)
        if not api_key:
            raise ChatModelUnavailableError()

        return await self._post_chat_completions(
            base_url,
            api_key,
            model,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            role="custom",
            provider=pid,
        )

    async def chat(
        self,
        role: str,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 2048,
    ) -> str:
        base_url, api_key, model, provider = self._resolve_role(role)
        if not api_key:
            raise RuntimeError(f"未配置 {role} 对应提供商的 API Key")

        roles_cfg = self.models_cfg.get("roles", {}).get(role, {})
        temp = temperature if temperature is not None else roles_cfg.get("temperature", 0.3)

        return await self._post_chat_completions(
            base_url,
            api_key,
            model,
            messages,
            temperature=temp,
            max_tokens=max_tokens,
            role=role,
            provider=provider,
        )

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
        base_url, api_key, model, provider = self._resolve_role(role)
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
                    self._openai_chat_url(base_url),
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
            completion_text = str(choice.get("content") or "")
            if tool_calls:
                completion_text = json.dumps(tool_calls, ensure_ascii=False)
            self._record_llm_usage(role, provider, model, messages, completion_text, data.get("usage"))
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

