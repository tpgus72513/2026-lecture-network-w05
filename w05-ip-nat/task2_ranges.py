#!/usr/bin/env python3
"""Week 5 · Task 2 A2/A3 — check the hand computation with Task 1's code.

The addresses below were read by hand off the raw ipconfig output in
out/addresses.json (the Wi-Fi adapter section). This only checks the arithmetic.

    python3 task2_ranges.py > out/task2-ranges.txt
"""
from task1_forward import int_to_ip, ip_to_int, network_range, prefix_mask

# label, interface address, mask, default gateway   (read from ipconfig /all)
READ_BY_HAND = [
    ("home Wi-Fi",                "192.168.219.108", "255.255.255.0", "192.168.219.1"),
    ("phone hotspot (both runs)", "10.155.204.215",  "255.255.255.0", "10.155.204.132"),
]

PRIVATE = [("10.0.0.0", 8), ("172.16.0.0", 12), ("192.168.0.0", 16)]   # RFC 1918
SHARED = ("100.64.0.0", 10)                                             # RFC 6598


def inside(addr, net, plen):
    return ip_to_int(addr) & prefix_mask(plen) == ip_to_int(net)


def kind(addr):
    if any(inside(addr, n, p) for n, p in PRIVATE):
        return "private (RFC 1918)"
    if inside(addr, *SHARED):
        return "shared / carrier-grade NAT (RFC 6598)"
    if inside(addr, "192.0.0.0", 29):
        return "IPv4 service continuity, 464XLAT (RFC 7335)"
    return "public"


for label, addr, mask, gw in READ_BY_HAND:
    m = ip_to_int(mask)
    plen = bin(m).count("1")
    assert prefix_mask(plen) == m, "mask is not contiguous"
    net = ip_to_int(addr) & m
    cidr = f"{int_to_ip(net)}/{plen}"
    first, last, bcast = network_range(cidr)
    print(f"== {label}")
    print(f"  address {addr}  mask {mask} (/{plen})  -> {kind(addr)}")
    print(f"  network {addr} AND {mask} = {cidr}")
    print(f"  network_range -> first {first}  last {last}  broadcast {bcast}"
          f"  ({(1 << (32 - plen)) - 2} usable)")
    print(f"  gateway {gw} inside {cidr}: {inside(gw, int_to_ip(net), plen)}\n")

print("== other addresses seen")
for a, where in [("124.52.76.47", "public, home"), ("124.52.76.1", "home traceroute hop 2"),
                 ("118.235.25.102", "public, phone LTE"), ("192.0.0.3", "LTE traceroute hop 2"),
                 ("10.203.14.61", "home traceroute hop 3"), ("100.107.3.53", "home traceroute hop 4"),
                 ("100.112.140.37", "Tailscale adapter")]:
    print(f"  {a:<16} {where:<24} {kind(a)}")
print(f"  124.52.76.1 and 124.52.76.47 share a /24: "
      f"{inside('124.52.76.1', '124.52.76.0', 24) and inside('124.52.76.47', '124.52.76.0', 24)}")
