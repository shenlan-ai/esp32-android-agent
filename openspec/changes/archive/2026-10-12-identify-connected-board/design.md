# Design

## Context

检测到 USB\VID_10C4&PID_EA60，Windows ConfigManagerErrorCode=28；当前进程无管理员权限，全局 esptool 5.5.0 可用。

## Goals / Non-Goals

**Goals:** 从实际硬件识别可用芯片和存储能力，建立适配依据。

**Non-Goals:** 不在识别阶段刷写固件，不通过 VID/PID 猜测 PCB 型号。

## Decisions

- 串口驱动使用 Silicon Labs 官方包或 Windows 官方驱动通道，核验有效签名后安装。管理员权限由正常 Windows UAC 提供，不绕过系统保护。
- 通过 esptool chip-id 和 flash-id 读取，操作可能短暂复位设备但不写 Flash。
- 检测脚本输出结构化诊断；驱动不可用时返回明确待恢复状态，独立开发继续。
- 自动选择只考虑已知 ESP USB/UART 厂商的在线串口；多个候选时要求指定端口，不能将其他串口设备当作开发板。读取命令使用 `--no-stub`，不上传 RAM stub。
- 仅对明确识别的经典 ESP32、S2、S3、C3、C6、H2 提供相应 USB/BLE 路线；未知或无可用 HID 能力的芯片返回未支持，不能退化为经典 ESP32。

## Risks / Trade-offs

- 官方下载被网络拦截 → 使用官方页面或 Windows 驱动通道；不改用不明下载站。
- 桥接芯片无法确定主芯片 → 恢复串口后读取主芯片；不能当作 S3 处理。
