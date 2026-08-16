# 司法风险批量筛查

批量筛查中国企业司法风险线索，高效识别红黄灯风险。

## 适用场景

- 批量查询多家企业司法风险
- 贷后定期司法风险监控
- 资产包准入初筛
- 供应链司法风险排查

## 安装

方式一（推荐，通过Hermes技能中心）：

```bash
hermes skills install hermes skills install https://github.com/x18815379395-wq/hermes-jinghai-judicial-risk
```

方式二（手动安装，从GitHub克隆）：

```bash
git clone https://github.com/x18815379395-wq/hermes-jinghai-judicial-risk.git ~/.hermes/skills/financial-risk/jinghai-judicial-risk
hermes reload-skills
```

## 使用方法

对接靖海司法大数据，批量查询企业诉讼、执行、失信、限高、终本等司法风险信息。支持单批多家企业导入、风险等级分类（红/黄/绿灯）、批量导出风险报告。适用于贷后监控、尽调初筛和资产包审查。

具体使用方法请参考技能的 `SKILL.md` 文件。

## 许可证

MIT

## 作者

Hermes Agent Contributor
