# TasteWeaver — Qloo Agentic Hackathon 提交文案

> 复制到 Devpost（Qloo Agentic Hackathon）提交表单。**截止 2026-10-30**（部分聚合站标 10-31，按 10-30 保险）。

## 赛事
- **Qloo Agentic Hackathon**（Devpost，devpost31054），线上全球可参加。
- 奖池 **$25,000**：一等奖 $15,000 / 二等奖 $6,000 / 三等奖 $4,000。
- 评委：Jason Calacanis、Qloo CTO Mike Diolosa、Nicole Seligman、Todd Boehly、Cedric the Entertainer、Michael Abrams 等。
- **评分四项**：技术实现（Qloo 用得深不深）/ 设计（是否完整产品）/ 潜在影响 / 想法质量（Qloo 的创造性、非显而易见用法）。
- **官方铁律**："如果你的作品去掉 Qloo 也能跑，那你就做错了。" TasteWeaver 是 Qloo-central——移除 Qloo，agent 直接失效（设计如此）。

## 必交项（官方硬要求）
1. ✅ **可运行的演示应用链接**（评委能端到端使用）→ Render 部署的 Web console。
2. ✅ **公开代码仓库 URL** → github.com/Zhiyilang/tasteweaver（MIT）。
3. ✅ **项目文字描述** → 见下。
4. ✅ **外部托管 / 完全发布**（"只在本机跑或私有访问不合格"）→ Render 公网 URL。
5. ✅ **开源许可证**在仓库 About 可见 → MIT LICENSE。
- 注：**不需要演示视频**，要的是评委能真用的活链接。

## 项目描述（可直接粘贴）

**TasteWeaver — an agent that recommends what people actually love, because it knows.**

A generic LLM will confidently recommend things people don't actually like — it reasons and plans, but it's *culturally blind*. TasteWeaver wires **Qloo's Taste Graph** (250M+ entities across music, film/TV, dining, fashion, travel) into a full agent loop so every recommendation is **grounded in real cultural affinity** and **explained with evidence**.

```
request ─► PERCEIVE ─► PROFILE ─► SEARCH ─► PLAN ─► GROUND ─► EXPLAIN ─► RECEIPT
```

- **Qloo-central**: every pick is scored against the user's real taste profile; remove Qloo and the agent stops working — by design.
- **Dual brain**: an OpenAI-compatible LLM frames intent and writes justifications; a deterministic offline brain takes over instantly if the model is down. LLM output is validated as untrusted input (types coerced, unusable fields salvaged). The hosted demo runs live against the **Qloo Taste Graph** the moment `QLOO_API_KEY` is set.
- **Offline mock mode**: the entire loop runs against an in-process Qloo mock, so `python eval.py` (80 assertions) and the demo need zero setup and zero keys.
- **Currency-aware budgets**: "under 400 RMB" is normalized to USD at a disclosed rate before any comparison — a yuan budget can never authorize a dollar-sized spend.
- **Occasion-fit coherence**: candidates are ranked by Qloo affinity *plus* occasion fit, and the receipt reports how many picks carry the occasion's tags.
- **Live-API resilience**: rate limits (429) and gateway blips are retried with exponential backoff honoring `Retry-After`; a dead network degrades instead of crashing the loop.
- **Evidence-cited**: each pick cites the affinity signals and constraints it used; the receipt is a full decision trail (candidates considered, why each was dropped).

**Why this is a real use of Qloo, not a wrapper:** the GROUND step drops candidates that score poorly against the user's actual taste profile *before* they reach the plan. The difference between "technically functional" and "actually good" is exactly the step that only works because Qloo is in the loop.

## 评分对照（我们如何命中）
| 官方评分项 | TasteWeaver 的命中点 |
|---|---|
| **技术实现** | `qloo.py` 真 REST 客户端（tags / search / insights + 429 重试退避）+ 7 阶段 agent 闭环 + `eval.py` 80 断言；离线 mock 与真实 API 同码。货币归一、场合契合排序、LLM 输出校验均为工程级实现。 |
| **设计（完整产品）** | Web console + CLI（weave/demo/serve）+ 文本/HTML 回执，非技术原型；读 PORT、绑 0.0.0.0，Render 一键部署。 |
| **潜在影响** | 真实场景：为电装修客户按情绪/舒适/个人品味推荐灯饰风格；为老人按易咀嚼/低热/用药禁忌推荐餐食——文化智能正是差异化所在。 |
| **想法质量** | "模型负责框定、Qloo 负责文化根基、证据负责解释"的非显而易见切分；GROUND 在入计划前按真实品味画像剔除不匹配项。 |

## 用户动作（3 步，约 15 分钟）
1. 从 Qloo 黑客松开发者指南邮件拿 **`QLOO_API_KEY`** 和 **`QLOO_BASE_URL`**（hackathon 端点）。
2. **Render 部署**：New → Blueprint 连本仓（`render.yaml` 已含）→ Environment 里填 `QLOO_API_KEY`（`QLOO_BASE_URL` 已预设，**若与邮件端点不符请改正**）→ Deploy → 得到公网 URL。
   - 部署后务必在页面试跑一句（如 "Plan a jazz-themed Shanghai date night under 400 RMB"）确认走的是**实时 Qloo**而非 mock。
3. **Devpost 提交**：贴公网 URL + 仓库 + 上面的描述；确认仓库 About 显示 MIT。

## 提交前自查
- [ ] Render 公网 URL 可访问，且用真实 QLOO_API_KEY 跑通（非 mock）
- [ ] 仓库公开，About 显示 MIT
- [ ] 提交表单填：demo 链接 / 仓库 URL / 描述 /（可选）截图
- [ ] 不再需要演示视频；给评委一个能点的活链接
