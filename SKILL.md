---
name: jinghai-judicial-risk
description: Batch-screen Chinese companies for judicial risk clues.
version: 0.1.0
author: stormchaser
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [financial-risk, judicial-risk, due-diligence, china]
    related_skills: [corporate-credit-due-diligence, kyc-screening]
---

# 鲸海企业司法风险批量筛查

将鲸海数据API作为第三方补充线索源，批量查询企业当前或历史失信被执行人记录。结果不能替代中国执行信息公开网、裁判文书网、法院材料、征信报告或正式法律意见；重大命中必须回到官方来源复核。

## When to Use

- 承租人、担保人、关联企业的批量失信筛查；
- 存量客户司法风险定期监测；
- 需要以JSON保留查询时点、请求编号和错误状态；
- 不用于仅凭第三方“未命中”作出无风险结论。

## Prerequisites

正式API由鲸海后台开通，凭据只从环境变量读取：

- `JINGHAI_APP_ID`
- `JINGHAI_API_KEY`
- `JINGHAI_API_BASE`（可选，默认`https://www.kqdaas.com`）

官方文档显示当前接口统一按0.05元/次计费，实名认证可获得账户级1,000次免费调用总量；免费规则、价格和授权范围可能变化，调用前以官网账户显示为准。不得把凭据写入脚本、Skill、报告、日志或聊天。

## How to Run

通过`terminal`调用随Skill安装的脚本：

```bash
python ~/.hermes/skills/financial-risk/jinghai-judicial-risk/scripts/jinghai_judicial.py --check

python ~/.hermes/skills/financial-risk/jinghai-judicial-risk/scripts/jinghai_judicial.py \
  --company "企业全称" --tag 0 --output result.json

python ~/.hermes/skills/financial-risk/jinghai-judicial-risk/scripts/jinghai_judicial.py \
  --input companies.csv --tag 0 --interval 0.5 --output judicial-risk.json
```

CSV必须包含`company`列；TXT为每行一家企业。`tag=0`查询当前失信，`tag=1`查询历史失信。

## Procedure

1. 用统一社会信用代码或工商资料核定企业全称，避免同名主体误判。完成标准：输入名单每家企业均能唯一识别。
2. 先运行`--check`，只检查凭据存在性，不调用计费接口。完成标准：返回`configured: true`。
3. 小批量查询1—2家公开测试企业，确认账户授权和字段结构。完成标准：`query_status=success`，并保留`request_id`和`queried_at`。
4. 对正式名单执行批量查询。完成标准：汇总中的`errors=0`；若非零，单独处理错误，禁止将错误解释成“无记录”。
5. 对命中记录通过官方司法渠道交叉验证案号、主体、立案时间、履行状态和执行标的。完成标准：正式报告区分“API线索”“官方核实”和“待核实”。
6. 在审查底稿中记录来源、查询时点、适用范围和证据等级。完成标准：任何“未发现”结论都明确限定为本次接口及查询时点。

## Output Semantics

- `query_status=success`且`records=[]`：本次API未返回记录，不等于主体绝对无司法风险；
- `query_status=error`：查询失败或未授权，绝不能写成无记录；
- `source`固定标识为第三方线索源；
- 默认只取指定页，不自动消耗额度遍历全部分页；需要全量时先确认预算和总量。

## Pitfalls

- 401通常是凭据缺失或错误；403可能是未实名、未授权、余额/次数不足、授权过期或IP白名单问题；
- 429、500、502、504会有限次指数退避重试，禁止无限重试；
- 企业名称作为路径参数传输，脚本会URL编码，但仍需使用准确全称；
- 第三方数据可能存在延迟、漏项或主体映射错误；
- 批量查询涉及付费额度，默认先小样本验证；
- 司法风险不只有失信，还应另行核查被执行、限高、终本、诉讼、股权冻结和行政处罚。

## Verification

```bash
python ~/.hermes/skills/financial-risk/jinghai-judicial-risk/scripts/test_jinghai_judicial.py
python -m py_compile ~/.hermes/skills/financial-risk/jinghai-judicial-risk/scripts/jinghai_judicial.py
```

安装验收需要同时满足：Skill可被Hermes识别、6项本地测试通过、缺凭据保护返回结构化错误；配置真实凭据后还需执行一次只读生产查询，才可标记为完整可用。
