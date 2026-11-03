# 分支模型与上游同步

本仓库是 FUjr/QModem 的下游修改版，用于给 5G CPE（RM520N-GL / M28C）增加
`qmodem.antenna_signal` 实时天线信号方法。改动由自动化工作流在上游更新时自动重新叠加。

## 分支

| 分支 | 内容 | 用途 |
|---|---|---|
| `main` | 上游源码 + 本仓库 CI 工作流 | 默认分支，仅承载 `.github/workflows/sync-upstream.yml` |
| `upstream` | 纯 FUjr/QModem:main 镜像（无改动） | 给同步工作流做差异比对与重建基准 |
| `custom` | 上游 + antenna_signal 改动 | **构建分支**，Kwrt / ImmortalWrt 的 feed 指向此分支 |

feed 行（在 Kwrt 的 `diy.sh` 中）：

```
src-git qmodem https://github.com/<你的账号>/QModem.git;custom
```

## 同步机制

`.github/workflows/sync-upstream.yml` 在以下情况运行：

- 每 6 小时定时（`cron`）
- 手动 `workflow_dispatch`
- 外部 `repository_dispatch`（event_type: `upstream-update`）

运行逻辑：

1. `git fetch upstream` 拉取 FUjr/QModem:main
2. 比对 `upstream/main` 与本仓库 `upstream` 分支是否一致
3. 不一致则：
   - 把本仓库 `upstream` 分支推进到最新上游
   - 以最新上游为基底，`git apply patches/antenna-signal.patch` 重建 `custom`
   - 强制推送 `custom`

## 本地改动如何进入同步

所有对 QModem 源码的修改都汇总进 `patches/antenna-signal.patch`
（由 `git diff <上游干净提交> custom` 生成）。工作流靠这个 patch 文件重建 `custom`，
因此**改了源码后必须重新生成并提交该 patch 文件**，否则上游一更新，你的改动会丢失。

重新生成 patch：

```sh
git diff <上游干净提交SHA> custom -- \
  application/qmodem/files/usr/libexec/rpcd/qmodem \
  application/qmodem/files/usr/share/qmodem/cmds/quectel.sh \
  application/qmodem/files/usr/share/qmodem/vendor/quectel.sh \
  docs/qmodem-rpcd-interface.md \
  docs/kwrt-integration.md \
  examples/at_rsrp.cgi > patches/antenna-signal.patch
git add patches/antenna-signal.patch && git commit -m "refresh reapply patch"
```
