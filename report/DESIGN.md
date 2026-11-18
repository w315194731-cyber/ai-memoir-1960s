# DESIGN.md — 拾光·AI人生回忆录 参赛项目报告

## 全局视觉约定

### ① 画布与安全区
- 画布 1280×720，padding 上下 60 / 左右 60，内容区 1160×600（y 60–660）
- 页眉 y=60–120；标题区 y=120–200；正文区 y=200–640；页脚 y=670
- 页脚字号 14px，仅内容页出现，全篇固定左下

### ② 配色方案（暖调人文 · Warm）
- 主色 accent：`#684F48`（暖褐）
- 辅色 surface：`#EAE4DB`；line：`#E2DEDA`
- 强调色：主色同色，关键数字/结论用 accent；点缀 深薄荷 `#45726A`
- 底色 bg：`#FEFCF8`（暖白纸色）
- 正文色：ink `#33241F` / secondary `#503C36` / body `#473A35` / muted `#8E8581`
- 深色块 deep_bg：`#241C19`，深底文字 `#FEFCF8`
- 系列色：`#684F48` `#8FA8A5` `#C9A96E` `#A8C4C1` `#9A7B6E` `#7E97A0`
- 色彩节奏：Hero 页 accent 15–20%；内容页 accent ≤5%、辅色 ≤20%

### ③ 字体系统
- 中文标题：霞鹜文楷（LXGW WenKai）；正文：思源黑体（Source Han Sans）
- 西文/数字：随所在中文文字
- 字号阶梯：封面主标 76px / 章节大字 60px / 巨型数据 88px / 页面主标 36px / 卡片小标 24px / 正文 18px / 标签 16px / 脚注 14px

### ④ 视觉母题
- 内容页顶部英文小眉标（kicker）+ 一条贯穿内容区的 1px 分隔线（底色向 accent 混 35%）
- 页面编号以小字置于眉标行右端

### ⑤ 配图清单
| 文件 | 用途 | 生成方式 | 真实内容 | 使用页 |
|---|---|---|---|---|
| cover.png | 封面主角 | ImageGen | 午后阳光的怀旧空教室 | P1 |
| ch1-childhood.jpg | 主角/证据 | Lux3D文生图 | 红双喜搪瓷缸 | P7,P9 |
| ch3-gaokao.jpg | 证据 | Lux3D文生图 | 老式煤油灯 | P7 |
| ch4-work.jpg | 证据 | Lux3D文生图 | 永久二八自行车 | P9 |
| ch5-downsizing.jpg | 证据 | Lux3D文生图 | 老式BP机 | P9 |
| ch8-today.jpg | 主角 | Lux3D文生图 | 老搪瓷脸盆 | P9 |
| 其余 ch*.jpg | 图鉴 | Lux3D文生图 | 石板/黑白电视/智能手机 | P9 |
| （结构化图） | 链路/矩阵 | SVG | 技术链路、评分矩阵 | P4,P10 |

全篇图片统一为温暖写实的摄影/产品图风格，不混用插画。

---

## 逐页设计

### P1 封面
- title: 拾光 · AI人生回忆录
- type: cover / role: hero / rhythm: peak
- layout: 满版图+渐变蒙层
- visual: cover.png 全出血，底部深色蒙层，白字主标
- density: 字数约 40 / 图片 1 / 留白 30%
- anti_pattern: 禁止居中大标题+三等分卡片；禁止文字投影
- description: 主标题「拾光」+副标「用AI，把普通人的一生变成可走进的回忆录」，底部赛事名与团队落款。

### P2 目录
- title: 目录
- type: catalog / role: supporting / rhythm: transition
- layout: 经典纵排
- visual: 无图，编号+章节名+页码三列
- density: 字数约 60 / 图片 0 / 留白 45%
- anti_pattern: 禁止卡片容器；禁止每章简述
- description: 五章——项目概览、创意与痛点、技术实现、成果展示、价值与展望。

### P3 项目概览
- title: 一个人，一部缩微的中国当代史
- type: content / role: supporting / rhythm: valley
- layout: 左标题色块+右内容
- visual: 右侧大字锚点「60 年」
- density: 字数约 200 / 图片 0 / 留白 25%
- anti_pattern: 禁止等宽卡片横排；禁止只摆数字不给判断
- description: 虚构人物陈守义1963—2025，8个人生节点，一句话定位；巨型数字「60」配洞察。

### P4 创意与痛点
- title: 记忆正在流失，而回忆录停留在纸上
- type: content / role: supporting / rhythm: valley
- layout: 对比式（现状 vs 我们）
- visual: 左右两区竖线分隔，各配小图/图标
- density: 字数约 220 / 图片 0 / 留白 20%
- anti_pattern: 禁止50:50机械对半且无结论；禁止对称罗列N大优势
- description: 左——传统回忆录纯文字图片、AI回忆录无沉浸；右——3D场景+时代物品+口述节点，底部结论条。

### P5 技术实现总览
- title: 从一句话，到一件可以旋转的3D物品
- type: content / role: supporting / rhythm: valley
- layout: 流程链（g）
- visual: 5阶段横向流程：访谈文本→文生图→图生3D→GLB→网页
- density: 字数约 160 / 图片 0 / 留白 25%
- anti_pattern: 禁止阶段>6；禁止无箭头方向
- description: 展示完整AIGC生产链路，每阶段一句说明，群核Lux3D承担文生图与图生3D两环。

### P6 群核技术栈应用
- title: Lux3D 如何成为整部作品的地基
- type: content / role: hero / rhythm: peak
- layout: 巨型数字+洞察
- visual: 深底 + 巨型「100%」锚点 + 三条实质作用
- density: 字数约 180 / 图片 0 / 留白 30%
- anti_pattern: 禁止等宽卡片横排；禁止把核心数字塞进角落
- description: 强调8件物品100%经Lux3D图生3D生成，点明文生图接口、任务轮询、批量队列；呼应评分30%权重。

### P7 关键资产迭代
- title: 一件物品，是怎么"长"出来的
- type: content / role: supporting / rhythm: valley
- layout: 左图右文（7:3）
- visual: 左侧搪瓷缸文生图大图，右侧迭代三步
- density: 字数约 180 / 图片 1 / 留白 20%
- anti_pattern: 禁止对半分；禁止图旁无结论
- description: 以红双喜搪瓷缸为例：文生图prompt→图生3D→解压提取GLB，讲清迭代过程与技术细节。

### P8 八件时代物品
- title: 八个年代，八个可以拿在手里的记忆
- type: content / role: supporting / rhythm: valley
- layout: 卡片组+底部结论条（4张卡，2行）
- visual: 4张代表性物品图（搪瓷缸/自行车/BP机/脸盆）
- density: 字数约 200 / 图片 4 / 留白 15%
- anti_pattern: 禁止卡片>4；禁止全等高均分呆板
- description: 展示8件跨年代物品，点出每件对应的时代烙印，底部结论：物品是最强的记忆锚点。

### P9 成果展示
- title: 一本可以点开、可以走进去的册子
- type: content / role: hero / rhythm: peak
- layout: 左图右文（6:4）
- visual: 左侧主视觉 cover.png 或场景图，右侧功能三点
- density: 字数约 170 / 图片 1 / 留白 25%
- anti_pattern: 禁止50:50；禁止把功能罗列成均分卡
- description: 展示网页册子：封面翻页、8章时间轴、3D可拖拽旋转缩放、在线分享链接，强调核心功能真实可体验。

### P10 评分呼应与创新
- title: 我们用作品回应了每一个评分维度
- type: content / role: supporting / rhythm: valley
- layout: 2×2矩阵+说明
- visual: 四象限——创新性/完成度/技术栈/趣味性
- density: 字数约 220 / 图片 0 / 留白 20%
- anti_pattern: 禁止维度不是正交轴硬套矩阵
- description: 把作品亮点对齐专业评分维度：形式创新、完整可运行、群核深度应用、情感共鸣。

### P11 价值与展望
- title: 每个普通人的一生，都值得被认真记下
- type: content / role: supporting / rhythm: valley
- layout: 三栏非均分（5:3:2）
- visual: 左栏大字宣言，中栏价值，右栏展望
- density: 字数约 190 / 图片 0 / 留白 25%
- anti_pattern: 禁止等宽三栏
- description: 家庭记忆传承、口述史数字化、AI访谈产品化；未来接入真实采访与语音。

### P12 结尾
- title: 谢谢观看
- type: ending / role: hero / rhythm: peak
- layout: 收束金句+落款
- visual: 深底 + 金句 + Demo链接落款
- density: 字数约 50 / 图片 0 / 留白 45%
- anti_pattern: 禁止只写"谢谢"占整页
- description: 金句「让记忆，不再是按下删除键就消失的东西」，附在线Demo链接与团队落款。
