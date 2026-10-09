# Danmaku Contract（千夜追忆 弹幕契约）

本文件描述 `proto/phk/v1/danmaku.proto` 及其派生数据/代码产物的字段含义、单位与逆向来源。

> **版权与用途**：本契约由对东方 Project 同人作品《千夜追忆 (Touhou: Thousand Night Anamnesis)》
> 1.40 的静态逆向成果移植而来，**仅用于自研玩法的服务端权威模拟**。仓库内不包含任何原版
> 美术/音频二进制资源，只保留数值、枚举与结构布局。原作品版权归其作者所有。

## 1. 数据源

| 产物 | 生成脚本 | 上游 |
|---|---|---|
| `data/danmaku_kinds.json` | `tools/export_danmaku_data.py` | `data/tna_contract.json`（`rev/tools/gen_contract.py`） |
| `data/danmaku_motions.json` | 同上 | `data/tna_contract.json` |
| `data/player_loadout.json` | 同上 | `data/tna_contract.json` + `rev/patterns/player_shots_disasm.md` §3 |
| `gen/cpp/phk/v1/danmaku.hpp` | `tools/export_danmaku_cpp.py` | `danmaku.proto` + 上述 data |
| `gen/go/phk/v1/danmaku.go` | `tools/export_danmaku_go.py` | `danmaku.proto` + 上述 data |

逆向报告目录：`rev/patterns/`（`bullet_kind_table.md`、`create_bullet_command.md`、
`bullet_funcs_disasm.md`、`player_shots_disasm.md`、`boss_pattern_tables.md`、`enum_tables.md`）。

## 2. 全局约定（实测）

1. **角度单位 = 度 (degree)**，不是弧度。原版 `0xace18c = 57.295780` 是 度↔弧度 换算常量
   （180/π）。移植时全程沿用度，避免角速度常量换算错误。
2. **发射位置哨兵**：`spawn_x/spawn_y == -1.0` 表示「跟随发射者坐标」。
3. **场地**：640×960，半宽 320 / 半高 480；逻辑帧率 60 Hz。
4. **服务端权威坐标用整数 milli**（1/1000 px），沿用现有 `BossRaceBullet` 风格。
5. **确定性 RNG** 输入 = `(match_seed, tick, pattern_index, spawn_index)`，禁用系统时间/帧率。
6. cocos2d 原点在**左下**，`angle = 90°` 朝正上方。

## 3. 枚举

### 3.1 `BulletKind`（216 + `UNSPECIFIED`）
- **值 = 原版 `kEnemyBullet` 枚举值**（9…224），**不重编号**，客户端用它索引图集帧。
- 分派表位于原版 `EnemyBullet::spriteWithFile` @ `0xb0a180`（216 × `uint16`，索引 = `type - 9`）。
- 命名 = `BULLET_KIND_<图集帧名大写>`（如 `kusabi_01` → `BULLET_KIND_KUSABI_01`）。
- 43 个物种，多数每 9 个连续 type 共享一个物种（帧 01–09）；`zeni`(3)/`ltama`(5)/`kou`(7) 等帧数不足。
- 完整表见 `data/danmaku_kinds.json` 与 `rev/patterns/bullet_kind_table.md`。

### 3.2 `BulletMotion`（79）
- **与原版 `EnemyBullet::bulletFuncN` 编号一一对应**（= 运行期状态号 `EnemyBullet+0x5B4`，取值 1…85）。
- 命名 `BULLET_MOTION_FUNC_NN`。
- **为何不按 A–M 归并**：服务端需要「状态号 → 逐帧更新」的精确分派键；归并是有损的。
  归并信息保留在 `BulletMotionFamily` 与 `data/danmaku_motions.json.family_code`。
- **注意**：`FUNC_00 = 0` 是真实运动（初始化/直线），不是占位值。
- 原版缺失 func `9/10/49/56/59/68/69`（无实现），故 79 而非 86 个。
- 运动逻辑内联在 `EnemyBullet::update`，由跳转表 @ `0xb0a88e` 分派。

### 3.3 `BulletMotionFamily`（A–M + UNCLASSIFIED）
- 来自 `bullet_motions.family_group` 的首字母 A–M（13 类）。
- `family_group` 为空串的 7 个 func（14/37/46/52/61/63/64）归入 `UNCLASSIFIED`（待确认）。
- 因此数据里实际有 **14 个桶**（13 个字母 + 1 个未分类），文档口径统一以此为准。

### 3.4 `PlayerBulletType`（0…83）
- 原版 `kMyBullet` 枚举值：`0..61` 自机射击贴图、`62..82` 炸弹贴图（复用 `kMyBullet`）、`83` 擦弹。
- 命名取自 `.so` 内**实际贴图字符串**（`myshot_*` / `mybomb_*`）。
- 资源复用导致重名者追加 `_T<NN>` 消歧：type 33 与 24 同图、type 79 与 78 同图。
- 贴图名以 `.so` 字符串为准（任务书中的 `ply_shot_01..13.png` 未出现于字符串表）。

## 4. 消息

### 4.1 `BulletSpawnCommand`（28 字段 / 96 字节）
严格对应原版 `Enemy::CreateBulletCommand`（`Enemy::createBullets1` @ `0x37bacc`）。
字段号 = 原版结构体偏移顺序：

| 字段 | 偏移 | 说明 |
|---|---|---|
| `bullet_type` | +0 | `BulletKind` 值 |
| `frame_index` | +4 | 图集帧号 |
| `spawn_x` / `spawn_y` | +8 / +12 | `-1.0` = 跟随发射者 |
| `flag16` | +16 | 透传 `spriteWithFile` 第 5 参 |
| `base_angle_deg` | +20 | 基础角度（度） |
| `f24`…`f40` | +24…+40 | 透传（语义未确定） |
| `count` | +44 | 本次发射数量（`0` → 直接返回）；原版 `int16` |
| `spread_or_speed` | +48 | 张角/速度，参与起始角计算 |
| `s52`/`s54`/`s56` | +52/+54/+56 | 透传 `spriteWithFile` p11–p13 |
| `f60`…`f80` | +60…+80 | 透传 p14–p19 |
| `s84`…`s94` | +84…+94 | 透传 p20–p25 |

- **整数 milli 约定仅作用于运行期状态与快照**，不改变本发射指令的原版 float 布局。
- C++ 侧 `struct BulletSpawnCommand` 用显式 padding 复刻 96 字节并 `static_assert(sizeof == 96)`。
- 协议 `int32` 承载原版 `int16` 字段（proto3 无 int16）。

**`createBullets1` 发射算法**：整圆径向发射器 —— `angleStep = 360.0 / count`，
起始角 = `baseAngle - spread`，负值归一化 +360。

### 4.2 `DanmakuSpawnBatch`
一个 tick 内的整批齐射，是 `BATTLE_PAYLOAD_TYPE_DANMAKU_SPAWN` 的载荷。
携带 `tick / pattern_index / spawn_index / owner_enemy_id` 与 `commands`。

### 4.3 `DanmakuBulletState`
运行期子弹状态：`bullet_kind`、`motion`、`x_milli/y_milli/vx_milli/vy_milli`、`life_ticks`、
`radius_milli`、`age_ticks`、`func_state`（原版 `+0x5B4` 状态号）、`angle_deg`、`owner_enemy_id`。

### 4.4 `DanmakuTimelineEntry` / `BossPhasePattern`
对应原版 `Enemy::setBossBullet11..22` + `setBossBulletPatchou`。
`setBossBullet*` 本质是「逐帧硬编码参数序列 + 节点链表构造器」，无 `bl → bulletFunc`
（实测 0 次）。一个构造批次可导出为
`{ phase, sub_phase, sub_phase_2, period_ticks, phase_offset, node_size_bytes, bullet_count,
pattern_node_id, base_angle_deg, spread_deg, ... }`。
`phase_field_offset` 记录主阶段字段（如 `0x534`）。完整逐点时序**未全部提取**（见 `boss_pattern_tables.md` §7），
未解析项以 `angle_expr/offset_expr` 保留原始表达式。

### 4.5 `PlayerShotSpec` / `PlayerBombSpec` / `DanmakuLoadout`
- 射击 52 条（13 角色 × A/B × 变体 1/2），对应 `MyShip::createBullets<Chara><A|B><N>`。
  `bullet_types` / `angles_deg` 为逐发值；`resolved=false` 表示含循环生成/未静态捕获项。
  主射速 8 帧；副射与特判周期因角色而异（12/6/200…）。
- 炸弹 13 条（每角色 1 个 `createBomb<Chara>`）：`total_frames` = `#1368`（表 `0xb23d50`），
  `invuln_frames` = `#1372`（表 `0xb23d0b`），`bullet_types`/`sprites` 为 1..N 个 `MyBomb` 组合。
  `w1..w5` 参数语义**未确定**（`player_shots_disasm.md` §5），未纳入结构。

## 5. 生成产物

- `gen/cpp/phk/v1/danmaku.hpp`：4 个 `enum class` + POD 结构（`DanmakuFieldSpec`、
  `BulletSpawnCommand`、`DanmakuBulletState`、`DanmakuTimelineEntry`）+ 216/79 查找表 +
  `BulletKindFrame/Atlas/Species`、`BulletMotionFamilyOf` 辅助函数。`BulletKindInfo` 含
  `kind/frame/atlas/species`（`species` 由帧名去尾号得到，供客户端按物种分组）。仅依赖标准库。
- `gen/go/phk/v1/danmaku.go`（package `phkv1`）：枚举常量 + 查找 map（含 `BulletKindSpecies`）
  + `PlayerShots`/`PlayerBombs`。
- 本仓库现有 codegen **不产出 TypeScript**，故无 TS 产物。

## 6. 待确认项（未编造）

1. `BulletSpawnCommand` 中 `f24..f80`、`s52..s94` 的语义未确定，仅知为透传。
2. `BulletMotionFamily` 中 `UNCLASSIFIED`（7 个 func）的分族待确认。
3. `boss_pattern_tables.md` 的节点 `id → bulletFunc` 映射表基址未定位。
4. 部分 `PlayerShotSpec`（`resolved=false`）的逐发炮口偏移/角度未静态还原。
5. `PlayerBombSpec` 的 `w1..w5` 语义未确定。
