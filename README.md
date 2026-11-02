# sprite-talk

一张立绘 + 几张嘴型/眨眼贴片 + 一条配音 → 会说话的 2D 主播视频。
One still + a few mouth/blink overlays + a voice track → a talking 2D host video.

[中文](#中文) | [English](#english)

## 演示 / Demo

https://github.com/zwjym1/sprite-talk/raw/main/examples/host_o/demo.mp4

[examples/host_o/demo.mp4](examples/host_o/demo.mp4)（host_o 示例，约 0.7 MB / sample render, ~0.7 MB）

## 动作预设 / Motion presets

| `--preset` | 说明 / Description |
|---|---|
| （默认 default）`GENERIC_LOOP` | 通用 25 帧循环曲线，`--dy-gain 0.75` / generic 25-frame loop |
| `aning_v4` | 已验收的 v4 说话动作（\|sin\| 点头）/ approved v4 talk motion |
| `aning_feel` | 舒缓版，动而不晃 / calmer, moves without shaking |
| `aning_dyn` | 12 帧循环、跟随响度包络的更动态版本 / livelier, envelope-driven |

预设只包含数值参数（见 `sprite_talk/presets.py`），不含任何参考视频素材。Presets are numeric parameters only; no reference footage is included.

---

## 中文

### 方法

1. **底部锚定的身体形变（body warp）**
   每个像素按 `w(y)·(dx, dy)` 位移：
   `w(y) = clip((BOT − y) / (BOT − PIV), 0, 1) ^ γ`（默认 γ=1）。
   - `PIV` 以上（头部）整块刚性移动；`PIV` 到 `BOT` 线性衰减；脚/画面底边钉住不动。
   - `PIV` 默认在“从头顶算起可见高度的 0.355”处，约在下巴下方。
   - 不加旋转、不加缩放脉冲：在参考片上拟合出的旋转只有 0.37° 峰峰值，可忽略。
   - 摆动（sway, dx）和点头（bob, dy）幅度**按屏幕上的头高缩放**（头顶→下巴），不按全身高度。
   - 内置一条通用循环曲线 `GENERIC_LOOP`（25 帧 / 0.83 秒，纯数值数据，单位为头高）。它是手工参数曲线，不是从任何第三方视频描出来的。
2. **嘴型轨道**：每帧 RMS 响度 → 闭 / 小张 / 大张三档；嘴比声音提前约 1 帧；有对齐数据时，每个辅音开头的音节强制闭嘴一帧（形成逐音节开合）；去掉孤立的 1 帧张嘴闪烁。可选：基于普通话拼音韵母的 viseme（A E I O U N MBP F）。
3. **眨眼调度**：平均 3.8 秒一次，带抖动，15% 概率双眨，模式为 半闭-闭-闭-半闭。
4. **sync 测量**：在视频嘴部框里统计嘴内像素，与音频响度做互相关；最佳滞后 0 或 −1 帧（嘴略领先）表示同步。
5. **校准**：用你自己提供的参考片段拟合运动曲线和 dy 增益（见下）。

### 为什么 bob ×0.75

我们拿一段商业 2D 说话主播的参考片段（未包含在仓库中）做过逐帧对比：把她自己的一张静帧用本方法形变，与真实 96 帧比较（剪影 IoU / 平均像素误差）：

| 驱动 | IoU | MAE |
|---|---|---|
| 静止 | 0.923 | 12.0 |
| 整体平移 | 0.940 | 9.70 |
| 默认形变，光流拟合 dx/dy | 0.948 | 7.28 |
| + 旋转（最优最小二乘） | 0.949 | 7.27 |
| dy = 剪影头顶下沉 ×1.0 | 0.947 | 7.67 |
| **dy = 剪影头顶下沉 ×0.75**（采用） | **0.948** | **7.09** |

“头顶剪影下沉量”最容易测，但它夸大了网格的真实位移（头发外轮廓比脸动得多）。乘以 0.75 后误差最低，所以 `--dy-gain` 默认 0.75。各部位（头发、发饰、衣领、手）相对脸部都是 0 帧滞后，说明这是一个同相位的整体网格形变，不需要二级头发运动。`GENERIC_LOOP` 的 dy 存的是“剪影下沉”单位，渲染时乘 `dy_gain`。

### 安装

```bash
pip install -e .            # numpy, opencv-python-headless, Pillow；需要系统里有 ffmpeg
pip install -e .[zh]        # 可选：pypinyin（辅音闭嘴、viseme）
pip install -e .[align]     # 可选：torch + torchaudio（MMS_FA 强制对齐）
```

### 用法

```bash
python examples/demo.py                     # 渲染示例 → out/host_a_demo.mp4，并做 sync / 校准自检
sprite-talk render examples/host_a/sprites.json examples/host_a/vo.mp3 -o talk.mp4 \
    --alignment examples/host_a/vo_timings.json
sprite-talk align vo.wav "你好世界" -o alignment.json       # 可选，普通话强制对齐
sprite-talk mouth vo.wav --alignment alignment.json         # 打印每帧 0/1/2
sprite-talk blinks 900
sprite-talk sync talk.mp4 --box 420,560,560,700              # 嘴部框 x0,y0,x1,y1
sprite-talk calibrate ref.mp4 --start 82 --dur 3.2 --crop 1280,200,1920,1080 -o my_curve.json
sprite-talk render sprites.json vo.wav --curve my_curve.json --dy-gain <校准给出的值>
```

`sprites.json` 格式见 `sprite_talk/sprites.py` 和 `examples/host_a/sprites.json`。贴片可以是整张图，也可以是放在 `overlay_offset` 的裁切图；只粘贴与底图有差异的像素（羽化 + 低频偏色校正）。

### 参数

| 参数 | 默认 | 含义 |
|---|---|---|
| `--piv-ratio` | 0.355 | 刚性头块下沿，占可见高度（从头顶算）的比例 |
| `--amp` | 1.0 | 运动总幅度倍数 |
| `--dy-gain` | 0.75 | 剪影下沉 → 实际形变 dy 的增益 |
| `--curve` | 内置 | 自定义曲线 JSON（`calibrate` 的输出） |
| `--alignment` | 无 | 对齐 JSON：`[{"text","start","end"}]` 或 `[text, roman, start, end]` |
| `--visemes` | 关 | 用 viseme 贴片（需在 sprites.json 里提供 A/E/I/O/U/N/MBP/F） |
| 嘴型阈值 | 0.42 / 0.13 | 归一化响度：大张 / 小张（`mouth_levels(hi, lo)`） |

### 校准工具做了什么

读取片段 → 剪影（暗/纯色背景用 `max(RGB)>thr`，或 `--bg-diff` 中值背景差）→ Farneback 光流（每帧对参考静帧）→ 用 `w(y)` 最小二乘拟合每帧 dx/dy → 每帧头顶下沉 → **把静帧按不同 dy 增益重新形变并与真实帧比较，取误差最小的增益** → 自相关检测循环周期，输出一个周期的曲线。自检：对本仓库自己渲染的视频跑校准，得到 dy 增益 1.0（正确，因为渲染时 dy 就是剪影下沉）。只用你有权使用的素材做校准。

### 局限

- 只有平移形变：没有转头、没有身体倾斜、没有手势；姿态切换需要另做。
- 不透明底图要求暗色或纯色背景（`BORDER_REPLICATE` 填边）；建议用带透明通道的立绘。
- 嘴型三档由响度驱动，不懂语义；viseme 只有普通话拼音映射。
- `sync` 的嘴部像素检测是阈值法，需按角色调 `--box/--thr/--mode`；示例上最佳滞后 −1 帧、相关 0.32（三档嘴型的上限不高）。
- 校准假设头身在一个平面内、背景基本静止；光流在大面积纯色区会低估，因此增益用“重渲染比误差”而不是光流斜率。全分辨率下每帧约 0.3 秒。
- 内置曲线是通用的；要贴近特定风格，请用自己的参考片段校准。

---

## English

### Method

1. **Bottom-anchored body warp.** Each pixel moves by `w(y)·(dx, dy)`, with `w(y) = clip((BOT − y)/(BOT − PIV), 0, 1)^γ` (γ=1). Above `PIV` the head moves as a rigid block; between `PIV` and `BOT` the motion falls off linearly; the feet / frame bottom stay pinned. `PIV` defaults to 0.355 of the visible height from the top of the head (just under the chin). There is no rotation and no scale pulse: the rotation fitted on the reference was 0.37° peak-to-peak, which is negligible. Sway (dx) and bob (dy) amplitudes **scale with on-screen head height** (top of head to chin), not body height. The package ships a generic 25-frame (0.83 s) loop `GENERIC_LOOP` as plain numbers in head-height units. It is a hand-built parametric curve, not traced from third-party footage.
2. **Mouth track.** Per-frame RMS loudness maps to closed, small or large. The mouth leads the audio by about 1 frame. When an alignment is given, the mouth is forced closed for one frame at each consonant-initial syllable, so it flaps once per syllable. Isolated 1-frame open blips are removed. Optional Mandarin pinyin visemes: A E I O U N MBP F.
3. **Blink scheduler.** About one blink every 3.8 s with jitter, and a 15% chance of a double blink. Each blink runs half, closed, closed, half.
4. **sync measure.** Counts mouth-interior pixels in a box and cross-correlates them with audio loudness. A best lag of 0 or −1 frames (mouth slightly ahead) reads as in sync.
5. **Calibration.** Fits a motion curve and dy gain from a reference clip that you supply.

### Why bob ×0.75

We warped a single still taken from a commercial 2D talking-host reference clip (not included) and compared the result with the 96 real frames. The full table is in the Chinese section. The best IoU/MAE (0.948 / 7.09) came from **dy = 0.75 × the silhouette-top dip**. Using 1.0× gave 0.947 / 7.67, and the full least-squares fit with rotation added gave 0.949 / 7.27. The silhouette dip is easy to measure, but it overstates the real mesh shift because the hair outline moves more than the face. All parts (hair, hair clip, collar, hands) moved with 0 frames of lag relative to the face, so the motion is one in-phase mesh warp and needs no secondary hair motion. `GENERIC_LOOP.dy` is stored in dip units and multiplied by `--dy-gain`.

### Install / Usage / Parameters

The commands and the parameter table are the same as in the Chinese section above. In short: `pip install -e .` (ffmpeg must be on PATH), then `python examples/demo.py` writes `out/host_a_demo.mp4` and runs a sync check and a calibration round-trip.

### Calibration

The tool takes these steps:
1. Build a silhouette from the frames.
2. Compute Farneback flow from each frame back to a still.
3. Least-squares fit dx/dy under `w(y)`.
4. Measure the per-frame silhouette dip.
5. Re-warp the still at a grid of dy gains and keep the one with the lowest pixel error.
6. Detect the loop period by autocorrelation and output one period.

As a round-trip check, calibrating on the demo render returns gain 1.0, which is correct because that render uses dy = dip. Only calibrate on footage you have the rights to use.

### Limitations

- The warp is translation only. There is no head turn, body lean, gesture or pose switching.
- Opaque base images need a dark or plain background. Sprites with an alpha channel are preferred.
- The 3-level mouth is driven by loudness only. Visemes are mapped for Mandarin only.
- The `sync` pixel detector is threshold based, so tune it per character. The demo gives a best lag of −1 frame with corr 0.32.
- Calibration assumes a roughly planar character and a static background. It takes about 0.3 s per frame at full resolution.

### License

MIT. The Host A example assets (an original character and our own TTS voice-over) are under the same license. See `examples/host_a/ASSETS.md`.

## Motion preset `aning_v4`

`--preset aning_v4` reproduces the approved host-A v4 talk motion (see `sprite_talk/presets.py`):
bottom-pinned linear warp, rigid above 0.307 head-heights over the chin; while speaking
`dx = 0.0288*hh*g*(1-cos θ)/2`, `dy = 0.0559*hh*g*|sin θ|`, `θ = 2π(t-onset)/(12.5 f)`;
gate attack 0.45 / release 0.16; idle breathing 0.0022*hh @ 0.25 Hz. Pass `--head-px`
(hair top->chin) and `--chin-y`. Differs from default `GENERIC_LOOP`
(25 f loop, bipolar ±0.016 sway, one big + one small dip, x0.75 dy-gain, pivot 0.355).

## Motion preset `aning_feel`

`--preset aning_feel` is the comfortable Aning workflow profile (moves, does not shake).
Matched to Skill SideTalk remeasure (AY≈0.050 HH, AX≈0.0295 HH): `dy = AY*g*sin²θ`,
`dx = AX*g*(1-cos(θ+70°))/2`, continuous clock `T=18 f @30fps` (no onset reset),
soft gate attack 0.22 / release 0.12, same bottom-anchored `LinearPinWarp` as v4.
Use this when `aning_v4`'s `|sin|` bob feels too bouncy. Default preset is unchanged
(still `GENERIC_LOOP` unless `--preset` is passed).
