# TasteWeaver（中文说明）

**一个扎根文化品味的 AI 智能体：从 Qloo 品味图谱中编织出连贯、合品味的计划。**

为 [Qloo Agentic Hackathon](https://www.qloo.com/)（主题"Agents, but with taste."）而建。

LLM 会推理、会规划，但它是"文化盲"：让它推荐点什么，它只能猜。TasteWeaver 补上这一环——给它几个品味锚点加一个场合、地区和约束条件，它去查询 **Qloo 品味图谱**（覆盖音乐/电影/餐饮/时尚/旅游等 2.5 亿+ 实体），组装出一份跨领域的连贯计划，且每一项推荐都**锚定真实文化亲和度**并**附带证据解释**。

> 核心论点：通用 LLM 给出"听起来像那么回事"的推荐；TasteWeaver 给出*真的好*的推荐——因为它知道人们真正喜欢什么，并且把推理过程摆出来。

- **以 Qloo 为核心**——每一项推荐都对照用户真实品味档案打分；抽掉 Qloo，agent 直接失效（刻意设计）。
- **货币感知预算**——"400 元以内"先按披露汇率归一成美元再比较，人民币预算永远不可能悄悄授权一笔美元级花费。
- **场合契合**——推荐按品味亲和度*加*场合契合度排序：约会夜排名里，烛光爵士酒吧高于同样高亲和度的热闹火锅。
- **零依赖**——纯 Python 标准库，`pip install` 什么都不需要。
- **双大脑**——OpenAI 兼容 LLM 大脑（意图解析/解释生成）或确定性离线大脑；LLM 输出按不可信输入校验，模型挂了自动降级。
- **真实 API 韧性**——Qloo 客户端对 429 限流与网关抖动做指数退避重试，遵守 `Retry-After`；断网时降级而不是让闭环崩溃。
- **证据引用**——每项推荐都引用它实际使用的亲和信号与约束。
- **离线 mock 模式**——完整 agent 闭环跑在进程内 Qloo mock 上，任何人零setup 可跑；`--live` 让同一份代码指向真实 Qloo API。

## Agent 闭环

```
request ──► PERCEIVE ──► PROFILE ──► SEARCH ──► PLAN ──► GROUND ──► EXPLAIN ──► RECEIPT
             (意图/锚点)  (品味档案)   (Qloo 图谱  (跨领域    (亲和度     (plain EN   (计划+
                                     候选查询)    连贯计划)   证据打分)    解释)       来源)
```

1. **PERCEIVE**——解析请求：场合、地区、预算、约束（饮食/时间/心情）与品味锚点（"她喜欢爵士"、"他迷科幻"）。
2. **PROFILE**——把锚点转成跨 Qloo 领域的品味档案。
3. **SEARCH**——在各相关领域（餐饮、音乐、电影……）查询 Qloo 品味图谱，带证据排序。
4. **PLAN**——组装连贯的多领域计划（如主题之夜），尊重预算与约束；候选按亲和度**加场合契合度**排序。
5. **GROUND**——用 Qloo 亲和度给每一项对照用户品味档案打分，文化不契合的直接淘汰。
6. **EXPLAIN**——为每一项写通俗英文理由，引用亲和信号+约束。
7. **RECEIPT**——计划报告（文本+HTML），带完整决策轨迹与 Qloo 实体来源。

## 预算与货币

请求可用任一种货币表述预算（"under 400 RMB"、"under $50"、"400元以内"）。规划器先把所有金额归一到美元再比较（实体自带币种），回执里披露得明明白白：

```
Occasion: date-night | Locale: shanghai | Budget : ¥400 (≈$55.56 USD @ 7.2)
Plan (spent ¥380.02 of ¥400):
  - [dining] Blue Note Cellar  (affinity 0.40; fit 0.20; matched jazz,live-music; rating 4.6 ~¥380)
Coherence: 1/2 picks carry 'date-night' occasion tags.
```

`¥400` 预算授权的是约 $55.56——永远不是 $400。汇率是文档化的常量（`planning.py` 里的 `CNY_PER_USD`），不是隐藏魔术数字。

## 快速开始

```bash
git clone https://github.com/Zhiyilang/tasteweaver.git
cd tasteweaver

# 1. 跑测试套件（离线，无需任何 key）
python eval.py

# 2. 跑脚本化 demo 场景（mock Qloo，离线）
python -m tasteweaver demo

# 3. 亲自问 agent 一个问题（mock 模式）
python -m tasteweaver weave "Plan a jazz-themed date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food"

# 4. 启动 web 控制台（mock 模式）
python -m tasteweaver serve --port 8790
# 打开 http://127.0.0.1:8790
```

> 部署到 Render 等平台时**不要传 `--port`**：服务自动读 `$PORT` 环境变量（见 `render.yaml`），传死端口会烧掉平台分配的随机端口。

## 接真实 Qloo API

默认 mock 模式，任何人可离线跑通全部功能。要指向真实 Qloo 品味图谱：

1. 从 Qloo 黑客松开发者指南领免费 key：<https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide>
2. 导出该指南给的凭证与 API 基址：

```bash
export QLOO_API_KEY="your-hackathon-key"
export QLOO_BASE_URL="https://<qloo-hackathon-endpoint>"
```

3. 加 `--live` 运行：

```bash
python -m tasteweaver weave "a jazz-themed Shanghai date night under 400 RMB" --live
python -m tasteweaver serve --port 8790 --live
```

## 加 LLM 大脑

任何 OpenAI 兼容聊天端点都行：

```bash
export TASTEWEAVER_LLM_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
export TASTEWEAVER_LLM_API_KEY="your-key"
export TASTEWEAVER_LLM_MODEL="mimo-v2-flash"
```

LLM 负责意图解析与推荐理由撰写。端点不可达或返回不可用 JSON 时，TasteWeaver 自动回退离线大脑。

## 自验证

```bash
python eval.py        # 80 条断言，离线，无需 key
```

覆盖：意图解析（双币种、双符号风格）、品味图谱接口、货币归一与预算强制执行（¥0 预算被当作真实约束而非"无预算"）、场合契合排序、LLM 大脑的不可信输出校验与离线回退、真实客户端的重试/退避/缓存行为（经注入的假 transport）、回执结构与 HTML 转义、web 控制台（`/healthz`、表单、POST）、CLI，以及 `$PORT` 环境变量传导（serve 启动回归断言）。

## 项目结构

```
tasteweaver/
├── tasteweaver/
│   ├── __init__.py
│   ├── __main__.py     # python -m tasteweaver
│   ├── qloo.py         # Qloo 品味图谱 REST 客户端（tags / search / insights，退避重试）
│   ├── mock_qloo.py    # 进程内 Qloo mock（离线 demo + 测试）
│   ├── profile.py      # 品味锚点 -> 跨领域品味档案
│   ├── planning.py     # 跨领域连贯计划组装（货币、预算、场合契合）
│   ├── reasoning.py    # LLM 大脑 + 离线大脑（同一接口，LLM 输出经校验）
│   ├── agent.py        # agent 闭环
│   ├── receipts.py     # 文本 + HTML 计划报告（带决策轨迹）
│   ├── cli.py          # weave / demo / serve 命令
│   └── web.py          # 标准库 web 控制台
├── eval.py             # 断言套件，离线可跑
├── examples/
│   └── requests.txt    # 示例自然语言请求
├── requirements.txt    # （空——仅用标准库）
├── .env.example
├── render.yaml         # Render 部署（读 $PORT，healthCheckPath /healthz）
├── LICENSE             # MIT
└── README.md
```

## 为什么"会推荐的 agent"需要文化地基

通用 LLM 会自信地推荐人们其实并不喜欢的东西。TasteWeaver 假设相反：**模型负责框定请求，Qloo 负责锚定品味，证据负责解释每一项选择。** 候选对照真实品味档案打分，受场合/地区/预算约束，每一项选择都引用为其背书的亲和信号。

## 许可

MIT——见 [LICENSE](LICENSE)。
