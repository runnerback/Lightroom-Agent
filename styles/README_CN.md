[English](./README.md) | 中文

# 风格

每个调色风格是本文件夹里的**一个 Markdown 文件**,文件名就是风格名:`A_Airy_White.md`、`D_Fuji_400H.md`……
文件里**第一个** ```` ```json ```` 代码块是参数,其余文字是写给人看的说明。新增风格就加一个文件,删除风格就删掉它的文件。

- **风格名** = 去掉 `.md` 的文件名,命令行里用它,输出目录也叫这个名字(`<工作目录>/style_applied/<风格名>/`)。
  建议用 `字母_名字` 的形式:只要字母不重复,单写字母也可以(`apply-style D`)。
- **你自己的风格**放在 `~/.lightroom-agent/styles/`(Windows:`%USERPROFILE%\.lightroom-agent\styles\`)。更新项目不会
  动这个文件夹;和内置风格同名的文件会替换内置风格。环境变量 `LIGHTROOM_AGENT_STYLES` 可以再指定其他文件夹。
- `README*.md` 和以 `_` 开头的文件不是风格([`_template.md`](./_template.md) 是新风格的模板)。
- 改完运行 `lightroom-agent styles` 校验:会列出所有风格,格式有错时指出是哪个文件。

## 风格是怎么套用的

一个风格由三部分组成:

| 部分 | 字段 | 作用 |
|---|---|---|
| 固定参数 | `settings` | 所有照片统一写入的 Lightroom 参数:对比度、高光阴影、HSL、色调曲线、颜色分级、校准、颗粒、暗角 |
| 肤色目标 | `skin` | 主体脸部中央皮肤的目标颜色(Lab)。**曝光**按它的亮度 L 逐张校准;画面里白色不够时,**白平衡**也按它的 a/b 校准 |
| 白色目标 | `white` | 画面中近白区域(衬衫、墙面、床单、天空薄雾)的目标偏色(a/b)。白色面积 ≥ 8% 时,**白平衡**按它校准 |

逐张校准流程(`pipeline/style_apply.py`):

1. 写入 `settings`,由 Lightroom 按你的裁切渲染一张 1600px 校准图。
2. 检测主体的脸,测量脸部中央皮肤和近白区域的 Lab。
3. 调整曝光(肤色 L 到目标)和白平衡(白色或肤色的 a/b 到目标),迭代 3~4 轮,取最接近目标的一轮。
4. 深肤色保留原有深度:脸比同一画面里最亮的部分暗很多时,自动降低肤色亮度目标。
5. 没有可用人脸的照片(风光、建筑、背影)借用 30 分钟内最近一张人像的校准(同样的光线);没有的话保持相机原本的曝光和白平衡,只套风格。
6. RAW 按 ISO 自动加明亮度降噪(≤1600: 10,≤3200: 20,≤6400: 30,更高: 40);JPG 和 AI 降噪过的 DNG 不加。

切换风格时,上一个风格设过、本风格没设的参数会恢复中性值,不留痕迹。裁切、角度、方向永远不动。

**为什么要有白色目标:** RAW 只按肤色定白平衡时,为了让皮肤达到红润的目标,色调会被推到 +40 左右,白衬衫、白床单随之发粉。
以白色定白平衡、肤色只管曝光,白色干净,肤色仍然自然。

### Lab 数值怎么理解

| 分量 | 含义 | 参考 |
|---|---|---|
| L | 亮度,0 黑 ~ 100 白 | 浅肤色 65~72 属于明亮通透;差 3 左右约 0.3 档曝光 |
| a | 正值偏红/品红,负值偏绿 | 肤色 13~15 自然红润;白色 >2 开始能看出发粉 |
| b | 正值偏黄,负值偏蓝 | 肤色 15~22 从清冷到温暖;白色 1~2 干净,4~6 奶油暖白,>8 明显发黄 |

肤色目标是按浅肤色调的,深肤色由上面第 4 步处理。

## 内置风格

每个一个文件:[A_Airy_White](./A_Airy_White.md) · [B_Warm_Film](./B_Warm_Film.md) · [C_Natural](./C_Natural.md) · [D_Fuji_400H](./D_Fuji_400H.md)

| | A 清透奶白 | B 暖调胶片 | C 自然通透 | D 富士 400H |
|---|---|---|---|---|
| 一句话 | 高调、明亮、奶白干净 | 温暖怀旧的胶片感 | 真实色彩、层次清晰 | 富士 Pro 400H:清透偏冷、粉彩 |
| 肤色目标 L / a / b | 72 / 13 / 15 | 68 / 15 / 22 | 66 / 14 / 18 | 70 / 14 / 16 |
| 白色目标 a / b | 0.5 / 1.5(干净白) | 1.0 / 5.0(奶油暖白) | 0.5 / 2.5(中性略暖) | −0.3 / 0.5(略冷白) |
| 对比 | 柔 | 柔,黑位提亮发灰 | 略强,黑位实 | 低,黑位提亮雾感 |
| 色彩 | 低饱和,黄绿压低 | 低饱和,绿偏黄、蓝压低,暖色分离色调 | 自然,鲜艳度 +10 | 薄荷青绿,阴影偏青,肤色粉嫩,粉彩 |
| 质感 | 柔化(纹理 −10,清晰度 −5) | 胶片颗粒 + 轻微暗角 | 略锐(纹理 +5,清晰度 +5) | 细颗粒,无暗角 |
| 适合 | 明亮室内、白色背景、婚礼、高调人像 | 室内暖光、生活记录、黄金时刻街拍 | 街拍、旅行、纪实、风光、建筑 | 日光人像、粉彩场景、日系清新 |

## 新增风格

1. 把 [`_template.md`](./_template.md)(或最接近的现有风格)复制为 `~/.lightroom-agent/styles/E_My_Style.md`;
   想贡献给项目就放到本文件夹。
2. 用文字写清楚想要的效果、适合的场景和注意事项。
3. 改 json:
   - `desc`:一句话描述,AI 选风格时会看到。
   - `skin`:从最接近的风格抄起,按上面的 Lab 说明调整。L 每 +3 约亮 0.3 档。
   - `white`:干净白 b≈1.5,奶油白 b≈5;a 保持 0.5~1(超过 2 发粉)。不写 `white` 就只按肤色定白平衡。
   - `settings`:Lightroom 参数,字段名见英文版 [README](./README.md#common-keys-settings) 的参数表。没写的参数保持 Lightroom 默认值。
4. 运行 `lightroom-agent styles` 校验。
5. 先拿 2~3 张出样片,满意后再整组套用。也可以直接对 AI 说:*"仿照柯达 Portra 400 加一个风格"*。

**不要写进风格的字段:** 白平衡(`Temperature`、`Tint`、`IncrementalTemperature`、`IncrementalTint`、`WhiteBalance`)、
`Exposure2012`、`LuminanceSmoothing`(由校准和降噪规则逐张决定),以及裁切相关(`Crop*`、`orientation`)。校验时会报错。

**贡献风格:** 提交 Pull Request,包含风格的 `.md` 文件和 2~3 张照片的前后对比图(他人肖像请先取得同意)。字母按顺序取下一个没用过的。

## 修改已有风格

- 只改文字说明:不需要做任何事。
- 改了 `settings`、`skin` 或 `white`:重新校准后套用(不要用 `--reuse-calib`,它会沿用旧的曝光/白平衡)。
  加 `--refine` 可以从上次的校准结果起步,收敛更快。

## 常用命令

```bash
lightroom-agent styles                                              # 校验并列出风格
lightroom-agent apply-style D --collection "样片"                    # JPG 默认参数
lightroom-agent apply-style D --collection "精选" --max-ev 1.5 --iters 4   # RAW
lightroom-agent apply-style D --collection "精选" --refine --only IMG_0012.ARW IMG_0230.ARW
lightroom-agent apply-style D --collection "精选" --refine --only IMG_0301.ARW --skin-wb IMG_0301.ARW
lightroom-agent check-boxes D --collection "精选"                    # 检查每张的测量位置
lightroom-agent rollback --collection "精选"                         # 撤销到第一次套风格之前
```
