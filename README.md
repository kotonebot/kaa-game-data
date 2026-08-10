# kaa-game-data

学园アイドルマスター离线游戏数据构建与发布。

## 数据流

```
gakumasu-diff → game.db → tasks.json → [gom|campus] → sprites → GitHub Release
```

## 前置条件

- Python >= 3.10
- `gakumasu-diff` 数据源（独立 clone，非 submodule；本地或 CI 拉取）
- `GkmasObjectManager`、`campus` submodule（`kaa-data vendor-sync` 初始化）
- 使用 `campus` 后端时需预先编译 `campus/campus`（或 `campus.exe`）

## 安装

```bash
pip install -e .
```

## 命令

```bash
kaa-data vendor-sync                 # submodule + vendor patches
kaa-data build [--backend gom|campus] # 完整构建
kaa-data schema                      # YAML → game.db
kaa-data tasks                       # game.db → tasks.json
kaa-data sprites --backend gom       # 下载精灵图
kaa-data package                     # 打包 release 产物
kaa-data release                     # 发布 GitHub Release
kaa-data prune-releases [--keep 3] [--dry]  # 清理旧 release，仅保留最新 N 个
kaa-data diff-backends               # 对比 gom / campus 产物
```

本地快捷脚本：

```powershell
.\scripts\build.ps1 -Backend gom
```

```bash
./scripts/build.sh gom
```

## 配置

见 `pipeline.toml`。路径、默认后端、zstd 压缩级别、vendor 目录均可在此调整。

## 输出产物

| 文件 | 说明 |
|------|------|
| `output/release/game.db.zst` | 压缩 SQLite 数据库 |
| `output/release/idol_cards.zip` | P 偶像卡精灵图 |
| `output/release/skill_cards.zip` | 技能卡精灵图 |
| `output/release/drinks.zip` | 饮品精灵图 |
| `output/release/manifest.json` | 版本清单（md5 / size） |
| `output/build-report.json` | 构建报告 |

## 后端说明

- **gom**（默认）：纯 Python，`GkmasObjectManager` 按 `tasks.json` 精确下载，无需 Firebase token
- **campus**：`campus --ab` 同步 manifest，按 `tasks.json` 从 cache/CDN 提取，无需 Firebase token

下载范围由 `tasks.json` 决定，不依赖 campus `--webab` 正则过滤。

## CI

GitHub Actions 每 6 小时构建一次，支持手动触发并选择 `gom` / `campus` 后端。
每次运行时都会调用 `prune-releases` 清理旧的 `data-*` release，仅保留最新 3 个。