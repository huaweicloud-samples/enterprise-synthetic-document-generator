# 响应约束与检查清单

## 约束（C1-C7）

| # | 约束 | 检查结果 |
|---|------|---------|
| C1 | 全程使用华为云原生产品 | ✅ 华为云 SDK + requests |
| C2 | IaC 统一为 Terraform + huaweicloud Provider | ✅ 不适用（纯Python CLI，无IaC）|
| C3 | 有对标服务 | ✅ ModelArts + NLP |
| C4 | 函数代码不直连原云端点 | ✅ ModelArts API / NLP API |
| C5 | docs/ 以华为云视角撰写，无迁移措辞 | ✅ 本文档为华为云实践文档 |
| C6 | infra/ 通过 terraform validate | ✅ 不适用（无Terraform）|
| C7 | 产物结构符合 docs/ + others/ 分库约定 | ✅ |

---

## 自检清单

- [ ] `src/adapter/modelarts_adapter.py` — ModelArts 适配层完整
- [ ] `src/adapter/nlp_adapter.py` — NLP PII 检测适配层完整
- [ ] `src/adapter/huawei_session.py` — 华为云会话管理完整
- [ ] `src/adapter/cloud_switcher.py` — 云厂商切换开关 (`HUAWEI_CLOUD=1`)
- [ ] 所有适配层代码无残留其他云直接调用
- [ ] `docs/architecture.md` — 华为云架构说明完整
- [ ] `docs/deployment-guide.md` — 部署指南完整
- [ ] `others/` — 分析报告完整（analysis / service-mapping / migration-report）
- [ ] README.md 目录树与实际结构一致

---

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| ModelArts 模型可用性 | 中 | 需在华为云控制台确认模型接入状态 |
| NLP PII 检测精度 | 低 | NLP 实体识别可满足需求 |
| AK/SK 认证格式 | 中 | 需配置完整的 IAM Token 或 AK 直调 |
