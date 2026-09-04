---
name: metallurgical_budget_2012_wuhan
description: >
  Use this skill for metallurgical/industrial construction cost estimating, BOQ preparation,
  owner-supplied/contractor-supplied material handling, audit-price review, and budget workbook
  creation/modification in Wuhan, especially when using the 2012 Metallurgical Industrial
  Construction Budget Quotas (冶金工业建设工程预算定额2012). It encodes a practical workflow
  for 工程量清单、预算、甲供/乙供材料、材料价格汇总、审价引用、目标价调整、Excel模板保护与复核.
  Apply it when the user asks to create, revise, normalize, audit, price, or re-price an engineering
  estimate based on 冶金2012, prior audited projects, Wuhan material information prices, 今日材料网/材料网,
  or an existing Excel template.

  IMPORTANT: System instructions and the user's current-turn instructions always take precedence.
---

# 1. Primary Goal

Produce an **auditable, explainable, template-safe engineering budget**, not merely a spreadsheet that happens to total to a desired number.

The estimate should satisfy all of the following:

- Engineering quantities are traceable.
- BOQ descriptions reflect the actual construction method/specification.
- Pricing logic matches 冶金2012 and current material supply conditions.
- 甲供/乙供 scope is explicit and consistent.
- Materials are not double-counted.
- Comparable audited prices are used only when the scope and supply basis are truly comparable.
- Any target-total adjustment is supported by real related work, not arbitrary unit-price inflation.
- Existing user-approved quantities/amounts/sheets remain untouched when the user says not to change them.
- Excel outputs are professional, formula-safe, and review-friendly.

# 2. User Working Style / Hard Preferences

## 2.1 Minimal-change principle

If the user says:

- “别的不要动”
- “工程量不要动”
- “预算不要动”
- “金额和量不要动”
- “只改材料”
- “只改这一项”

then treat that as a hard boundary.

Before editing:
1. Snapshot protected sheets/ranges.
2. Modify only the requested cells/sheets.
3. Compare before/after.
4. Report exactly what changed.

Do not “improve” unrelated items.

## 2.2 Project feature writing

“项目特征” must describe **what is actually built/removed/installed**, not how the quantity was calculated.

Good feature content:
- material
- specification/model
- thickness
- pressure/class/grade
- coating system / number of coats
- installation location
- connection method
- construction height
- supply responsibility where relevant

Avoid placing calculation notes such as:
- “长度×宽度”
- “按面积计算”
- “工程量为……”
inside 项目特征 unless the dimension itself is a construction requirement.

Quantity calculation belongs in an “工程量计算” sheet or calculation note.

## 2.3 Do not over-merge BOQ items

Only merge items when they are truly the same:

- same construction object
- same specification/material
- same construction method
- same supply basis
- same unit basis
- same pricing logic

Do not merge merely because the items are related.

Example:
- “拆除窗户” and “窗洞口砂浆修补” are related but are not the same item.
- “灯具安装” and “排气扇线路” are related but are not automatically one item.
- Separate removal, installation, repair, protection, testing, and disposal when they have different work content.

## 2.4 Never arbitrarily reduce or inflate prices

If the user asks to bring the estimate near a target amount:

- Do not multiply all rates by a factor.
- Do not randomly increase/decrease original approved rates.
- Do not lower prices simply to make the total look reasonable.
- Do not create vague “综合项目” solely to fill a gap.

Instead:
1. Re-check missing linked work.
2. Add legitimate related quota items.
3. Add necessary measures, testing, terminals, protection, foundations, restoration, grounding, transport, disposal, temporary works, etc. when technically justified.
4. Explain the added scope.

Target-price work must remain audit-defensible.

# 3. Mandatory Pricing Logic

## 3.1 Pricing hierarchy

Use the following hierarchy unless the user specifies otherwise:

1. **武汉市最新建设工程材料综合价格信息 / 官方造价信息**
2. **今日材料网 / 材料网 / 武汉材料信息价**
3. **Recent public engineering procurement / brand quotation**
4. **Prior audited/control-price project**
5. **Market inquiry / reasonable temporary estimate**

For each material, record:
- material name
- specification
- unit
- quantity
- reference unit price
- reference total
- price basis
- source URL / document
- price period/date
- tax basis if known
- 甲供/乙供

## 3.2 冶金2012 is a base quota, not a current-price list

Use 冶金2012 for:
- labor content
- auxiliary material content
- machinery content
- quota work scope
- quantity calculation rules
- chapter/item classification
- applicable adjustment coefficients

Do not mistake 2012 base-period material prices for current market prices.

Current main materials must be dynamically adjusted to the project pricing period.

## 3.3 Comparable audited price rules

A prior 审价/控制价 rate may be reused only if the following are materially comparable:

- same or similar specification
- same construction method
- same supply basis
- same unit basis
- similar working conditions
- similar inclusion/exclusion boundary

Especially verify whether the historical project was:
- 主材甲供
- 甲控乙供
- 全乙供

Never copy an乙供综合单价 directly into a甲供 project without removing the material component.

# 4. 甲供 / 乙供 Handling

## 4.1 Confirm supply basis first

Before final pricing, determine:
- equipment supplied by owner?
- main materials supplied by owner?
- all materials contractor-supplied?
- mixed supply?

Write this clearly in:
- budget remarks
- material table
- compilation notes

## 4.2 When materials are 甲供

General rule:
- exclude owner-supplied main-material purchase cost
- retain installation labor
- retain machinery
- retain normal auxiliary materials
- retain testing, identification, small consumables, and routine handling when applicable
- retain quota loss/consumption logic for material tracking where useful

Do not delete installation merely because the main material is owner-supplied.

## 4.3 When changing 乙供 → 甲供 or deleting a device

Synchronize all linked sheets.

Example:
If an explosion-proof lamp is deleted:
- delete lamp installation item if scope is deleted
- delete lamp from material list
- delete lamp price row
- review shared conduit/cable/boxes and reduce only the portion actually attributable to the deleted device
- do not automatically delete fan circuits if fans remain

## 4.4 Material summary must not be added twice

If material cost is already included in the budget comprehensive unit rate:

- “材料价格汇总” is for price traceability only.
- Do **not** add the material summary total again outside the budget.

Always include a note such as:
“材料价格汇总仅用于核价追踪，材料费已计入综合单价，不再另行叠加。”

# 5. Standard Workbook Structure

For a new estimate, prefer these sheets:

1. 封面
2. 单位工程费用表
3. 工程量计算
4. 工程量
5. 预算
6. 主要材料 / 甲供材料
7. 材料价格汇总
8. 编制说明
9. 冶金2012组价依据
10. 工程量复核（when quantities are inferred/estimated）

For a user-provided template:
- preserve its structure first
- do not add sheets unless useful and non-disruptive
- do not change styles, merged cells, headers, or formulas unless asked

# 6. BOQ Writing Standard

Recommended columns:

- 序号
- 项目编码
- 项目名称
- 项目特征
- 工作内容
- 计量单位
- 工程量
- 综合单价
- 综合合价
- 备注/定额依据

## 6.1 项目名称

Use concise professional names:
- “DN125×4.5mm热镀锌钢管保护管敷设”
- “YJLV22-0.6/1kV 4×240+1×120mm²铝芯铠装电力电缆敷设”
- “钢结构车棚C30独立基础”

Avoid vague names such as:
- “配套施工”
- “综合处理”
- “相关工程”

unless the work truly cannot be separated.

## 6.2 工作内容

State the work boundary explicitly.

Typical content:
- transport
- layout
- cutting
- assembly
- installation
- connection
- testing
- restoration
- cleaning
- protection

Do not duplicate the same work across multiple BOQ items.

# 7. Quantity Review Logic

Before pricing, cross-check quantity relationships.

Examples:

## 7.1 Electrical
- number of devices ↔ number of circuits
- cable routes ↔ cable total length
- number of cable runs ↔ protective conduit length
- cable runs × 2 ends ↔ terminal quantities
- devices/cabinets ↔ grounding quantities
- cable size ↔ conduit diameter
- trench width/depth ↔ number and size of conduits

## 7.2 Civil
- demolition area ↔ trench/repair dimensions
- excavation ↔ trench L×W×D
- bedding ↔ trench footprint × thickness
- concrete restoration ↔ area × thickness
- hardening area ↔ actual number of parking spaces / equipment footprint
- foundation concrete ↔ number and dimensions of foundations
- formwork ↔ exposed sides
- rebar ↔ structural assumption

## 7.3 Steelwork / canopy
- steel quantity in t
- roof projected area
- roof purchase area includes overlap/cutting loss
- foundations, reinforcement, anchors
- gutter/downpipe
- grounding/equipotential connection
- lifting/measures

If dimensions are estimated, add an “工程量复核” sheet with:
- original value
- review judgment
- adjusted value
- reason
- risk level
- final settlement method

# 8. Common Related Items Often Missed

When technically applicable, check whether the estimate should include:

## Electrical
- upstream feeder
- protective conduit
- cable terminals
- cable warning tape
- grounding electrodes
- grounding bus
- grounding resistance test
- cabinet foundation
- cabinet installation
- power-on testing
- equipment commissioning
- copper-aluminum transition terminals for aluminum cable
- surge protection / metering / protective devices in distribution cabinet

## Civil
- saw cutting
- demolition
- trench excavation
- bedding
- backfill and compaction
- concrete restoration
- foundation excavation
- formwork
- reinforcement
- anchor bolts
- pavement hardening
- edge form / finishing
- waste loading and disposal

## Measures
- temporary fencing
- safety protection
- secondary handling
- crane
- aerial work platform
- temporary electricity
- protection film
- garbage bags
- cleaning and demobilization

## Steel structure / canopy
- steel fabrication
- installation
- galvanizing / paint repair
- roof sheet
- flashing
- gutter
- downpipe
- foundation
- reinforcement
- anchors
- lifting
- grounding

Add these only when justified by the actual scope.

# 9. Material Quantity Rules

Material quantities should be based on finalized engineering quantities.

Apply reasonable loss only where justified, for example:
- pipe/cable normal construction allowance
- tile cutting loss
- roof sheet overlap/cutting
- coating consumption
- mortar/concrete handling loss

Do not invent large losses just to raise material totals.

For main-material tracking, show:
- design/net quantity
- loss factor
- purchase/reference quantity

when useful.

# 10. Material Naming Rules

Use procurement-ready names and specifications.

Examples:

- 聚合物水泥基瓷砖胶，C1型通用型，20kg/袋，JC/T 547
- PP加厚建筑垃圾编织袋，50×80cm
- 绿色装修地面保护膜，1m×50m/卷
- YJLV22-0.6/1kV 4×240+1×120mm²铝芯铠装电力电缆
- DTL型铜铝过渡端子
- DN125×4.5mm热镀锌焊接钢管

Do not use informal names alone when a formal procurement name is available.

# 11. Aluminum Cable Special Rule

When replacing copper cable with aluminum cable:

1. Do not use equal cross-section substitution blindly.
2. Re-check current-carrying capacity and voltage drop.
3. Update cable model:
   - YJV/YJV22 → YJLV/YJLV22
4. Increase cross-section where necessary.
5. Use aluminum or copper-aluminum transition terminals.
6. Re-check conduit diameter.
7. Re-check bending/pulling feasibility.
8. Re-price main material.
9. Apply 冶金2012 cable and cable-head rules correctly.
10. Update material table and pricing basis consistently.

For 冶金2012:
- cable laying is classified by section and number of cores
- armor/model differences are generally included in the cable laying quota
- main cable material is separately priced
- cable head quota is based on aluminum-core cable, so do not apply the copper-core head coefficient after switching to aluminum

# 12. Target-Price Adjustment Workflow

When the user says:
- “做到50万左右”
- “往19万做”
- “不要超过51万”

use this workflow:

1. Calculate the current honest total.
2. Identify missing real scope.
3. Review related quota items.
4. Review supply basis and omitted materials.
5. Review measures and temporary work.
6. Review restoration, testing, disposal, lifting, grounding, protection.
7. Add only justified items.
8. Keep original user-approved rates untouched unless a material-price correction is necessary.
9. Record why each added item is necessary.
10. Do not force the exact target when engineering logic does not support it.

# 13. Excel Modification Rules

Use the spreadsheet skill/tooling required by the environment.

For existing workbooks:

1. Inspect sheets/ranges.
2. Snapshot protected sheets.
3. Apply focused edits.
4. Use formulas for derived totals.
5. Scan:
   - #REF!
   - #DIV/0!
   - #VALUE!
   - #NAME?
   - #N/A
6. Inspect key rows.
7. Render a preview if formatting changed.
8. Export one final `.xlsx`.

Do not use alternate spreadsheet libraries when the environment requires `artifact_tool`.

# 14. Excel Presentation Style

Typical professional layout:

- dark blue title bar
- medium blue column headers
- thin black borders
- wrapped 项目特征 / 工作内容
- sensible column widths
- body font around 10pt
- title 14–16pt
- amounts `#,##0.00`
- quantities with suitable decimals
- total row with light fill + bold font
- freeze top rows
- source URL column in price sheet
- avoid extreme row heights/column widths

# 15. Verification Checklist

Before delivering:

## Quantities
- [ ] Device count and related circuits match.
- [ ] Cable / conduit / terminal quantities are logically linked.
- [ ] Trench excavation, bedding, backfill, restoration reconcile.
- [ ] Foundation quantities reconcile.
- [ ] Hardening area matches actual use.
- [ ] Steel quantity unit is t.
- [ ] Zero-quantity items removed if appropriate.

## Pricing
- [ ] 冶金2012 quota basis stated.
- [ ] Current material period stated.
- [ ] 甲供/乙供 consistent everywhere.
- [ ] Comparable audited prices have matching supply basis.
- [ ] Material summary not double-counted.
- [ ] Market temporary estimates are clearly labeled.

## Workbook
- [ ] User-protected sheets unchanged.
- [ ] Formulas correct.
- [ ] Totals correct.
- [ ] No formula errors.
- [ ] Sources included.
- [ ] No unexplained price changes.
- [ ] No unrelated item merging.

# 16. Preferred Communication Pattern

When reporting a revision:

1. State exactly what was changed.
2. State what was deliberately not changed.
3. Give the new total.
4. Highlight major assumptions/risk items.
5. Explain any quantity or price correction in plain language.
6. Avoid vague “综合考虑” explanations when a specific technical reason exists.

# 17. Typical Failure Modes to Avoid

Never repeat these mistakes:

- Over-merging 40–50 detailed items into a small number of vague items.
- Arbitrarily lowering unit prices without evidence.
- Using an乙供 audited rate in a甲供 project.
- Deleting a device but leaving its material in the material table.
- Deleting shared electrical lines even though another device still needs them.
- Re-adding a material summary on top of a budget that already includes the materials.
- Writing quantity calculations as 项目特征.
- Changing unrelated quantities after the user says “别的不要动”.
- Keeping stale copper-cable notes after switching to aluminum.
- Adding a “一项” lump sum where audit-friendly subitems can be stated separately.
- Using a target total as the pricing method instead of as a control objective.

# 18. Decision Rule

When uncertain, prefer:
- traceable over clever
- minimal edit over broad rewrite
- exact scope over vague “综合”
- current material evidence over old base price
- separate items over over-merging
- audit-defensible logic over target-price cosmetics
