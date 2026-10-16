#!/usr/bin/env python3
"""Week 5 · Task 3 — evidence behind observation.md.

    python3 task3_experiments.py > out/task3-experiments.txt

1. Correctness beyond bench.py: shuffled insertion order, /25-/32 prefixes,
   duplicate prefixes, all compared with LinearTable.
2. The two textbook directions, timed on the bench.py table:
   group-by-length hash, and a one-bit-at-a-time binary trie.
3. What each structure costs in memory, and how much work a lookup does.
"""
import random, sys, time

import bench
from task3_lpm import LinearTable, YourTable

MASK = 0xFFFFFFFF


class LengthHash:
    """Direction 1: one dict per prefix length, asked longest first."""

    def __init__(self):
        self.by_len = {}

    def add(self, network, prefix_len, next_hop):
        self.by_len.setdefault(prefix_len, {}).setdefault(network, next_hop)
        self.order = [(p, (MASK << (32 - p)) & MASK, self.by_len[p])
                      for p in sorted(self.by_len, reverse=True)]

    def lookup(self, address):
        for plen, mask, table in self.order:
            hop = table.get(address & mask)
            if hop is not None:
                return hop
        return None


class BitTrie:
    """Direction 2: walk the address one bit at a time (what hardware does)."""

    def __init__(self):
        self.root = [None, None, None]        # child0, child1, next_hop
        self.nodes = 1

    def add(self, network, prefix_len, next_hop):
        node = self.root
        for i in range(prefix_len):
            b = (network >> (31 - i)) & 1
            if node[b] is None:
                node[b] = [None, None, None]
                self.nodes += 1
            node = node[b]
        if node[2] is None:
            node[2] = next_hop

    def lookup(self, address):
        node, best, i = self.root, self.root[2], 31
        while node is not None:
            if node[2] is not None:
                best = node[2]
            if i < 0:
                break
            node = node[(address >> i) & 1]
            i -= 1
        return best


def random_routes(rng, n):
    routes, seen = [], set()
    while len(routes) < n:
        plen = rng.choice([0, 8, 12, 16, 17, 20, 22, 24, 24, 24, 25, 28, 30, 31, 32])
        net = rng.getrandbits(32) & ((MASK << (32 - plen)) & MASK)
        routes.append((net, plen, f"h{len(routes)}"))
        if rng.random() < 0.05 and (net, plen) not in seen:   # duplicate prefix
            routes.append((net, plen, f"dup{len(routes)}"))
        seen.add((net, plen))
    return routes


def check_random(trials=30, n=400, queries=3000):
    rng = random.Random(5)
    for t in range(trials):
        routes = random_routes(rng, n)
        rng.shuffle(routes)
        lin, mine = LinearTable(), YourTable()
        for r in routes:
            lin.add(*r)
            mine.add(*r)
        qs = []
        for _ in range(queries):
            net, plen, _ = rng.choice(routes)
            qs.append(net | rng.getrandbits(32 - plen) if plen < 32 else net)
            qs.append(rng.getrandbits(32))
        wrong = sum(lin.lookup(a) != mine.lookup(a) for a in qs)
        if wrong:
            return f"trial {t}: {wrong} wrong"
    return f"{trials} trials x {n} shuffled routes (/0-/32, 5% duplicates) x {2 * queries} queries: 0 wrong"


def deep_size(obj, seen=None):
    """Bytes held by nested lists/dicts (shared hop strings counted once)."""
    seen = set() if seen is None else seen
    if id(obj) in seen:
        return 0
    seen.add(id(obj))
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple)):
        size += sum(deep_size(x, seen) for x in obj)
    return size


def timed(cls, routes, queries, reference):
    t0 = time.perf_counter()
    table = cls()
    for net, plen, hop in routes:
        table.add(net, plen, hop)
    build_s = time.perf_counter() - t0
    best = None
    for _ in range(3):                        # best of three, to damp noise
        t0 = time.perf_counter()
        answers = [table.lookup(a) for a in queries]
        s = time.perf_counter() - t0
        best = s if best is None else min(best, s)
    wrong = sum(a != b for a, b in zip(answers, reference))
    return table, build_s, best, wrong


def main():
    print("== 1. correctness beyond bench.py")
    print("  " + check_random())

    routes, queries = bench.build()
    print(f"\n== 2. bench.py table: {len(routes):,} prefixes, {len(queries):,} queries")
    lin = LinearTable()
    for net, plen, hop in routes:
        lin.add(net, plen, hop)
    t0 = time.perf_counter()
    reference = [lin.lookup(a) for a in queries]
    base = time.perf_counter() - t0
    print(f"  {'LinearTable':<24} lookup {base:8.3f}s  {len(queries) / base:>11,.0f}/s"
          f"     1.0x  memory {deep_size(lin.entries) / 1e6:6.2f} MB")

    lengths = sorted({plen for _, plen, _ in routes}, reverse=True)
    tables = {}
    for name, cls in [("LengthHash (by length)", LengthHash),
                      ("BitTrie (1 bit/step)", BitTrie),
                      ("YourTable (16-8-8)", YourTable)]:
        table, build_s, s, wrong = timed(cls, routes, queries, reference)
        tables[cls] = table
        mem = deep_size(table.__dict__)
        print(f"  {name:<24} lookup {s:8.3f}s  {len(queries) / s:>11,.0f}/s"
              f"  {base / s:7.1f}x  memory {mem / 1e6:6.2f} MB"
              f"  build {build_s:.2f}s  wrong {wrong}")

    print("\n== 3. work per lookup")
    print(f"  prefix lengths present: {lengths}")
    by_len = {p: {net for net, q, _ in routes if q == p} for p in lengths}
    probes = 0
    for a in queries:
        for k, plen in enumerate(lengths, 1):
            if a & ((MASK << (32 - plen)) & MASK) in by_len[plen]:
                break
        probes += k
    print(f"  LengthHash: dict probes per lookup, mean {probes / len(queries):.2f},"
          f" worst {len(lengths)}")

    trie = tables[BitTrie]
    steps = 0
    for a in queries:
        node, i = trie.root, 31
        while i >= 0:
            node = node[(a >> i) & 1]
            if node is None:
                break
            steps += 1
            i -= 1
    print(f"  BitTrie: {trie.nodes:,} nodes; nodes visited per lookup, mean"
          f" {steps / len(queries):.1f}, worst 32")

    mine = tables[YourTable]
    l2 = sum(type(x) is list for x in mine.root)
    l3 = sum(type(y) is list for x in mine.root if type(x) is list for y in x)
    one = sum(type(mine.root[a >> 16]) is not list for a in queries)
    print(f"  YourTable: {l2:,} level-2 nodes, {l3} level-3 nodes; {one:,} of"
          f" {len(queries):,} queries answered after 1 index, the rest after 2;"
          f" worst 3")


if __name__ == "__main__":
    main()
