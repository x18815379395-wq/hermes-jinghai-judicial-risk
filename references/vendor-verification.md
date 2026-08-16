# 鲸海数据API核验记录

核验日期：2026-08-10。

## 官方页面

- 官网：`https://www.kqdaas.com/`
- 文档中心：`https://www.kqdaas.com/docs`
- 鉴权：`https://www.kqdaas.com/docs/auth`
- 频率与配额：`https://www.kqdaas.com/docs/rate-limit`
- 错误码：`https://www.kqdaas.com/docs/error-codes`
- SDK示例：`https://www.kqdaas.com/docs/sdk`
- 司法风险方案：`https://www.kqdaas.com/solutions/judicial-risk-api`

## 已核验事实

- 鉴权头为`X-Jinghai-App-Id`与`X-Jinghai-Api-Key`；
- 默认网关为`https://www.kqdaas.com`；
- 成功判定需兼容`errcode/status/code=200`或`success=true`；
- 失信接口路径：`POST /DataService/judicial/breach-of-trust/{企业名称}?queryType=1`；
- 请求体包含`tag`、`pageIndex`、`pageSize`；
- 无凭据请求实测返回HTTP 401及JSON错误，不会产生有效查询结果；
- 官方尚未发布SDK；本Skill使用Python标准库实现；
- 官网声明司法风险维度包括裁判文书、开庭公告、被执行人、失信、终本、限高、司法协助及立案信息；当前脚本仅实现失信接口。

## 证据边界

官网对覆盖、准确性和免费额度的表述属于服务商披露。第三方API命中属于线索，关键事项须通过司法机关官方渠道或正式法律核查交叉验证。
