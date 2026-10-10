---
title: "CCNA备考初学心得（一）：交换机与路由器的转发原理"
date: 2026-10-10T22:46:12+08:00
draft: false
slug: "ccna-switch-router-forwarding"
categories:
  - CCNA
tags:
  - 心得
---



学习路由表时，略有些对packets的理解不到位，为此写下关于 **ARP 地址解析、交换机的二层转发，以及路由器的三层转发**的一些分析理解。

下面以 PC1 访问不同子网的 PC2 为例，梳理整个过程。

## 一、网络拓扑

```text
PC1 ── Switch1 ── Router ── Switch2 ── PC2
 |                  |   |                 |
192.168.1.10   192.168.1.1          192.168.2.10
                192.168.2.1
```

假设 PC1 所在子网是 `192.168.1.0/24`，PC2 所在子网是 `192.168.2.0/24`，PC1 的默认网关为 `192.168.1.1`。路由器的两个接口分别连接这两个子网。

## 二、ARP：先找到下一跳的 MAC 地址

PC1 想访问 `192.168.2.10`，查路由表后发现目标不在本地子网，需要把数据包交给下一跳 `192.168.1.1`。

如果 PC1 尚未缓存网关的 MAC 地址，就广播 ARP Request：

```text
Ethernet Destination MAC: FF:FF:FF:FF:FF:FF
Ethernet Source MAC:      PC1 的 MAC
ARP Sender IP:            192.168.1.10
ARP Sender MAC:           PC1 的 MAC
ARP Target IP:            192.168.1.1
ARP Target MAC:           00:00:00:00:00:00
```

它问的是：**“谁拥有 192.168.1.1？请告诉 192.168.1.10。”** 这里查询的是**网关的 MAC**，不是 PC2 的 MAC。路由器回复 ARP Reply 后，PC1 将网关 IP 与 MAC 的对应关系存入 ARP 缓存。

## 三、二层交换机：根据 MAC 转发 Frame

Switch1 收到 ARP Request 时，会根据以太网帧的 **Source MAC** 学习 PC1 位于哪个端口，并更新 MAC Address Table。由于 ARP Request 的目的 MAC 是广播地址，交换机会把它泛洪到同一 VLAN 的其他转发端口。

路由器返回 ARP Reply 时，Switch1 又能学习路由器接口的 MAC。后续 PC1 发送数据帧，交换机便根据 **Destination MAC** 查表转发。

普通二层交换机的核心动作是：

```text
接收 Frame → 学习 Source MAC → 查询 Destination MAC → 转发 Frame
```

它通常**不需要取出其中的 IP Packet 进行路由**，也不修改 IP 地址或 TTL。但 VLAN 标签等二层字段在特定场景下可能变化。

## 四、路由器：处理 Packet，再重新封装 Frame

PC1 发出的数据具有如下结构：

```text
Ethernet Frame
├── Source MAC:      PC1 的 MAC
├── Destination MAC: Router 入接口的 MAC
└── IP Packet
    ├── Source IP:      192.168.1.10
    ├── Destination IP: 192.168.2.10
    ├── TTL:            64
    └── TCP/UDP 等上层数据
```

路由器收到帧后，处理并移除原有的二层封装，读取 **Destination IP**，查询路由表，确定从连接 `192.168.2.0/24` 的接口转发。同时把 TTL 从 `64` 减为 `63`，并更新 IPv4 首部校验和。

如果还不知道 PC2 的 MAC，路由器会在 PC2 所在子网发送 ARP Request。随后用下一条链路所需的二层信息，**重新封装** IP Packet：

```text
New Ethernet Frame
├── Source MAC:      Router 出接口的 MAC
├── Destination MAC: PC2 的 MAC
└── IP Packet
    ├── Source IP:      192.168.1.10
    ├── Destination IP: 192.168.2.10
    └── TTL:            63
```

普通路由转发通常不需要进一步处理 TCP/UDP 首部；不过 NAT/PAT、ACL 等功能可能检查甚至修改传输层字段。

## 五、Switch 与 Router：区别在哪里？

| 对比项    | 二层交换机            | 路由器                           |
| --------- | --------------------- | -------------------------------- |
| 主要依据  | Destination MAC       | Destination IP                   |
| 查询的表  | MAC Address Table     | Routing Table / FIB              |
| 转发对象  | Ethernet Frame        | IP Packet（通过链路层帧承载）    |
| 二层封装  | 通常保留原有 MAC 地址 | 通常重新生成下一跳所需的二层封装 |
| IP Header | 通常不修改            | 转发时修改 TTL 等必要字段        |

### 总结

完整路径是：

```text
PC1 ──ARP 获取网关 MAC──> Router
PC1 ──Frame──> Switch1 ──Frame──> Router
Router ──新 Frame──> Switch2 ──Frame──> PC2
```

**我的理解是：交换机主要决定“这个 MAC 在哪个端口”，路由器主要决定“这个目标 IP 应该往哪里走”。** 路由器重新封装二层帧，<u>根本原因是数据包进入了下一条链路，需要使用对应的链路层地址和封装；并不只是因为它修改了 TTL</u>。

另外，所谓“交换机不解封装”，指的是**普通二层转发不需要把 Frame 解封装成 IP Packet 再执行路由**；并不表示交换机完全不解析帧头。
