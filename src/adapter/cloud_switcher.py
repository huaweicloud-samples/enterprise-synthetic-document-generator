# Copyright (C) 2026 华为云
# SPDX-License-Identifier: MIT-0
"""
华为云适配层入口：提供统一的云厂商切换接口

通过环境变量 HUAWEI_CLOUD 切换云厂商：
- HUAWEI_CLOUD=1: 使用华为云适配层（ModelArts + NLP）
- 其他/未设置: 使用原始仓库配置
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pocsynth.errors import DocSynthError

# 云厂商检测
_USE_HUAWEI = os.environ.get("HUAWEI_CLOUD", "").lower() in ("1", "true", "yes")

if _USE_HUAWEI:
    # ── 华为云适配 ────────────────────────────────────────────
    from adapter.huawei_session import HuaweiSession as _HuaweiSession
    from adapter.modelarts_adapter import HuaweiModelArtsClient
    from adapter.nlp_adapter import HuaweiNLPClient
    
    def make_session(profile=None, region=None):
        """创建华为云会话"""
        from adapter.huawei_session import DEFAULT_REGION
        return _HuaweiSession(profile=profile, region=region or DEFAULT_REGION)

    def resolve_region(cli_region=None, profile=None):
        """解析华为云区域"""
        huawei_region = cli_region or os.environ.get("HUAWEI_REGION") or "cn-north-4"
        return huawei_region, "huawei_env"
    
    __all__ = [
        "make_session",
        "resolve_region",
        "HuaweiSession",
        "HuaweiModelArtsClient",
        "HuaweiNLPClient",
    ]
    
    print("[PoCSynth] 华为云模式已启用 (HUAWEI_CLOUD=1)")
    print("[PoCSynth] 使用 ModelArts + NLP 服务")
