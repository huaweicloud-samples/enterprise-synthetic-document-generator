# Copyright (C) 2026 华为云
# SPDX-License-Identifier: MIT-0
"""
华为云 NLP 适配层
将 PII 实体检测调用适配为华为云 NLP 命名实体识别 API

华为云 NLP 服务: https://www.huaweicloud.com/product/nlp.html
API 文档: https://support.huaweicloud.com/api-nlp/nlp_03_0010.html
端点: https://nlp-ext.cn-north-4.myhuaweicloud.com/v1/{project_id}/nlp-fundamental/ner
认证: AK/SK 签名（SDK-HMAC-SHA256）或 X-Auth-Token

注意:
- 使用前需在 NLP 控制台"总览"页面开通服务（免费开通，按调用次数计费）
- 基础版 NER 支持实体类型: 人名(per/nr)、地名(loc/ns)、组织机构(org/nt)、时间(t)
- 邮箱/手机号等扩展 PII 类型需使用"命名实体识别(领域版)"(ner/domain)
- 文本长度限制: 中文 1~512 字符，英文/西班牙文 1~2000 字符
"""

from __future__ import annotations

import json
from typing import Optional

import requests

from pocsynth.errors import AuthError, AuthExpiredError, UpstreamError

# 华为云 NLP API 端点（区域: cn-north-4）
NLP_ENDPOINT = "https://nlp-ext.{region}.myhuaweicloud.com/v1/{project_id}/nlp-fundamental/ner"

# NLP 实体标签 → 内部 PII 类型（基础版 NER 支持的标签）
# 英文: per/loc/org/t；中文: nr/ns/nt/t
TAG_TO_TYPE = {
    "per": "NAME",            # 人名（英文）
    "nr": "NAME",             # 人名（中文）
    "loc": "ADDRESS",         # 地名（英文）
    "ns": "ADDRESS",          # 地名（中文）
    "org": "ORGANIZATION",    # 组织机构（英文）
    "nt": "ORGANIZATION",     # 组织机构（中文）
    "t": "DATE_TIME",         # 时间
}

# NLP 文本长度限制（按语言）
TEXT_LENGTH_LIMIT = {"zh": 512, "en": 2000, "es": 2000}


def _sign_request(ak: str, sk: str, method: str, url: str, body: bytes = b"") -> dict:
    """
    使用官方 SDK 的签名器构建华为云 AK/SK 签名请求头（SDK-HMAC-SHA256）

    依赖: pip install huaweicloudsdkcore
    """
    from urllib.parse import urlsplit
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.sdk_request import SdkRequest
    from huaweicloudsdkcore.signer.signer import Signer

    parsed = urlsplit(url)
    rq = SdkRequest(
        schema=parsed.scheme,
        host=parsed.netloc,
        resource_path=parsed.path,
        method=method.upper(),
        query_params=[],
        header_params={"Content-Type": "application/json"},
        body=body,
    )
    Signer(BasicCredentials(ak, sk, None)).sign(rq)

    headers = {}
    for k, v in rq.header_params.items():
        if k.lower() != "host":
            headers[k] = v
    return headers


class HuaweiNLPClient:
    """
    华为云 NLP 客户端

    功能: PII 实体检测
    API: 命名实体识别（基础版）POST /v1/{project_id}/nlp-fundamental/ner
    """

    def __init__(self, session, region: str = "cn-north-4"):
        self.session = session
        self.credentials = session.credentials
        self.region = region
        self._project_id: Optional[str] = None

    @property
    def project_id(self) -> str:
        """获取项目 ID（华为云资源管理单元）"""
        if not self._project_id:
            self._project_id = self.credentials.project_id or self._resolve_project_id()
        if not self._project_id:
            raise AuthError(
                "Huawei Cloud project ID not found",
                hint="Set HUAWEI_PROJECT_ID env var or configure in credentials file",
            )
        return self._project_id

    def _resolve_project_id(self) -> Optional[str]:
        """通过 IAM API 按区域查询项目 ID（AK/SK 签名）"""
        url = f"https://iam.{self.region}.myhuaweicloud.com/v3/auth/projects"
        try:
            headers = _sign_request(self.credentials.ak, self.credentials.sk, "GET", url)
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                for project in resp.json().get("projects", []):
                    if project.get("name") == self.region:
                        return project["id"]
        except Exception:
            pass
        return None

    def detect_pii_entities(self, Text: str, LanguageCode: str = "en", **kwargs) -> dict:
        """
        检测文本中的 PII 实体（命名实体识别基础版）

        Args:
            Text: 待检测文本（中文≤512字符，英文≤2000字符）
            LanguageCode: 语言代码（zh、en、es）

        Returns:
            dict: {"Entities": [{"Type": ..., "BeginOffset": ..., "EndOffset": ..., "Score": ...}]}
        """
        lang = self._map_language_code(LanguageCode)
        max_len = TEXT_LENGTH_LIMIT.get(lang, 2000)
        if len(Text) > max_len:
            Text = Text[:max_len]
        if not Text:
            return {"Entities": []}

        endpoint = NLP_ENDPOINT.format(region=self.region, project_id=self.project_id)

        # 华为云 NLP 请求体格式: {"text": ..., "lang": ...}
        payload = json.dumps({"text": Text, "lang": lang}).encode("utf-8")

        # AK/SK 签名请求头
        try:
            headers = _sign_request(self.credentials.ak, self.credentials.sk, "POST", endpoint, payload)
        except ImportError:
            raise AuthError(
                "huaweicloudsdkcore is required for NLP API signing",
                hint="Run: pip install huaweicloudsdkcore",
            )

        # 备选: 若会话已有 IAM Token 则优先使用
        token = getattr(self.session, "_token", None)
        if token:
            headers.pop("Authorization", None)
            headers["X-Auth-Token"] = token

        try:
            resp = requests.post(endpoint, data=payload, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"NLP API request failed: {e}")

        if resp.status_code == 401:
            raise AuthExpiredError("NLP API 认证失败（AK/SK 无效或 Token 过期）")
        if resp.status_code == 403:
            raise AuthError(f"NLP API access denied: {resp.text}")
        if resp.status_code >= 400:
            raise UpstreamError(
                f"NLP API error: HTTP {resp.status_code}",
                context={"status_code": resp.status_code, "body": resp.text[:500]}
            )

        return self._to_standard_format(resp.json(), Text)

    def _map_language_code(self, language_code: str) -> str:
        """映射语言代码（华为云 NLP 仅支持 zh/en/es）"""
        mapping = {"en": "en", "zh": "zh", "zh-cn": "zh", "es": "es"}
        return mapping.get(language_code.lower(), "en")

    def _to_standard_format(self, nlp_response: dict, original_text: str) -> dict:
        """
        将华为云 NLP 响应转为内部标准格式

        华为云 NLP 响应格式:
        {
            "named_entities": [
                {"word": "张三", "tag": "nr", "offset": 0, "len": 2},
                ...
            ]
        }
        """
        entities = nlp_response.get("named_entities", [])

        standard_entities = []
        for entity in entities:
            begin_offset = entity.get("offset", 0)
            entity_len = entity.get("len", 0)
            end_offset = begin_offset + entity_len
            tag = entity.get("tag", "")

            standard_entities.append({
                "BeginOffset": begin_offset,
                "EndOffset": end_offset,
                "Type": TAG_TO_TYPE.get(tag, "OTHER"),
                "Score": 1.0,
                # 额外字段（用于审计）
                "_huawei_tag": tag,
                "Text": original_text[begin_offset:end_offset],
            })

        return {"Entities": standard_entities}

    def scan_for_pii(
        self,
        text: str,
        folder_name: str = "pii-audit",
        filename: str = "all",
        page_num: int = 0,
        redact_values: bool = False,
    ) -> list[dict]:
        """
        PII 扫描入口

        这是 pocsynth 内部调用的主要接口。
        """
        import csv
        import os
        from pathlib import Path

        os.makedirs(folder_name, exist_ok=True)

        # 分块处理: 中文每块 512 字符、英文每块 2000 字符，重叠 200
        # （华为云 NLP 文本长度限制: zh 1~512, en/es 1~2000）
        CHUNK_OVERLAP = 200
        max_len = TEXT_LENGTH_LIMIT.get("en", 2000)

        step = max(1, max_len - CHUNK_OVERLAP)
        chunk_starts = list(range(0, max(len(text), 1), step))
        chunks = [
            (start, text[start:start + max_len])
            for start in chunk_starts
        ]

        all_entities = []
        seen_offsets: set[tuple] = set()

        for chunk_index, (chunk_start, chunk) in enumerate(chunks):
            response = self.detect_pii_entities(chunk, LanguageCode="en")

            for entity in response.get("Entities", []):
                begin_offset = entity["BeginOffset"] + chunk_start
                end_offset = entity["EndOffset"] + chunk_start
                key = (begin_offset, end_offset, entity["Type"])

                if key in seen_offsets:
                    continue
                seen_offsets.add(key)

                detected_text = text[begin_offset:end_offset]

                all_entities.append({
                    "FileName": filename,
                    "PageNumber": page_num,
                    "Type": entity["Type"],
                    "Score": entity["Score"],
                    "BeginOffset": begin_offset,
                    "EndOffset": end_offset,
                    "Value": "[REDACTED]" if redact_values else detected_text,
                })

        # 写入审计 CSV
        audit_file_path = Path(folder_name) / f"{filename}_pii_scan_audit.csv"
        write_header = not audit_file_path.exists() or audit_file_path.stat().st_size == 0

        with open(audit_file_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            if write_header:
                writer.writerow(["FileName", "PageNumber", "Type", "Score", "BeginOffset", "EndOffset", "Value"])
            for entity in all_entities:
                writer.writerow([
                    entity["FileName"],
                    entity["PageNumber"],
                    entity["Type"],
                    entity["Score"],
                    entity["BeginOffset"],
                    entity["EndOffset"],
                    entity["Value"],
                ])

        return all_entities


def translate_nlp_error(exc: Exception, *, service: str = "nlp") -> Exception:
    """将华为云 NLP API 异常转为 DocSynthError 格式"""
    from pocsynth.errors import DocSynthError

    error_mapping = {
        "InvalidToken": AuthExpiredError,
        "InvalidAccessKey": AuthError,
        "AccessDenied": AuthError,
        "ThrottlingException": UpstreamError,
    }

    error_cls = error_mapping.get(type(exc).__name__, UpstreamError)
    return error_cls(str(exc), context={"service": service, "exception": type(exc).__name__})
