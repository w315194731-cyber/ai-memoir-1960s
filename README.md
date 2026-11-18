# 拾光 · AI 人生回忆录

> 把普通人的一生，做成一本可以翻阅、也可以「走进去」的 3D 回忆录。

本项目为「群核 Aholo 全球 3D AI 黑客松」参赛作品。以虚构人物陈守义（1963 年生）的一生为蓝本，用 AI 访谈式叙事拆解出 8 个人生节点，每个节点配一件有时代烙印的物品——红双喜搪瓷缸、石板和石笔、煤油灯、二八自行车、BP 机、黑白电视、早期智能手机、搪瓷脸盆。这些物品由群核 Lux3D 生成图片再转为 3D 模型，嵌入可翻页的网页册子中。

## 在线 Demo

**https://memoir-1960s.app.workbuddy.host/?sharecode=RQCNEKCMEF**

> 链接需要带完整的 `sharecode` 参数才能打开。

## 功能

- 书册式翻页：封面 → 时间轴目录 → 8 个章节，支持按钮、圆点、方向键翻页
- 每件时代物品都是可拖动旋转、滚轮缩放的 3D 模型
- 每章含故事正文、「那年头」时代注脚与一句人生教训
- 手机自适应；3D 模型逐章懒加载
- 另含一个教室 3D 场景样例（`index.html`），可切换 three.js 程序化版本与群核 3DGS 版本

## 技术链路

```
访谈式叙事文本
   ↓  大模型拆解节点（时间/地点/事件/感受/教训）
结构化数据 memoir-data.json
   ↓  文生图 multimodal-to-image
物品写实图片
   ↓  群核 Lux3D 图生3D img-to-3d
GLB 三维模型
   ↓  three.js + GLTFLoader
可交互的网页册子
```

图生 3D 返回的是压缩包，内含 `mesh/tex_mesh.glb`（网页使用）与 3DGS 版本；`artifact_pipeline.py` 会自动解压提取。

## 目录结构

| 文件 | 说明 |
| --- | --- |
| `memoir.html` | 回忆录主页面（最终作品） |
| `memoir-data.json` | 8 章故事、时代注脚、教训与物品提示词 |
| `index.html` | 教室场景样例，可点击「走进这间教室」 |
| `assets/ch*.glb` | 8 件由 Lux3D 生成的 3D 模型（约 135MB） |
| `artifact_pipeline.py` | 批量生产流水线：文生图 → 图生3D → 解压 → 落盘 |
| `queue_worker.py` | 世界生成队列：上传素材 → 提交 → 轮询 → 写回配置 |
| `generate_classroom.py` | 教室 3DGS 场景生成（单次任务示例） |
| `upload_reference.py` / `validate_pipeline.py` | 上传与链路验证脚本 |
| `pipeline-state.json` 等 | 断点续跑状态，记录任务 ID，避免重复提交 |
| `report/` | 参赛项目报告 PPT、分镜设计与逐页 DSL |
| `report/Demo演示视频-分镜与台词.md` | 演示视频分镜、旁白稿与录屏清单 |

## 本地运行

网页依赖浏览器的模块加载与本地文件读取，不能直接双击 HTML 打开。请在本目录起一个静态服务：

```bash
python -m http.server 8000
```

然后浏览器访问 `http://localhost:8000/memoir.html`。

## 关于 API Key

所有脚本都从环境变量读取密钥，**仓库中不含任何 API key**：

```bash
export LUX3D_CN_API_KEY="你的群核资产API密钥"
export AHOLO_API_KEY="你的群核世界API密钥"
```

如需重新生成物品，配置好环境变量后运行 `python artifact_pipeline.py`；建议先用 `python artifact_pipeline.py --dry-run` 空跑确认任务清单。

## 素材与版权说明

- 8 件物品的写实图片与 3D 模型均由群核 Lux3D 生成；PPT 封面为 AI 生成。
- `reference/` 中的老教室照片来自公开网络文章，仅作建模参考，未用作作品成品画面。
- 人物「陈守义」及全部故事为虚构创作，不涉及真实个人隐私问题。

## 许可

源代码可自由查看与学习。使用的第三方服务（群核 Lux3D / Aholo API）需遵守其各自的服务条款。
