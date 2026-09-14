# 部署指南：合成文档生成器

## 前置要求

- Python 3.10+
- 华为云账号（已开通 ModelArts、NLP 服务）
- AK/SK 凭证（华为云控制台 → 我的凭证 → 访问密钥）

## 安装

### 方式 1：从本仓库安装

```bash
git clone <本仓库URL>
cd enterprise-synthetic-document-generator
pip install -e .
```

### 方式 2：仅安装依赖（不安装本仓库）

```bash
pip install pymupdf>=1.27 beautifulsoup4>=4.14 requests>=2.33 html2text>=2025.4.15 typer>=0.12 rich>=13 faker>=37
pip install huaweicloudsdkcore  # 华为云 AK/SK 签名（NLP 调用必需）
```

## 配置华为云凭证

### 环境变量方式（推荐）

```bash
# 华为云 AK/SK（必需，用于 NLP 服务签名调用）
export HUAWEI_AK="your-access-key-id"
export HUAWEI_SK="your-secret-access-key"
export HUAWEI_REGION="cn-north-4"

# MaaS API Key（必需，用于 LLM 文档重写；在 ModelArts Studio 控制台创建）
export HUAWEI_MAAS_API_KEY="your-maas-api-key"

# 项目 ID（可选；不设置时自动通过 IAM API 按区域查询）
export HUAWEI_PROJECT_ID="your-project-id"

# 启用华为云模式（切换云厂商的关键开关）
export HUAWEI_CLOUD=1
```

### 配置文件方式

```bash
# 创建配置文件
mkdir -p ~/.huaweicloud
cat > ~/.huaweicloud/credentials << 'EOF'
{
    "default": {
        "ak": "your-access-key-id",
        "sk": "your-secret-access-key",
        "region": "cn-north-4",
        "username": "your-username",
        "password": "your-password",
        "domain_name": "your-domain-name",
        "project_id": "your-project-id"
    }
}
EOF
```

## 快速开始

### 1. 验证凭证

```bash
export HUAWEI_CLOUD=1
python -c "
from adapter.huawei_session import HuaweiSession
s = HuaweiSession()
print('Region:', s.region)
print('Credentials OK')
"
```

### 2. 转换 PDF

```bash
export HUAWEI_CLOUD=1
pocsynth convert contract.pdf --model deepseek_v4_flash --format html --mode synthetic --pii-audit --redact-values
```

### 3. 批量生成合成数据

```bash
export HUAWEI_CLOUD=1
pocsynth generate --preset crm_contacts --rows 1000 --seed 42 -o ./out
```

## 模型选择

模型通过 ModelArts Studio MaaS 的 OpenAI 兼容接口调用（中国大陆站当前部署于**西南-贵阳一**区域，价格按 Token 计费）：

| 模型 | model 参数值 | 输入价格 | 输出价格 | 适用场景 |
|------|-------------|---------|---------|---------|
| DeepSeek V4 Flash | `deepseek-v4-flash` | ¥0.001/千Token | ¥0.002/千Token | 批量文档重写（推荐） |
| DeepSeek V4 Pro | `deepseek-v4-pro` | ¥0.012/千Token | ¥0.024/千Token | 高质量文档 |
| GLM-5.2 | `glm-5.2` | ¥0.008/千Token | ¥0.028/千Token | 高质量文档 |

> 完整模型列表与实时价格以 [MaaS 价格详情](https://support.huaweicloud.com/price-maas/price-maas-0002.html) 为准。

## 认证方式对比

| 方式 | 适用场景 | 配置难度 |
|------|---------|---------|
| MaaS API Key | LLM 调用（Bearer Token） | 低 |
| AK/SK 签名 | NLP 服务调用（SDK-HMAC-SHA256） | 低 |
| 配置文件 | 团队共享配置 | 低 |

## 华为云服务开通

开通操作均需在控制台完成（免费开通，按量计费）：

1. **NLP 服务（cn-north-4）**: 控制台 → 自然语言处理 NLP → 总览 → 单击"开通服务"。未开通时调用返回 `ModelArts.4204`（not subscribed）。
2. **ModelArts Studio MaaS（西南-贵阳一）**: 控制台 → ModelArts Studio → 模型推理 → 预置服务，开通所需模型（如 DeepSeek V4 Flash）；并在 "API Key" 页面创建 API Key。

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| `No Huawei Cloud credentials` | 未设置环境变量 | 设置 `HUAWEI_AK`/`HUAWEI_SK` |
| `MaaS API Key 无效（ModelArts.81003）` | API Key 未设置/错误 | 设置 `HUAWEI_MAAS_API_KEY`，确认与模型同区域 |
| `ModelArts.4204 not subscribed` | NLP 服务未开通 | 控制台 NLP 总览页开通服务（区域与调用一致） |
| `NLP API 认证失败` | AK/SK 无效或未安装签名库 | 检查 AK/SK；`pip install huaweicloudsdkcore` |
| `NLP.0301 文本长度错误` | 分块超过限制 | 中文≤512字符、英文≤2000字符（适配层已自动分块） |
