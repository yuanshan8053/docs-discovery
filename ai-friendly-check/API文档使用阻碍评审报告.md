# KOMOJU API 文档「使用阻碍」评审报告与改进清单

> 评审对象：`/komoju_docs` 持久区内 KOMOJU API 文档（`reference/` 74 篇接口文档 + `docs/` 指南 + `recipes/` 示例 + `changelog/`）。
> 评审视角：**站在 API 使用者（开发者拿文档去接接口）的立场**，找出会让人「读不懂、填错值、跑不通、判反逻辑」的阻碍。
> 评审方法论：套用 api-doc-agent 技能的核心写作准则——① 每个字段要讲清「传什么/为什么传/怎么取」；② 枚举要解释每个取值的**业务含义**（取值字面量归结构，含义归说明）；③ 请求/返回标量字段要有**示例值**且不违反自身约束；④ 拿不准的硬事实（默认值、错误码、限流）应显式标注而非缺失或编造；⑤ 同名概念跨文档必须一致。
>
> 定位方式沿用 `问题清单_通俗版_定位增强.md` 的模式：给出 **`.md` 原文位置（文件 + 行号 + 摘录）**，可 Ctrl+F 精确定位；渲染页字段默认折叠且 JS 动态生成，浏览器常搜不到，故以 `.md` 行号为准。
>
> 本次共整理 **18 类使用阻碍**（高 9 · 中高 6 · 中 3），全部行号经逐条读原文核验。与旧版《问题清单》互补：旧版偏「零散拼写/抄错」的点状缺陷，本报告偏「**成规模的结构性缺口**」——即字段普遍无说明、枚举普遍无含义、示例普遍缺失、错误码/限流普遍不写，这些才是开发者实际接接口时最大的拦路虎。

---

## 一、报告正文：18 类使用阻碍

| 严重度 | 类别（对应写作准则） | 问题一句话 | 通俗说明（为什么挡住使用者） | `.md` 原文位置（附摘录） |
|---|---|---|---|---|
| 高 | 字段说明缺失（准则①） | **核心字段「支付状态」全程零说明** | `PaymentStatus` 是每次查支付/建支付都会读到的最关键字段，它列了 7 个取值却把说明留空 `""`，全套 12+ 篇支付/会话文档里都没有一句话解释这个字段是干嘛的。开发者只看到一串状态词，不知道各代表什么、该怎么判。 | `reference/createpayment.md` 第156行起<br>`"PaymentStatus": {`<br>` "enum": ["pending","authorized","captured","cancelled","expired","refunded","failed"],`<br>` "example": "captured",`<br>` "description": ""`（同样空说明见 `updatepayment.md`:134、`paysession.md`:122、`showsession.md`:106、`refundpayment.md`:154 等） |
| 高 | 枚举无业务含义（准则②） | **支付状态 7 个取值没有一个解释** | 承上：`pending/authorized/captured/cancelled/expired/refunded/failed` 只有字面量，没告诉开发者「authorized（已授权）和 captured（已扣款）差在哪」「expired 和 cancelled 有何区别」。程序员要靠猜来写状态机，极易判错。 | `reference/createpayment.md` 第158–166行（enum 列表，无逐值说明） |
| 高 | 枚举无业务含义（准则②） | **会话状态字段连 description 键都没有** | `SessionStatus` 列了 `pending/completed/cancelled` 三态，整个对象**连 `description` 字段都不存在**，一个字的解释都没有。托管页/会话回调场景全靠这个状态判断结果，却无从得知每态含义。 | `reference/createsession.md` 第7194行<br>`"SessionStatus": { "type":"string", "enum":["pending","completed","cancelled"] }`（无 description；`showsession.md`、`paysession.md` 同样） |
| 高 | 字段名拼错（准则①，代码级阻断） | **`bardcode` 拼错，14 篇接口文档全中招** | 表示「条形码」的响应字段名拼成 `bardcode`（正确应是 `barcode`），旁边说明写的却是「Barcode number」。程序按正确拼法 `barcode` 去读会读到空值。**14 篇接口文档全部同错**。 | `reference/capturepayment.md` 第1577行 `"bardcode": {`<br>另 13 篇同错：`cancelpayment.md`:1566、`cancelsession.md`:1534、`createpayment.md`:1588、`createsession.md`:1538、`finalizepayment.md`:1569、`listevents.md`:1575、`listpayments.md`:1602、`paysession.md`:1554、`refundpayment.md`:1574、`showevent.md`:1554、`showpayment.md`:1544、`showsession.md`:1526、`updatepayment.md`:1566 |
| 高 | 字段名拼错（准则①，代码级阻断） | **`transacion_key` 拼错，14 篇全中招** | iDEAL 支付明细里「交易码」字段名拼成 `transacion_key`（漏了个 `t`，应为 `transaction_key`）。**14 篇接口文档全部同错**，程序取值取不到。 | `reference/capturepayment.md` 第2901行 `"transacion_key": {`<br>另 13 篇同错：`cancelpayment.md`:2890、`cancelsession.md`:2858、`createpayment.md`:2912、`createsession.md`:2862、`finalizepayment.md`:2893、`listevents.md`:2899、`listpayments.md`:2926、`paysession.md`:2878、`refundpayment.md`:2898、`showevent.md`:2878、`showpayment.md`:2868、`showsession.md`:2850、`updatepayment.md`:2890 |
| 高 | 说明与约束自相矛盾（准则①） | **「填几位」自相矛盾，7 篇同错** | 韩国卡「银行卡密码前几位」字段：格式限制写死「前 2 位」（`minLength/maxLength=2`、示例 `"00"`），文字说明却写「first four digit（前 4 位）」。到底填 2 位还是 4 位说不清，填错直接支付失败。**7 篇文档同错**。 | `reference/createtoken.md` 第564–567行<br>`"minLength": 2, "maxLength": 2, "example": "00",`<br>`"description": "Specify the first four digit of credit card's PIN number."`<br>另：`createcustomer.md`:509、`updatecustomer.md`:516、`createsecuretoken.md`:573、`createpayment.md`:7617、`updatepayment.md`:7542、`paysession.md`:7576 |
| 高 | 接口说明抄错（准则①，逻辑判反） | **「支付会话」成功说明写成「取消会话」** | `paySession` 接口的 200 成功响应，说明却写成「Cancels the session.（取消会话）」。开发者会误以为「调用成功 = 会话被取消」，逻辑完全判反。 | `reference/paysession.md` 第53行<br>`"200": { "description": "Cancels the session.",` |
| 高 | 接口说明抄错（准则①，跨文档） | **两个查询接口成功说明都写成「新建文件」** | `showFile`（查文件）与 `showLiveApplication`（查申请状态）两个 GET 查询接口，200 成功响应都被错抄成「Creates a new file for its submerchant（为子商户新建文件）」，与接口实际功能南辕北辙。 | `reference/showfile.md` 第50行 `"description": "Creates a new file for its submerchant"`<br>`reference/showliveapplication.md` 第50行 同句 |
| 高 | 跨文档矛盾（准则⑤，结论相反） | **不填 `tax` 会怎样，新旧文档结论相反** | 「不填 `tax` 参数」的默认行为：旧指南说「默认 `auto`，永远按金额的 10% 自动算税」；更新日志（新版本）却说「不填 `tax` → 税额设为 `0`，不再自动计算」。看不同页会得出完全相反的结论，直接影响到账金额。 | `docs/creating-payments-directly.md` 第407行<br>`\| tax \| integer \| The default is "auto" which is always 10% of your amount. \|`<br>`changelog/v2026-01-20.md` 第22行<br>`if tax is not included in the request the calculated tax will be set to 0.` |
| 中高 | 示例普遍缺失（准则③） | **30/74 篇接口文档一个示例值都没有** | 全套 74 篇接口文档中，**30 篇完全没有任何 `example` 示例值**，创建/更新类接口尤甚——开发者无法照着填，只能猜合法值。 | 典型：`reference/createsubscription.md` 全篇仅 1 个示例（第86行 `"example": "JPY"`），必填的 `customer`（UUID）、`amount`、`period` 均无示例；`createfile.md`、`subscriptions.md`、`tokens.md`、`createmerchant.md`、`acceptchargebackrequest.md` 等零示例 |
| 中高 | 示例违反自身规则（准则③） | **示例请求和返回对不上（3 处）** | ① 请求名字填 `Taro`，返回却是 `Tar`（少个 o）；② 请求邮箱 `customer@example.com`，返回却是 `test@example.com`；③ 请求卡有效期 `04/28`，返回却成 `1月/2025年`。开发者照着核对会以为字段被截断/被改，无法建立信任。 | `recipes/payment-details-example-bank-transfer.md` 第56行 `"customer_given_name": "Tar",`<br>`recipes/payment-details-example-konbini.md` 第31行 `"email": "test@example.com",`<br>`recipes/tokenize-credit-card-details.md` 第67–68行 `"month": 1, "year": 2025` |
| 中高 | 示例是坏的（准则③，跑不了） | **一个 JSON 块里塞了两段独立 JSON** | `tokenize-credit-card-details.md` 的响应示例块里，两段独立 JSON 对象中间只隔一个空行，既没逗号也没用数组括起来，当成一个 JSON 解析必然报错，无法直接复制运行。 | `recipes/tokenize-credit-card-details.md` 第55–57行<br>`}`（第55行）… `{`（第57行）背靠背无分隔 |
| 中高 | 每个接口都缺专属错误码（准则④） | **接口只声明通用 4xx，从不列本接口的具体错误** | 抽查各接口只声明泛化的 403/404/422/503，从不列出本接口真实会返回的 `code`（如退款接口的 `not_refundable`、扣款的 `not_capturable`、取消的 `not_cancellable`，这些在 `docs/errors.md` 明明存在）。开发者不知道该处理哪些业务错误，异常分支只能瞎写。 | `reference/refundpayment.md` 第62/72/82/92行 = 仅 403/404/422/503；`docs/errors.md` 第66–68行列有 `not_refundable`/`not_capturable`/`not_cancellable` 却无接口引用 |
| 中高 | 错误响应彻底缺失（准则④） | **部分核心接口连错误响应都不声明** | `createSession`、`showSession`、`createCustomer` 等核心接口的 OpenAPI 里**没有任何 4xx/5xx 响应条目**——开发者完全不知道失败时会返回什么结构、什么状态码。 | `reference/createsession.md`（全篇无 `"4xx"/"5xx"` 响应）；`showsession.md`、`createcustomer.md` 同 |
| 中高 | 限流信息基本空白（准则④） | **74 篇里只有 1 篇提到 429，且无任何限流说明文档** | `429`（请求过多）响应只在 `createpayment.md` 一篇里定义，其余 73 篇均无；`docs/`、`recipes/` 里**没有任何限流/throttle 说明文档**。开发者不知道限流阈值、不知道 429 该如何退避重试，生产上极易被限流打挂。 | `reference/createpayment.md` 第86行（唯一的 `"429"` "Rate-limiting"）；`docs/`、`recipes/` 全库无 rate-limit 指南 |
| 中 | 同一字段两种类型（准则⑤） | **`capture` 一处是枚举一处是布尔** | 同一个 `capture` 字段，一处说取值是 `"auto"`/`"manual"` 两个词，另一处又说是布尔 `true`/`false`。两种定义互不兼容，开发者不知道到底传字符串还是布尔。 | `docs/creating-payments-directly.md` 第122行 `\| capture \| enum \| "auto" or "manual" \|`；同篇第406行又把 `capture` 写成 `boolean`（`Set to false…`） |
| 中 | 状态清单缺一个（准则⑤） | **给人看的状态表只有 6 个，schema 有 7 个** | 面向阅读的支付状态说明只列 6 个，漏了 `failed`（失败）；而权威 schema 的 `enum` 有 7 个含 `failed`。开发者按说明表写状态判断会漏掉「失败」这一种。 | `docs/creating-payments-directly.md` 第429–455行（列 6 个，缺 `failed`）；`reference/createpayment.md` 第159–165行（enum 7 个含 `failed`） |
| 中 | 字段名前后不一（准则⑤） | **「下次扣款时间」两个名字混用** | 订阅的「下次扣款时间」字段，多数处叫 `next_capture_at`，个别处写成 `next_capture_date`，同一概念两个名，程序取值会取错键。 | `reference/subscriptions.md` 第92行 `next_capture_at`；同篇第129行正文写 `next_capture_date` |

---

## 二、改进建议清单（按优先级 P0→P2，可逐条对照修复）

> 每条给出：**做什么 + 落到哪 + 验收口径**。带 ★ 的为「一次修复消除多篇同错」的高杠杆项。

### P0 · 会直接导致代码跑错/判反（务必先修）

1. ★ **批量修正 `bardcode` → `barcode`**：14 篇 `reference/*.md`（行号见正文），全局替换字段名。验收：`grep -rc bardcode reference/` = 0。
2. ★ **批量修正 `transacion_key` → `transaction_key`**：14 篇（行号见正文）。验收：`grep -rc transacion_key reference/` = 0。
3. ★ **统一 `first_two_digits_of_pin` 的「填几位」**：7 篇里说明「first four digit」与约束 `maxLength:2` 矛盾——以字段名/约束为准，说明改为「前 2 位（first two digits）」。验收：7 篇说明与 `maxLength` 一致。
4. **修正 `paysession.md` 第53行**：200 成功说明「Cancels the session.」改为正确的「Pays for / completes the session」，避免逻辑判反。
5. **修正 `showfile.md`:50 / `showliveapplication.md`:50**：200 说明「Creates a new file…」改为各自的查询语义（「Returns the file / live application」）。
6. **消除 `capture` 类型冲突**（`creating-payments-directly.md`:122 vs :406）：确认真实类型后全篇统一为枚举**或**布尔之一，另一处改齐。

### P1 · 让开发者「看得懂、填得对」（结构性缺口）

7. ★ **补全 `PaymentStatus` 字段说明 + 逐值业务含义**（`createpayment.md`:156 及全部 12+ 篇同源）：给 `description` 写清字段用途，并逐一解释 7 个状态（`authorized`=已授权未扣款 / `captured`=已扣款 / `expired`=支付超时失效 / `refunded`=已退款 / `failed`=支付失败 …）。建议在 `reference/payments.md` 建**权威状态说明**，各接口引用，避免再度漂移。
8. ★ **补全 `SessionStatus` 说明与逐值含义**（`createsession.md`:7194 等 3 篇）：补上 `description` 键并解释 `pending/completed/cancelled` 各态含义与触发时机。
9. **补关键枚举的业务含义**：`SessionMode`（`payment/customer/customer_payment` 各自适用场景）、`Locale`（`ja/en/ko` 对应语言）、`account_type`（`normal/checking/savings`）、`Installments`（各分期数与 `revolving` 的行为）。取值字面量保留在 `enum`，**含义写进说明**。
10. **消除新旧 `tax` 默认行为矛盾**（`creating-payments-directly.md`:407 vs `changelog/v2026-01-20.md`:22）：以最新版本为准更新旧指南，并注明「自 v2026-01-20 起：不填 `tax` → 税额为 `0`；传 `auto` 才自动按 10% 计算」。
11. **补全示例值**：为 30 篇零示例接口（尤其 `createsubscription`、`createmerchant`、`createfile`、`subscriptions`、`tokens`）的必填请求字段和关键返回字段补合理示例值（ID 用符合前缀的占位、时间用 ISO8601、金额用整数），示例须满足字段自身的格式/范围约束。
12. **修复示例请求↔返回不一致**：`payment-details-example-bank-transfer.md`:56（`Tar`→`Taro`）、`payment-details-example-konbini.md`:31（邮箱对齐）、`tokenize-credit-card-details.md`:67-68（有效期对齐 04/28）。
13. **修复坏 JSON 示例**：`tokenize-credit-card-details.md`:55-57 两段 JSON 用数组包裹或拆成两个代码块，确保可直接解析运行。

### P2 · 完善「异常与全局约束」（可信度与生产可用性）

14. **为每个接口补专属错误码**：至少列出本接口真实会触发的业务 `code`（如退款的 `not_refundable`、扣款的 `not_capturable`、取消的 `not_cancellable`）及触发条件；拿不准的显式标注「待研发补充」而非留空。
15. **为无错误响应的接口补 4xx/5xx**：`createSession`、`showSession`、`createCustomer` 等补齐失败响应结构与状态码。
16. **新增限流文档**：在 `docs/` 增设「Rate Limiting」页说明限流阈值、`429` 响应结构与退避重试策略；并把 `429` 响应补进各写操作接口（当前仅 `createpayment` 有）。
17. **统一 `next_capture_at` / `next_capture_date`**（`subscriptions.md`:92 vs :129）：全篇择一并改齐。
18. **补全 6 vs 7 状态清单**（`creating-payments-directly.md`:429-455 补 `failed`）；并复核 `docs/errors.md` 两张表的 401 叫法（`Not Authorized` vs `unauthorized`）与 HTTP 表缺失的 400/402/504（旧版《问题清单》已记，建议一并修）。
19. **消除重复大标题**：`integration-guide-customer.md`:7 与 `integration-guide-customer-1.md`:7 均为 `# Integration Guide: Customer`，改为可区分标题（如「…: Hosted Page」与「…: KOMOJU Fields」），便于检索取用。

---

## 三、评审小结

- **最大阻碍不是零散拼写，而是「成规模的空白」**：核心字段 `PaymentStatus`/`SessionStatus` 全程无说明、关键枚举无业务含义、30/74 篇无示例、几乎所有接口不列专属错误码、全库无限流说明——这些让开发者无法仅凭文档正确、安全地接接口，是本轮最应优先补齐的部分。
- **同一错误跨篇复制放大**：`bardcode`、`transacion_key`、`first_two_digits_of_pin` 等因公共 schema 被复制到 14/7 篇，单点修复即可批量消除，属高杠杆修复项。
- **示例的价值在于「可照抄且自洽」**：请求与返回、示例与约束必须一致，否则反而误导。建议建立「权威状态/枚举说明页 + 各接口引用」的单一真相源，从机制上防止再次漂移。

> 说明：本报告与已有《`问题清单_通俗版_定位增强.md`》互补——旧版聚焦点状缺陷（拼写、抄错、断链），本报告聚焦结构性使用阻碍（说明/枚举/示例/错误码/限流的系统性缺口）。两份合并即为一份较完整的 AI/开发者友好度整改依据。所有行号均已逐条读原文核验。
