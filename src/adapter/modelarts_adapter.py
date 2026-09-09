# Copyright (C) 2026 华为云
# SPDX-License-Identifier: MIT-0
"""
ModelArts 适配层
将文档重写 LLM API 调用适配为华为云 ModelArts Studio MaaS 的 OpenAI 兼容接口

MaaS OpenAI 兼容接口（中国大陆站当前部署于西南-贵阳一区域）:
- 文档: https://support.huaweicloud.com/model-call-maas/model-call-021.html
- 调用地址: https://api.modelarts-maas.com/openai/v1/chat/completions
- 认证: Authorization: Bearer <MaaS_API_Key>（在 MaaS 控制台"模型推理 > API Key"页面创建）
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

from pocsynth.errors import AuthError, AuthExpiredError, UpstreamError

# MaaS OpenAI 兼容接口基础地址（可按区域覆盖，见 HUAWEI_MAAS_BASE_URL）
MAAS_BASE_URL = "https://api.modelarts-maas.com/openai/v1"
MAAS_CHAT_COMPLETIONS_URL = f"{MAAS_BASE_URL}/chat/completions"

# 华为云 MaaS 可用模型（model 参数值以 MaaS 控制台"预置服务"为准）
MODELS: dict[str, dict[str, Any]] = {
    "deepseek_v4_flash": {
        "id": "deepseek-v4-flash",
        "context_window": 128_000,
        "endpoint": MAAS_CHAT_COMPLETIONS_URL,
        "description": "DeepSeek V4 Flash（高性价比，适合批量文档重写）",
    },
    "deepseek_v4_pro": {
        "id": "deepseek-v4-pro",
        "context_window": 128_000,
        "endpoint": MAAS_CHAT_COMPLETIONS_URL,
        "description": "DeepSeek V4 Pro（推理能力强）",
    },
    "glm_5_2": {
        "id": "glm-5.2",
        "context_window": 128_000,
        "endpoint": MAAS_CHAT_COMPLETIONS_URL,
        "description": "GLM-5.2",
    },
}

DEFAULT_MODEL = "deepseek_v4_flash"
DEFAULT_MAX_TOKENS = 8000


class HuaweiModelArtsClient:
    """
    华为云 ModelArts Studio MaaS 客户端

    使用 MaaS API Key（Bearer Token）调用 OpenAI 兼容接口。
    API Key 来源:
      1. 环境变量 HUAWEI_MAAS_API_KEY（或 MAAS_API_KEY）
      2. MaaS 控制台: 模型推理 > API Key 页面创建
    """

    def __init__(self, session, region: str = "cn-north-4"):
        self.session = session
        self.credentials = session.credentials
        self.region = region
        self._base_url = os.environ.get("HUAWEI_MAAS_BASE_URL", MAAS_BASE_URL)
        self._api_key: Optional[str] = None

    @property
    def api_key(self) -> str:
        """获取 MaaS API Key"""
        if self._api_key:
            return self._api_key
        key = (
            os.environ.get("HUAWEI_MAAS_API_KEY")
            or os.environ.get("MAAS_API_KEY")
        )
        if not key:
            raise AuthError(
                "MaaS API Key not found",
                hint="在 MaaS 控制台创建 API Key，并设置环境变量 HUAWEI_MAAS_API_KEY",
            )
        self._api_key = key
        return key

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发起请求（添加 MaaS API Key 认证头）"""
        headers = kwargs.pop("headers", {})
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Bearer {self.api_key}"
        return requests.request(method, url, headers=headers, **kwargs)

    def converse(
        self,
        modelId: str,
        messages: list,
        system: Optional[list] = None,
        inferenceConfig: Optional[dict] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        调用 MaaS OpenAI 兼容 Chat Completions 接口

        参数尽量与原 Converse API 对齐，方便适配层切换。
        """
        model_config = self._resolve_model(modelId)
        endpoint = model_config["endpoint"]
        actual_model = model_config["id"]
        max_tokens = inferenceConfig.get("maxTokens", DEFAULT_MAX_TOKENS) if inferenceConfig else DEFAULT_MAX_TOKENS
        temperature = inferenceConfig.get("temperature", 0) if inferenceConfig else 0

        # 构建 OpenAI 兼容格式消息
        # system 消息转为 messages[0].role=system
        all_messages = []
        if system:
            system_text = "\n".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in system
            )
            all_messages.append({"role": "system", "content": system_text})
        all_messages.extend(messages)

        # 构建请求体（OpenAI Chat Completions 格式）
        payload = {
            "model": actual_model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        try:
            resp = self._make_request(
                "POST",
                endpoint,
                json=payload,
                timeout=120,
            )
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"ModelArts request failed: {e}", context={"url": endpoint})

        if resp.status_code == 401:
            raise AuthExpiredError("MaaS API Key 无效或已过期（ModelArts.81003）")
        if resp.status_code == 403:
            raise AuthError(f"ModelArts access denied: {resp.text}")
        if resp.status_code >= 400:
            raise UpstreamError(
                f"ModelArts API error: HTTP {resp.status_code}",
                context={"status_code": resp.status_code, "body": resp.text[:500]}
            )

        result = resp.json()

        # 转换响应格式（OpenAI → Converse 兼容格式）
        return self._to_converse_format(result, modelId, resp)

    def _resolve_model(self, model_id: str) -> dict:
        """解析模型 ID，返回模型配置"""
        # 如果传入的是已知模型 key（deepseek_v4_flash 等），返回配置
        if model_id in MODELS:
            return MODELS[model_id]
        # 否则视为 MaaS 实际模型 ID（如 deepseek-v4-flash），直接使用默认端点
        return {
            "id": model_id,
            "endpoint": f"{self._base_url}/chat/completions",
            "context_window": 128_000,
        }
    
    def _to_converse_format(self, openai_response: dict, model_id: str, raw_response: requests.Response) -> dict:
        """
        将 OpenAI Chat Completions 响应转为华为云内部格式
        
        这样上层调用代码（core.py 等）无需修改。
        """
        choice = openai_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        return {
            "output": {
                "message": {
                    "role": message.get("role", "assistant"),
                    "content": [
                        {"text": message.get("content", "")}
                    ]
                }
            },
            "stopReason": choice.get("finish_reason", "stop"),
            "usage": {
                "inputTokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
                "outputTokens": openai_response.get("usage", {}).get("completion_tokens", 0),
            },
            # 华为云特有字段
            "_huawei": {
                "model_id": model_id,
                "request_id": openai_response.get("id", ""),
            }
        }
    
    def list_models(self) -> dict:
        """列出可用模型（替代 pocsynth models）"""
        return {
            "models": [
                {
                    "modelId": model_id,
                    "description": config["description"],
                    "contextWindow": config["context_window"],
                }
                for model_id, config in MODELS.items()
            ],
            "default": DEFAULT_MODEL,
        }


def translate_modelarts_error(exc: Exception, *, service: str = "modelarts") -> Exception:
    """将华为云 ModelArts API 异常转为 DocSynthError 格式"""
    from pocsynth.errors import DocSynthError
    
    error_mapping = {
        # 华为云错误码 → DocSynthError 子类
        "InvalidToken": AuthExpiredError,
        "InvalidAccessKey": AuthError,
        "AccessDenied": AuthError,
        "ThrottlingException": UpstreamError,
        "ApiCallError": UpstreamError,
    }
    
    error_cls = error_mapping.get(type(exc).__name__, UpstreamError)
    return error_cls(str(exc), context={"service": service, "exception": type(exc).__name__})
