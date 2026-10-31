# 风格文档

这份文档是调色风格的**唯一来源**:流水线脚本(`style_apply.py`、`style_proof.py`)直接从这里读取参数。
新增或修改风格只需要改这一份文件。

- 每个风格是一个 `## 风格名` 小节;小节里**第一个** ```` ```json ```` 代码块就是它的参数,其余文字只是说明。
- 风格名就是命令行里用的名字,也是输出目录名(`runs/<拍摄>/style_applied/<风格名>/`),建议 `字母_中文名` 的形式。
- 改完先运行校验:`.venv/bin/python -I pipeline/style_lib.py`(会列出每个风格的目标值,格式不对会报错)。

---

## 风格是怎么套用的

一个风格由三部分组成:

| 部分 | 字段 | 作用 |
|---|---|---|
| 固定参数 | `settings` | 所有照片统一写入的 Lightroom 参数:对比度、高光阴影、HSL、色调曲线、颗粒、暗角等 |
| 肤色目标 | `skin` | 宝宝脸部中央皮肤的目标颜色(Lab)。**曝光**按它的亮度 L 逐张校准;画面里白色不够时,白平衡也按它的 a/b 校准 |
| 白色目标 | `white` | 画面中近白区域(床单、衣服、毯子)的目标偏色(Lab 的 a/b)。白色面积 ≥ 8% 时,**白平衡**按它校准 |

逐张校准流程(`style_apply.py`):

1. 写入 `settings`,用当前曝光 / 白平衡导出一张 1600px 校准图(按你的裁切)。
2. 在校准图上检测宝宝的脸,测脸部中央皮肤和全图近白区域的 Lab。
3. 调整曝光(让肤色 L 达到目标)和白平衡(让白色或肤色的 a/b 达到目标),重复 3~4 轮直到收敛。
4. 没测到脸的照片,借用时间上最近一张照片的校准结果。
5. RAW 按 ISO 自动加明亮度降噪(≤1600: 10,≤3200: 20,≤6400: 30,更高: 40);JPG 和 AI 降噪过的 DNG 不加。

切换风格时,其他风格设过而本风格没设的参数会自动归零(或恢复中性值),不会留下上一个风格的痕迹。
裁切、角度、方向永远不动。

**为什么要有白色目标:** RAW 照片只按肤色定白平衡时,为了让皮肤达到目标红润度,色调会被推到 +40 左右,
白色床单随之发粉发紫。改为以白色定白平衡、肤色只管曝光后,白色干净,肤色仍然自然。

### Lab 数值怎么理解

| 分量 | 含义 | 参考 |
|---|---|---|
| L | 亮度,0 黑 ~ 100 白 | 宝宝肤色 65~72 属于明亮通透;每差 3 左右大约是 0.3 档曝光 |
| a | 正值偏红/品红,负值偏绿 | 肤色 13~15 自然红润;白色 >2 开始能看出发粉 |
| b | 正值偏黄,负值偏蓝 | 肤色 15~22 从清冷到温暖;白色 1~2 干净,4~6 奶油暖白,>8 明显发黄 |

---

## 风格一览

| | A_清透奶白 | B_暖调胶片 | C_自然通透 | D_富士胶片 |
|---|---|---|---|---|
| 一句话 | 高调、明亮、奶白干净 | 温暖怀旧的胶片感 | 真实色彩、层次清晰 | 富士 400H:清透偏冷、粉彩 |
| 肤色目标 L / a / b | 72 / 13 / 15 | 68 / 15 / 22 | 66 / 14 / 18 | 70 / 14 / 16 |
| 白色目标 a / b | 0.5 / 1.5(干净白) | 1.0 / 5.0(奶油暖白) | 0.5 / 2.5(中性略暖) | -0.3 / 0.5(略冷白) |
| 对比 | 柔 | 柔,黑位提亮发灰 | 略强,黑位实 | 低,黑位提亮雾感 |
| 色彩 | 低饱和,黄绿压低 | 低饱和,绿偏黄、蓝压低,暖色分离色调 | 自然,鲜艳度 +10 | 薄荷青绿,阴影偏青,肤色粉嫩,粉彩 |
| 质感 | 柔化(纹理 -10,清晰度 -5) | 胶片颗粒 + 轻微暗角 | 略锐(纹理 +5,清晰度 +5) | 细颗粒,无暗角 |
| 适合 | 白色床品、浅色布景、新生儿/百天 | 室内暖光、生活记录、想要氛围感 | 彩色道具多(气球)、纪实、需要还原真实颜色 | 粉彩布景、浅绿/青色床品、日系清新 |

---

## A_清透奶白

**定位:** 日系高调奶白。整体明亮,高光柔和,白色干净不偏色,肤色白里透粉。

**画面特点**
- 肤色目标最亮(L72),整体比另外两个风格亮约半档。
- 高光大幅压低(-45)保护床单细节;阴影提亮(+20)、黑位略提(+5),反差柔和。
- 降低整体饱和度,黄、绿、橙压低,画面里杂色少,呈现"奶白"感。
- 纹理、清晰度略减,皮肤显得细腻。
- 色调曲线:黑点抬到 8、高光端收到 252,轻微的空气感。

**注意**
- 曝光推得最多。暗场景下可能碰到曝光上限(`--max-ev`,默认 0.9,RAW 我们用 1.5),这时脸会比目标略暗。
- 背光、半边脸在阴影里的照片,肤色测量容易偏暖,需要看总览确认。

```json
{
  "desc": "high-key airy: soft contrast, protected highlights, desaturated creams, bright clean skin",
  "skin": {"L": 72, "a": 13, "b": 15},
  "white": {"a": 0.5, "b": 1.5},
  "settings": {
    "Contrast2012": -10,
    "Highlights2012": -45,
    "Shadows2012": 20,
    "Whites2012": 5,
    "Blacks2012": 5,
    "Texture": -10,
    "Clarity2012": -5,
    "Vibrance": 5,
    "Saturation": -8,
    "SaturationAdjustmentOrange": -8,
    "LuminanceAdjustmentOrange": 10,
    "SaturationAdjustmentYellow": -25,
    "SaturationAdjustmentGreen": -20,
    "ToneCurvePV2012": [0, 8, 64, 68, 128, 134, 192, 197, 255, 252]
  }
}
```

## B_暖调胶片

**定位:** 温暖怀旧的胶片感。黑位发灰、色彩收敛、带细颗粒和淡淡暗角。

**画面特点**
- 肤色目标最暖(b22),白色是奶油暖白(b5),整体色温比 A 高几百 K。
- 黑位明显提亮(Blacks +10,曲线黑点抬到 22),高光端收到 245,形成胶片的"褪色"感。
- 绿色偏黄并降饱和(-30),蓝色降饱和(-20),彩色道具不抢眼。
- 分离色调:阴影和高光都加少量暖橙(色相 35/45,饱和 8/10)。
- 颗粒 12、暗角 -8,在 100% 下颗粒细而均匀;对高 ISO 照片能掩盖一部分噪点。

**注意**
- 颗粒是渲染时加上的,缩小看不出来,放大或打印才明显。
- 不适合需要还原准确颜色的场景(例如服装、蛋糕颜色要和实物一致)。

```json
{
  "desc": "warm film: faded blacks, muted greens, warm split-tone, light grain and vignette",
  "skin": {"L": 68, "a": 15, "b": 22},
  "white": {"a": 1.0, "b": 5.0},
  "settings": {
    "Contrast2012": -15,
    "Highlights2012": -35,
    "Shadows2012": 15,
    "Whites2012": -5,
    "Blacks2012": 10,
    "Saturation": -12,
    "Vibrance": 6,
    "Texture": -5,
    "HueAdjustmentGreen": 15,
    "SaturationAdjustmentGreen": -30,
    "SaturationAdjustmentYellow": -10,
    "SaturationAdjustmentBlue": -20,
    "SplitToningShadowHue": 35,
    "SplitToningShadowSaturation": 8,
    "SplitToningHighlightHue": 45,
    "SplitToningHighlightSaturation": 10,
    "SplitToningBalance": 0,
    "GrainAmount": 12,
    "GrainSize": 20,
    "GrainFrequency": 50,
    "PostCropVignetteAmount": -8,
    "PostCropVignetteMidpoint": 50,
    "PostCropVignetteFeather": 70,
    "ToneCurvePV2012": [0, 22, 60, 64, 128, 130, 200, 203, 255, 245]
  }
}
```

## C_自然通透

**定位:** 纪实自然。颜色接近真实,层次清楚,不加特效。

**画面特点**
- 肤色目标 L66,三个风格里最实;白色接近中性、略暖(b2.5)。
- 对比略加(+5),黑位略压(-5),曲线保持线性,暗部有分量。
- 鲜艳度 +10,不动整体饱和度,彩色气球、道具颜色最鲜活。
- 纹理、清晰度各 +5,细节清楚但不生硬。

**注意**
- 不提亮黑位,饱和颜色(金色、蓝色气球)个别通道会顶到头,属于正常的饱和表现,不是溢出。
- 没有颗粒遮盖,高 ISO 照片的噪点会比 B 明显,建议先做 AI 降噪。

```json
{
  "desc": "natural documentary: true colour, crisp but gentle, moderate highlight recovery",
  "skin": {"L": 66, "a": 14, "b": 18},
  "white": {"a": 0.5, "b": 2.5},
  "settings": {
    "Contrast2012": 5,
    "Highlights2012": -30,
    "Shadows2012": 15,
    "Whites2012": 5,
    "Blacks2012": -5,
    "Texture": 5,
    "Clarity2012": 5,
    "Vibrance": 10,
    "Saturation": 0,
    "ToneCurvePV2012": [0, 0, 255, 255]
  }
}
```

## D_富士胶片

**定位:** 模拟富士 Fujicolor Pro 400H 负片,日系人像/儿童摄影里辨识度最高的"富士色"。清透、偏冷、粉彩。

**富士感从哪里来**(参考:Mastin Labs、Presetpro 对 400H 的描述,Fujilove 的 400H 数码模拟方法)
- **薄荷绿 / 青绿**:绿色色相大幅往青色推、降饱和、提亮,青色提亮;浅绿、青色床单和气球会变成粉彩的薄荷色。
- **阴影偏青**:颜色分级给阴影加青绿(色相 185),校准面板的阴影色调往绿偏。
- **肤色粉嫩不发黄**:橙色色相往红偏、提亮,黄色降饱和;校准面板红原色略往洋红偏,肤色粉嫩干净。
- **粉彩、低反差、雾感**:对比降低,曲线黑点抬到 18、高光收到 248,蓝、紫、洋红降饱和并提亮。
- **白色略冷**:白色目标 b 只有 +0.5,比 A/B/C 都冷,带一点青。
- 细颗粒(10)模拟胶片质感,不加暗角。

**适合:** 浅色、粉彩布景(气球、浅绿或青色床品),白天自然光;想要日系清新感。

**注意**
- 校准面板(`RedHue` 等)会改变所有颜色的基础,调这个风格时以它为主、HSL 为辅。
- 白色目标偏冷(b0.5)。如果画面里的"白"其实是奶白衣服、米色沙发,整张会被校得太冷、肤色发灰;这类照片用 `--skin-wb` 改按肤色定白平衡
  (气球组的 04747、04777、04792、04793 就是这样处理的)。
- 白色不够的照片本来就按肤色定白平衡,肤色目标偏粉(b16),不会发黄。

```json
{
  "desc": "Fuji Pro 400H: mint/cyan greens, cyan shadows, pink clean skin, pastel low contrast, slightly cool whites",
  "skin": {"L": 70, "a": 14, "b": 16},
  "white": {"a": -0.3, "b": 0.5},
  "settings": {
    "Contrast2012": -15,
    "Highlights2012": -40,
    "Shadows2012": 25,
    "Whites2012": 0,
    "Blacks2012": 5,
    "Texture": -5,
    "Saturation": -8,
    "Vibrance": 5,
    "HueAdjustmentRed": 5,
    "HueAdjustmentOrange": -10,
    "SaturationAdjustmentOrange": -3,
    "LuminanceAdjustmentOrange": 8,
    "HueAdjustmentYellow": 10,
    "SaturationAdjustmentYellow": -25,
    "HueAdjustmentGreen": 40,
    "SaturationAdjustmentGreen": -25,
    "LuminanceAdjustmentGreen": 15,
    "HueAdjustmentAqua": -10,
    "SaturationAdjustmentAqua": -15,
    "LuminanceAdjustmentAqua": 12,
    "HueAdjustmentBlue": -10,
    "SaturationAdjustmentBlue": -20,
    "LuminanceAdjustmentBlue": 10,
    "SaturationAdjustmentPurple": -20,
    "SaturationAdjustmentMagenta": -15,
    "LuminanceAdjustmentMagenta": 8,
    "ShadowTint": -8,
    "RedHue": -6,
    "RedSaturation": 0,
    "GreenHue": -15,
    "GreenSaturation": 5,
    "BlueHue": -10,
    "BlueSaturation": 10,
    "SplitToningShadowHue": 185,
    "SplitToningShadowSaturation": 12,
    "SplitToningHighlightHue": 0,
    "SplitToningHighlightSaturation": 0,
    "SplitToningBalance": 0,
    "GrainAmount": 10,
    "GrainSize": 15,
    "GrainFrequency": 60,
    "ToneCurvePV2012": [0, 18, 64, 70, 128, 132, 192, 195, 255, 248]
  }
}
```

---

# 维护指南

> 本节及以下内容不是风格,脚本只读取 `## ` 小节里的 json 代码块。下面的示例代码块放在 `###` 小节里,不会被当成风格。

### 新增一个风格

1. 复制一个现有风格的整个小节(从 `## 名字` 到它的 json 代码块),放在"维护指南"**之前**,改名,例如 `## D_森系柔绿`。
2. 改文字说明(定位、画面特点、注意),写清楚想要的效果。
3. 改 json:
   - `skin`:先从最接近的风格抄,再按"Lab 数值怎么理解"调整。L 每 +3 大约亮 0.3 档。
   - `white`:想要干净白 b≈1.5,奶油白 b≈5;a 保持 0.5~1,不要超过 2,否则发粉。
   - `settings`:Lightroom 参数,字段名见下表。没写的参数保持 Lightroom 默认值。
4. 运行校验:`.venv/bin/python -I pipeline/style_lib.py`
5. 先出样片对比,再整组套用(见"常用命令")。

### 修改已有风格

- 只改了文字说明:不需要做任何事。
- 改了 `settings`、`skin` 或 `white`:需要重新校准后套用(不要用 `--reuse-calib`,它会沿用旧的曝光/白平衡)。
  可以加 `--refine` 从上次的校准结果起步,收敛更快。

### 常用参数名(`settings` 里的字段)

| 字段 | 面板 | 范围 | 默认 |
|---|---|---|---|
| `Exposure2012` | 曝光(由校准决定,不要写在风格里) | -5 ~ +5 | 0 |
| `Contrast2012` / `Highlights2012` / `Shadows2012` / `Whites2012` / `Blacks2012` | 基本 | -100 ~ +100 | 0 |
| `Texture` / `Clarity2012` / `Dehaze` | 基本 · 质感 | -100 ~ +100 | 0 |
| `Vibrance` / `Saturation` | 基本 · 鲜艳度/饱和度 | -100 ~ +100 | 0 |
| `HueAdjustment<颜色>` / `SaturationAdjustment<颜色>` / `LuminanceAdjustment<颜色>` | HSL,颜色为 Red Orange Yellow Green Aqua Blue Purple Magenta | -100 ~ +100 | 0 |
| `SplitToningShadowHue` / `SplitToningHighlightHue` | 颜色分级(阴影/高光色相) | 0 ~ 360 | 0 |
| `SplitToningShadowSaturation` / `SplitToningHighlightSaturation` | 颜色分级(饱和度) | 0 ~ 100 | 0 |
| `SplitToningBalance` | 颜色分级 · 平衡 | -100 ~ +100 | 0 |
| `ToneCurvePV2012` | 点曲线,`[输入1, 输出1, 输入2, 输出2, ...]`,0~255 | — | `[0,0,255,255]` |
| `GrainAmount` / `GrainSize` / `GrainFrequency` | 效果 · 颗粒 | 0 ~ 100 | 0 / 25 / 50 |
| `PostCropVignetteAmount` | 效果 · 裁切后暗角(负值变暗) | -100 ~ +100 | 0 |
| `PostCropVignetteMidpoint` / `PostCropVignetteFeather` / `PostCropVignetteRoundness` | 效果 · 暗角形状 | 0~100 / 0~100 / -100~100 | 50 / 50 / 0 |
| `SharpenDetail` / `SharpenRadius` 等 | 细节 | — | — |

**不要写进风格的字段:** 白平衡(`Temperature`、`Tint`、`IncrementalTemperature`、`IncrementalTint`、`WhiteBalance`)、
`Exposure2012`、`LuminanceSmoothing`(由校准和降噪规则逐张决定),以及裁切相关(`Crop*`、`orientation`)。

**默认值不是 0 的字段:** 切换风格时,别的风格设过的字段会被恢复成"中性值"。默认值不是 0 的字段
(如 `GrainSize` 25、暗角 `Midpoint` 50)需要登记在 `pipeline/style_lib.py` 的 `NEUTRAL` 里;
用到上表以外、默认值不是 0 的新字段时,记得在那里加一行。

### 常用命令

```bash
# 校验风格文档
.venv/bin/python -I pipeline/style_lib.py

# 整组套用(RAW 建议 --max-ev 1.5 --iters 4)
.venv/bin/python -I pipeline/style_apply.py runs/<拍摄> styles/STYLES.md <风格名> --collection <收藏集> --iters 4 --max-ev 1.5

# 从已有校准起步(风格参数小改后)
... --refine

# 只重做几张
... --refine --only JBZ04827.ARW JBZ04819.ARW

# 个别照片的"白"其实是奶白/米色(衣服、沙发),按白色校会整张偏冷:改按肤色定白平衡
... --refine --only JBZ04792.ARW --skin-wb JBZ04792.ARW

# 不重新校准,直接套回之前的结果(风格参数没改过时)
... --reuse-calib

# 撤销到调色前
.venv/bin/python -I pipeline/style_apply.py runs/<拍摄> --rollback runs/<拍摄>/style_applied/<风格名>/baseline.json
```

套用后输出在 `runs/<拍摄>/style_applied/<风格名>/`:`overview_*.jpg` 总览、`boxes.jpg` 测量框检查
(`pipeline/check_boxes.py` 生成)、`calib.json` 每张的校准结果、`baseline.json` 调色前备份。
