# Copyright (C) 2026 华为云
# SPDX-License-Identifier: MIT-0
"""
华为云会话管理
支持 AK/SK 认证 + IAM Token 两种模式
"""

from __future__ import annotations

import os
from typing import Optional

import requests
from pocsynth.errors import AuthError, AuthExpiredError

# 华为云 Python SDK (可选，已安装则导入)
try:
    import openstack
    _HAS_OPENSTACK_SDK = True
except ImportError:
    _HAS_OPENSTACK_SDK = False


DEFAULT_REGION = "cn-north-4"


class HuaweiCredentials:
    """华为云凭证管理"""
    
    def __init__(
        self,
        ak: Optional[str] = None,
        sk: Optional[str] = None,
        region: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        self.ak = ak or os.environ.get("HUAWEI_AK") or os.environ.get("HW_ACCESS_KEY")
        self.sk = sk or os.environ.get("HUAWEI_SK") or os.environ.get("HW_SECRET_KEY")
        self.region = region or os.environ.get("HUAWEI_REGION") or DEFAULT_REGION
        self.project_id = project_id or os.environ.get("HUAWEI_PROJECT_ID")
        
        if not self.ak or not self.sk:
            raise AuthError(
                "No Huawei Cloud credentials found",
                hint="Set HUAWEI_AK/HUAWEI_SK env vars, or run: esdk-obs-python configure",
            )
    
    def get_iam_token(self) -> str:
        """获取 IAM Token (password 模式)"""
        # 华为云 IAM Token 获取
        # 用户名/密码/域名从环境变量或配置文件读取
        from os import getenv
        
        username = getenv("HUAWEI_USERNAME")
        password = getenv("HUAWEI_PASSWORD")
        domain_name = getenv("HUAWEI_DOMAIN_NAME")
        
        if not all([username, password, domain_name]):
            # 尝试从配置文件读取
            config = self._load_config()
            username = username or config.get("username")
            password = password or config.get("password")
            domain_name = domain_name or config.get("domain_name")
        
        if not all([username, password, domain_name]):
            raise AuthError(
                "Huawei Cloud IAM credentials incomplete",
                hint="Set HUAWEI_USERNAME, HUAWEI_PASSWORD, HUAWEI_DOMAIN_NAME env vars",
            )
        
        url = f"https://iam.myhuaweicloud.com/v3.0/OS-AUTH/tokens"
        payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": username,
                            "password": password,
                            "domain": {"name": domain_name}
                        }
                    }
                },
                "scope": {"project": {"name": self.region}}
            }
        }
        
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code not in (200, 201):
            raise AuthError(f"IAM token获取失败: HTTP {resp.status_code}", hint="Check credentials")
        
        return resp.headers.get("X-Subject-Token", "")
    
    def _load_config(self) -> dict:
        """从 ~/.huaweicloud/config.json 加载配置（如果存在）"""
        import os, json
        config_path = os.path.expanduser("~/.huaweicloud/config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        return {}
    
    def to_dict(self) -> dict:
        return {
            "ak": self.ak,
            "sk": self.sk,
            "region": self.region,
            "project_id": self.project_id,
        }


class HuaweiSession:
    """
    华为云会话
    提供 ModelArts、NLP、OBS 等服务的客户端
    """
    
    def __init__(
        self,
        ak: Optional[str] = None,
        sk: Optional[str] = None,
        region: Optional[str] = None,
        profile: Optional[str] = None,
    ):
        if profile:
            # 从命名配置加载
            creds = _load_profile_credentials(profile)
            self.credentials = HuaweiCredentials(
                ak=creds.get("ak"), sk=creds.get("sk"),
                region=creds.get("region", DEFAULT_REGION)
            )
        else:
            self.credentials = HuaweiCredentials(ak=ak, sk=sk, region=region)
        
        self.region = self.credentials.region
        self._token: Optional[str] = None
    
    @property
    def token(self) -> str:
        """获取 IAM Token（延迟加载）"""
        if not self._token:
            self._token = self.credentials.get_iam_token()
        return self._token
    
    def client(self, service_name: str):
        """
        获取华为云服务客户端
        """
        if service_name in ("modelarts", "ma"):
            from adapter.modelarts_adapter import HuaweiModelArtsClient
            return HuaweiModelArtsClient(self, region=self.region)
        elif service_name == "nlp":
            from adapter.nlp_adapter import HuaweiNLPClient
            return HuaweiNLPClient(self, region=self.region)
        elif service_name == "obs":
            # OBS 客户端需安装 esdk-obs-python，按需懒加载
            try:
                from adapter.obs_adapter import OBSClient
                return OBSClient(self)
            except ImportError:
                raise ValueError(
                    "OBS client requires esdk-obs-python; run: pip install esdk-obs-python"
                )
        else:
            raise ValueError(f"Unsupported service: {service_name}")
    
    def __repr__(self):
        return f"HuaweiSession(region='{self.region}')"


def _load_profile_credentials(profile: str) -> dict:
    """从 ~/.huaweicloud/credentials 加载命名配置"""
    import os, json
    creds_path = os.path.expanduser(f"~/.huaweicloud/credentials")
    if os.path.exists(creds_path):
        with open(creds_path) as f:
            all_creds = json.load(f)
            if profile in all_creds:
                return all_creds[profile]
    raise AuthError(f"Profile '{profile}' not found in ~/.huaweicloud/credentials")


# 兼容别名
def make_session(profile: Optional[str] = None, region: Optional[str] = None) -> HuaweiSession:
    """创建华为云会话（兼容原接口）"""
    return HuaweiSession(profile=profile, region=region or DEFAULT_REGION)
