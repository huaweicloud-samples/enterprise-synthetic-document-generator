# enterprise-synthetic-document-generator

<!-- README 语言规则：目标用户为中国客户（华为云国内客户），使用中文 -->

<!-- CRITICAL · 章节1 标题与徽章 -->
[![许可证: MIT-0](https://img.shields.io/badge/License-MIT--0-blue.svg)](./LICENSE)
[![华为云](https://img.shields.io/badge/%E5%8D%8E%E4%B8%BA%E4%BA%91-%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5-orange.svg)](https://www.huaweicloud.com)
[![企业合成文档](https://img.shields.io/badge/华为云-合成文档生成-blue)](https://www.huaweicloud.com)

---

## 2. 简介 / 概述

将参考 PDF（合同、表单、报告）转换为合成版本——保持结构和格式不变，但将正文和 PII 替换为真实感的虚构内容，然后扫描结果中是否有遗漏的 PII（华为云 NLP 审计）。

适用于：RAG 评估语料库生成、模型基准测试、合作伙伴文档交接等场景。

---

## 3. 目录

- [简介/概述](#2-简介--概述)
- [架构图](#4-架构图)
- [方案亮点](#5-方案亮点)
- [涉及云服务与费用](#6-涉及云服务与费用)
- [前置条件](#7-前置条件)
- [快速开始](#8-快速开始)
- [分步部署](#9-分步部署)
- [使用方法/验证](#10-使用方法验证)
- [清理资源](#11-清理资源)
- [详细说明](#12-详细说明)
- [依赖与致谢](#13-依赖与致谢)
- [FAQ](#14-faq)
- [许可证](#15-许可证)
- [联系方式](#16-联系方式)

---

## 4. 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户终端 (CLI)                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   pocsynth CLI (Python)                    │
│  ├─ PDF 解析 (PyMuPDF)                                 │
│  ├─ 华为云 ModelArts (文档重写)                        │
│  │     ↕ AK/SK 认证                                    │
│  │     ↕ ModelArts Studio API                         │
│  │        盘古系列 / Claude 兼容模型                    │
│  │                                                    │
│  ├─ 华为云 NLP (PII 审计)                            │
│  │     ↕ AK/SK 认证                                    │
│  │     ↕ NLP 实体识别 API                            │
│  │        人名/地址/证件/电话等实体                    │
│  │                                                    │
│  └─ 本地文件输出                                       │
│       ├─ *_cleaned.html (合成文档)                    │
│       ├─ *_pii_scan_audit.csv (PII 审计报告)       │
│       └─ *_page_*.html/png (分页预览)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 方案亮点

- **PDF 转合成文档**：保持原文档布局、章节结构、表格形式，文本替换为虚构内容
- **PII 审计**：华为云 NLP 实体识别，自动检测人名/地址/证件等敏感信息
- **多变量生成**：支持从同一 PDF 生成 N 个独立合成版本
- **离线数据生成**：使用预设生成结构化合成数据，无需 API 调用

---

## 6. 涉及云服务与费用

| 云服务 | 用途 | 计费模式 |
|--------|------|---------|
| ModelArts Studio | 文档重写 LLM | 按 token 计费 |
| NLP 实体识别 | PII 检测 | 按调用次数计费 |
| OBS | 临时文件存储 | 按存储量计费 |

---

## 7. 前置条件

- 华为云账号（已实名认证）
- 已开通 ModelArts Studio 服务
- 已开通 NLP 服务
- AK/SK 凭证（华为云控制台 → 我的凭证 → 访问密钥）
- Python 3.10+

---

## 8. 快速开始

```bash
# 克隆仓库
git clone <repo-url>
cd enterprise-synthetic-document-generator

# 安装依赖
pip install -e .

# 配置凭证
export HUAWEI_CLOUD=1
export HUAWEI_AK="your-ak"
export HUAWEI_SK="your-sk"
export HUAWEI_REGION="cn-north-4"

# 转换 PDF（合成模式）
pocsynth convert contract.pdf --model pangu_s --format html --mode synthetic --pii-audit --redact-values

# 生成合成数据（离线，无需 API）
pocsynth generate --preset crm_contacts --rows 1000 --seed 42 -o ./out
```

---

## 9. 分步部署

**Step 1：安装依赖**

```bash
pip install -e .
```

**Step 2：配置凭证**

```bash
export HUAWEI_CLOUD=1
export HUAWEI_AK="your-ak"
export HUAWEI_SK="your-sk"
export HUAWEI_REGION="cn-north-4"
```

**Step 3：运行合成转换**

```bash
pocsynth convert contract.pdf --model pangu_s --format html --mode synthetic --pii-audit --redact-values
```

---

## 10. 使用方法 / 验证

**查看输出**

```bash
# 合成文档
ls -la *_cleaned.html

# PII 审计报告
ls -la *_pii_scan_audit.csv
```

**验证 PII 脱敏**

```bash
# 检查审计报告
cat *_pii_scan_audit.csv
```

---

## 11. 清理资源

```bash
# 删除本地临时文件
rm -rf *_cleaned.html *_pii_scan_audit.csv ./out
```

> 注意：本工具主要在本地运行，不创建云端资源。

---

## 12. 详细说明

### 支持的 PDF 类型

| 类型 | 说明 |
|------|------|
| 合同 | 条款、双方信息 |
| 表单 | 字段、填写内容 |
| 报告 | 数据、分析结论 |

### PII 检测实体

| 实体类型 | 示例 |
|----------|------|
| 人名 | 张三、李四 |
| 证件号 | 身份证、护照 |
| 地址 | 家庭住址、单位地址 |
| 电话 | 手机号、固话 |

### 离线预设

| 预设 | 说明 |
|------|------|
| crm_contacts | CRM 联系人数据 |
| invoices | 发票数据 |
| orders | 订单数据 |

---

## 13. 依赖与致谢

- 华为云 ModelArts Studio：[华为云大模型平台](https://www.huaweicloud.com/product/modelarts.html)
- 华为云 NLP：[华为云 NLP 服务](https://www.huaweicloud.com/product/nlp.html)
- PDF 解析：[PyMuPDF](https://pymupdf.readthedocs.io/)
- 合成数据：[Faker](https://faker.readthedocs.io/)

---

## 14. FAQ

**Q：支持哪些 PDF 格式？**  
A：支持 PDF 1.4 及以上版本，包括扫描版（需 OCR）。

**Q：PII 检测精度如何？**  
A：华为云 NLP 在中文实体识别上表现良好，英文实体可能存在差异。

**Q：可以生成多少个变体？**  
A：`--num-docs N` 参数支持生成任意数量独立变体。

---

## 15. 许可证

本项目基于 **MIT-0 License**。  
完整许可证声明请参阅 [LICENSE](./LICENSE)。

---

## 16. 联系方式

- **维护者**：
- **项目主页**：
- **问题反馈**：请提交 GitHub Issue
