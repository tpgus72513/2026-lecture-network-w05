#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse

FULL = 0xFFFFFFFF


def ip_to_int(text):
    """'163.152.6.5' -> 32-bit int. Four decimal octets, each 0-255."""
    parts = text.strip().split(".")
    if len(parts) != 4:
        raise ValueError(f"not a dotted quad: {text!r}")
    value = 0
    for p in parts:
        if not p.isdigit() or int(p) > 255:
            raise ValueError(f"bad octet {p!r} in {text!r}")
        value = (value << 8) | int(p)
    return value


def int_to_ip(value):
    return ".".join(str((value >> s) & 0xFF) for s in (24, 16, 8, 0))


def prefix_mask(plen):
    """/24 -> 0xFFFFFF00. Shift ones in from the left, keep 32 bits."""
    return (FULL << (32 - plen)) & FULL


def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    addr, sep, plen = cidr.strip().partition("/")
    if not sep or not plen.isdigit():
        raise ValueError(f"missing or bad prefix length: {cidr!r}")
    plen = int(plen)
    if not 0 <= plen <= 32:
        raise ValueError(f"prefix length {plen} outside 0-32: {cidr!r}")
    net = ip_to_int(addr)
    if net & ~prefix_mask(plen) & FULL:
        raise ValueError(f"host bits set, {cidr!r} is a host, not a network")
    return net, plen


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    Careful at the edges. /31 and /32 do not have a usable host range in the
    ordinary sense - decide what you return and say so in observation.md.

    /0-/30  network+1, broadcast-1, broadcast (all-ones host part)
    /31     both addresses are hosts, no broadcast (RFC 3021 point-to-point)
    /32     the one address is the host, no broadcast
    """
    net, plen = parse_cidr(cidr)
    last = net | (~prefix_mask(plen) & FULL)
    if plen == 32:
        return int_to_ip(net), int_to_ip(net), None
    if plen == 31:
        return int_to_ip(net), int_to_ip(last), None
    return int_to_ip(net + 1), int_to_ip(last - 1), int_to_ip(last)


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match. If two entries have the same prefix
    length, the table is malformed - say what you do.

    Two different networks of the same length can never both contain one
    address, so the only real conflict is the same prefix added twice. Adding
    it again with the same next hop is a no-op; with a different next hop it
    raises ValueError instead of silently picking one.
    """

    def __init__(self):
        self.routes = {}                      # (prefix_len, network) -> next_hop

    def add(self, cidr, next_hop):
        net, plen = parse_cidr(cidr)
        old = self.routes.get((plen, net))
        if old is not None and old != next_hop:
            raise ValueError(f"{cidr} already points to {old!r}, "
                             f"refusing a second next hop {next_hop!r}")
        self.routes[(plen, net)] = next_hop

    def matches(self, address):
        """Every entry that contains address, longest first."""
        a = ip_to_int(address) if isinstance(address, str) else address
        hits = [(plen, net, hop) for (plen, net), hop in self.routes.items()
                if a & prefix_mask(plen) == net]
        return sorted(hits, reverse=True)

    def lookup(self, address):
        a = ip_to_int(address) if isinstance(address, str) else address
        best_len, best_hop = -1, None
        for (plen, net), hop in self.routes.items():
            if plen > best_len and a & prefix_mask(plen) == net:
                best_len, best_hop = plen, hop
        return best_hop


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
