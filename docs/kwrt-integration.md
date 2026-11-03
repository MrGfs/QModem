# 把改后的 QModem 编入 Kwrt / OpenWrt / ImmortalWrt 固件

目标：在 kiddin9/Kwrt（或你的 fork）构建出的固件里，包含带 `antenna_signal` 方法的 QModem，
供 M28C（Widora MangoPi，RM520N-GL 5G 模组）的"天线信号实时可视化 + 历史记录"前端调用。

## 1. 维护一个 QModem fork / 分支

上游 `FUjr/QModem` 是 MPL-2.0 + 禁止商用的附加条款（见仓库 LICENSE）。本改动是增量、向后兼容，
建议：

1. Fork `FUjr/QModem` 到你账号，例如 `you/QModem`。
2. 把本目录（含 `antenna_signal` 方法、`cmd_qrsp/qsrq/qscp/qrsgr` 封装、文档）提交到该 fork 的一个分支，例如 `feat/antenna-signal`。
3. 后续同步上游时 rebase 该分支即可，改动不会与 `info`/`network_info`/`send_at` 冲突。

## 2. 在 Kwrt 的 diy.sh / feeds 里加 feed 指向你的 fork

在构建系统的 `devices/<target>/diy.sh`（或公共 `devices/common/diy.sh`）里，把原来的：

```sh
# 原（指向上游）
echo "src-git qmodem https://github.com/FUjr/QModem.git;main" >> feeds.conf.default
```

改成指向你的分支（带 `antenna_signal`）：

```sh
# 改后（指向你的 fork + 分支）
sed -i '/src-git qmodem/d' feeds.conf.default
echo "src-git qmodem https://github.com/you/QModem.git;feat/antenna-signal" >> feeds.conf.default
./scripts/feeds update qmodem
./scripts/feeds install -a -p qmodem
```

> M28C 目标（`devices/m28c/`）的 `settings.ini` 已经把 `REPO_URL` 指向 `immortalwrt/immortalwrt`，
> 上面的 feed 改动在两个源码树下都生效（ImmortalWrt 同样支持 QModem 的 `src-git` feed）。

## 3. 确保相关内核模块被编入（5G 模组必需）

在目标 `.config` 里开启（网页勾选或写死）：

```sh
CONFIG_PACKAGE_luci-app-qmodem-next=y
CONFIG_PACKAGE_qmodem=y
CONFIG_PACKAGE_kmod-usb-net-qmi-wwan=y
CONFIG_PACKAGE_kmod-usb-net-cdc-mbim=y
CONFIG_PACKAGE_kmod-usb-serial-option=y
CONFIG_PACKAGE_kmod-usb-serial-wwan=y
CONFIG_PACKAGE_proto-qmi=y
CONFIG_PACKAGE_proto-mbim=y
# RM520N-GL 是 PCIe(M.2) 模组，需要 MHI 驱动
CONFIG_PACKAGE_kmod-mhi-pci-generic=y
```

## 4. 前端调用（两种写法）

### 方案 B（推荐，固件已含本改动）
```sh
ubus call qmodem antenna_signal '{"config_section":"modem1"}'
```
前端定时（如 1s）轮询此接口，直接拿到 4 路天线 RSRP/RSRQ/SINR + 速率因子，落历史日志即可。

### 方案 A（不刷固件、仅加 CGI）
把 `examples/at_rsrp.cgi` 放到路由 `/www/cgi-bin/at_rsrp` 并 `chmod +x`，前端 GET
`/cgi-bin/at_rsrp?modem1` 得到同构 JSON。前提是固件已含原版 QModem（`send_at` 存在）。

## 5. 验收要点
- `ubus call qmodem antenna_signal '{"config_section":"modem1"}'` 返回 4 路数组、bandwidth_mhz、ca_count、mimo_rank。
- RSQR/QRSCP 已是 ÷10 后的 dB（非 0.1dB 原始值）。
- 1 秒级连续调用无空读、无端口竞争（所有 AT 走 tom_modem 托管通道）。
- NSA(ENDC) 与 SA(NR5G) 下均正确解析 NR 段。
- 原 `info` / `network_info` / `send_at` / LuCI 页面不受影响。
