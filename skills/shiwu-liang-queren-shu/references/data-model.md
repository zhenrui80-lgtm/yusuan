# 两表数量核验数据模型

`scripts/reconcile.py` 只使用 Python 标准库。版本为 `physical-materials/1`，完整可运行样例见 [example-model.json](example-model.json)。样例全部为虚构数据。

```text
python scripts/reconcile.py model.json --output report.json
python scripts/reconcile.py model.json --readback final-readback.json --output report.json
python scripts/test_reconcile.py
```

`--out` 与 `--output` 等价。成功退出码为 0；输入、数量或读回不合格退出码为 2，并写入错误报告，覆盖旧的成功报告。未知量本身可以合法存在：必须同时检查 `complete`，不能只看退出码。无 `--readback` 时 `artifact_verified` 永远为 false。

报告路径不得与model、readback或readback声明的原Word/Excel源文件相同；解析绝对路径及同文件别名均会拒绝，错误仅输出到stderr，不覆盖原件。

## 数量与精度

所有数量及损耗率必须是非负十进制**字符串**，例如 `"8"`、`"0.025"`；未知数量为 JSON `null`，不得填 0。拒绝 JSON 数字、布尔值、负数、科学计数法和 NaN/Infinity。允许显式已知零。最多 36 位数字、18 位小数；显示精度为 0–12 位；舍入方式仅支持 `ROUND_HALF_UP`。

材料 `qty` 是调用方已按清单、尺寸、配合比或定额计算的**额外损耗前基数**，并非脚本自动从工程量推算的结果。若基数已含定额消耗损耗，将 `loss.already_in_quota` 设为 true，额外 `rate` 必须为 `"0"`。脚本不核验原计算式、资料归属或证据真伪。完整底稿仍需 `formula`、`assumptions`、原文页/表/行等定位及用户范围决定出处；这些可作为额外字段保存在输入中，本工具不会据此证明其正确。

每个材料贡献的输出明确区分：

- `base_qty`：输入的基数。
- `adopted_qty`：未做显示舍入的采用量，estimated 为 `base × (1 + rate)`；owner_actual 不加损耗。
- `display_qty`：按单位精度舍入的确认书展示量；未知仍为 null。

台账按**已经逐条舍入的 display_qty 求和**。例如两条 `0.0045kg`，显示精度 3 位时，各为 `0.005kg`，台账为 `0.010kg`，不能先合计成 `0.009kg`。不可拆分成品必须在输入时即为整数，不能把 8.08 舍入成 8 以掩盖损耗错误；显示为整数。

## 顶层字段

| 字段 | 内容 |
| --- | --- |
| `schema_version` | 固定 `physical-materials/1` |
| `works` | 原工程量条目，非空数组 |
| `materials` | 材料或机械贡献数组；一条贡献只计一次，可关联多项工程 |
| `owner_lines` | 甲方采用的原始数量行，可为空数组 |
| `display` | `default_decimals`、`unit_decimals` 对象及 `rounding: "ROUND_HALF_UP"` |
| `decisions` | 下面的显式策略对象 |

```json
{
  "ledger_mode": "equal_adopted",
  "equal_adopted_authorized": true,
  "dates": "blank",
  "blank_dates_authorized": true
}
```

这四个值不提供隐式默认。`equal_adopted` 仅用于用户明确允许把同一采用量填入入库、出库两栏的情形，采用量可以来自测算或甲方资料。它不是实际收发流水核算。实际入库、出库不同的 `actual` 等模式将明确拒绝；不得把其改名为 equal_adopted 来取得通过。其他日期策略也不支持。范围取上限、下限、采购包装及备料取整等不由本工具决定，必须由调用方依据用户指示或证据处理。

## works 条目

必填 `id`、`name`、`qty`、`unit`、`source_refs`。ID在本数组内唯一；name为原清单名称；qty允许null，但必须补 `pending_reason`。`source_refs` 是非空字符串数组，内容应为稳定、可查的原文件页/表/行定位。

左栏优化措辞可以与原名称不同。独立回读时，应保留原BOQ名称的标准化 `name` 字段，通过可追溯定位把实际整段左栏归回该条目；不要从模型直接拷贝并假称读取了全文。工具比较ID、原名字段、数量、单位；完整工序、部位、尺寸与范围的覆盖仍需人工逐项检查。

## materials 条目

| 字段 | 规则 |
| --- | --- |
| `id` | 全部材料贡献中的唯一ID，不是材料品种ID |
| `work_ids` | 非空、无重复且存在于works的ID数组；多工程关联不重复计料 |
| `name` / `unit` / `scope_key` | 非空字符串，无首尾空格；scope区分不可合并的供料/核算范围 |
| `spec` | 完整规格字符串，或null/空串；未知必须有pending_reason，不得为过校验编规格 |
| `qty` | 额外损耗前基数，十进制字符串或null；未知必须有pending_reason |
| `kind` | `main`、`auxiliary`、`machine` |
| `source_refs` | 非空数量/工作依据定位数组；未知量也可指向待计量的原工作项 |
| `spec_refs` | 已知规格必须非空；未知规格可为[] |
| `quantity_basis` | `estimated`或`owner_actual` |
| `owner_line_id` | owner_actual所采用的owner_lines ID；estimated必须null或省略 |
| `loss` | 对象，含rate、already_in_quota、refs，见下文 |
| `indivisible` | 显式布尔值；成品件/套等不可拆分量设true |
| `allocation_refs` | 仅在同一甲方行拆给多个贡献时使用；每条都需非空分配证据 |
| `pending_reason` | qty或spec未知时必填；可以说明两者分别待核的内容 |

确认书纳入 main 与 machine；台账仅汇总 main；auxiliary不进入两表，但仍须通过数据结构和数量规则校验。输出会列出被排除的辅材。采用这套分类前须确认用户范围，脚本不自动识别主辅材。

`loss.rate` 为额外损耗小数率，仅支持0至1；`already_in_quota`是布尔值。rate大于0或already_in_quota为true时，`loss.refs`必须有依据。不能将定额含损耗基数再加率；owner_actual、indivisible不能加率。工具检查声明之间的一致性，不能识别调用方是否误把已含损耗量标成未含损耗。

`name/spec/unit/scope_key` 四项严格相同才汇总，不做字符同义、尺寸、单位、包装或品牌自动转换。未知规格规范化为null；多条同名同单位同scope的未知规格不能安全认定相同，会拒绝汇总，需用有意义的不同scope_key分开。不同不可拆分标记的同组贡献同样拒绝。

组内有未知qty时，`qty/in_qty/out_qty`均为null，`known_subtotal`仅为已知贡献小计，`unknown_ids`列出未定贡献，`quantity_complete=false`。仅规格未知但数量齐全时，数量可显示而`complete=false`。不要把已知小计写入未知完整量的数量格。

## owner_lines 及分配

每行含唯一 `id`、已知 `qty`、`unit`、`basis`及非空 `source_refs`。basis只允许 `received`（收货）或 `issued`（实发），明确本次采用哪列；本脚本不自动选择两列之一。

owner_actual材料必须与采用行同单位；单条贡献qty须等于采用行qty。一个原始来源行也可按有证据的分配拆给多项：每条贡献均需非空allocation_refs、同单位，所有原始qty之和必须恰好等于采用行qty。不许多条各自引用整行全量，也不许通过给同一来源行编造多个owner_line_id绕过校验。输出`owner_line_allocations`记录分配守恒，未用甲方行另列。分配守恒检查原始精确值；显示层仍按逐项舍入求和，调用方应选择足够精度并核对可能的显示尾差。

原工作量单位与材料单位可以不同，例如安装按套、实体件按个；脚本不把它们互换，也不据此推导材料配置。若甲方凭据确需单位换算，调用方应先形成有原量、原单位、换算式、适用范围及定位的换算证据，再以同一规范单位提供采用行和材料量。工具只核其内部一致性，不证明换算合理。

## 独立读回 --readback

工具不包含DOCX/XLSX解析器，也不生成读回数据。应先独立读取最终Word的左量/右料和最终Excel的台账，再生成以下结构。**不能复制model或本脚本输出伪装成readback。** 同一行跨页延续、合并单元格及一料关联多项，须先按实际模板中的定位完成无重复的标准化。

```json
{
  "schema_version": "physical-materials-readback/1",
  "extraction": {
    "independent": true,
    "method": "说明实际使用的文件解析及定位方法",
    "sources": {
      "confirmation": {"path": "final.docx", "sha256": "最终文件的64位SHA256"},
      "ledger": {"path": "final.xlsx", "sha256": "最终文件的64位SHA256"}
    }
  },
  "confirmation": {
    "works": [{"id": "W1", "name": "原清单名称", "qty": "8", "unit": "套"}],
    "materials": [{"id": "M1", "work_ids": ["W1"], "name": "标准成品", "spec": "规格A", "unit": "个", "kind": "main", "scope_key": "zone-a", "qty": "8"}],
    "date_fields": {"原签认日期栏定位": ""}
  },
  "ledger": {
    "rows": [{"name": "标准成品", "spec": "规格A", "unit": "个", "scope_key": "zone-a", "in_qty": "8", "out_qty": "8", "in_date": "", "out_date": null}]
  }
}
```

示意hash和说明文字须由实际提取替换；上方只说明结构，不是可冒充独立提取的测试样本。相对路径按readback文件所在目录解析。脚本校验文件存在与SHA256，不重新解析文件内容。`independent: true`是调用方声明，hash不能证明提取独立或证据关联正确。

读回qty使用**实际展示**的值；未知为null，不能省略字段。未知spec允许null或空串。台账可额外读回已明确标为已知小计的`known_subtotal`；提供时也会核验，未显示小计则无需制造该字段。日期空支持null、空串或纯空白；台账两日期字段必填，确认书date_fields应枚举实际需要检查的日期位置。没有日期位置可用空对象，但提取覆盖范围必须另行审查。

核验检测：左工程量漏重/改变；右材料及机械漏重、归属、名称规格单位和数量差；台账合并键漏重、两数量差和非空日期；源文件变更hash。`artifact_verified=true`仅表示这些**标准化字段和文件hash**通过，不等于原文全部工序/范围、计算公式、签字签章、审批、表格格式或打印页面通过。完整证据审查和原生逐页渲染仍需单独完成。

## 输出与限制

输出包含 `model_valid`、`artifact_verified`、`complete`、`confirmation`、`ledger`、`excluded_auxiliary`、`owner_line_allocations`、`unused_owner_line_ids`及限制说明。合法未知量可以同时满足model_valid=true和complete=false；独立读回正确保留未知时也可artifact_verified=true。这不代表结算数量已齐全。

本工具不做实际收发流水、退料/调拨负数、费用、单价、结算价、库龄、库存余额、单位自动换算、主材自动识别、公式真实性或证书批次适用性审查。新增业务模式应显式实现及测试，不能依赖忽略字段让不支持的情形假通过。
