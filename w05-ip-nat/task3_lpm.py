#!/usr/bin/env python3
"""Week 5 · Task 3 — Make longest-prefix match fast.

Textbook §4.3.3.

`LinearTable` is correct and it is what you probably wrote in Task 1: keep the
prefixes in a list, check every one, remember the longest that matched. On six
entries that is fine. A real router holds close to a million, and it has to
answer while the packet is still in the buffer.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first: `bench.py` checks every one of your answers against the
linear table. A fast router that forwards to the wrong next hop is not a
router, it is an outage.
"""


class LinearTable:
    """Correct, and slow in the obvious way."""

    def __init__(self):
        self.entries = []                     # (prefix_len, network, next_hop)

    def add(self, network, prefix_len, next_hop):
        self.entries.append((prefix_len, network, next_hop))

    def lookup(self, address):
        best = None
        for plen, net, hop in self.entries:
            mask = (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
            if address & mask == net and (best is None or plen > best[0]):
                best = (plen, hop)
        return best[1] if best else None


class YourTable:
    """Your table. Same three methods, same answers, fewer comparisons.

    Addresses and networks are plain 32-bit ints here - no strings, no parsing,
    so that the benchmark measures your lookup and nothing else.

    Two directions worth knowing about before you pick one:

      * group by prefix length. There are only 33 possible lengths, and you can
        ask them in an order that lets you stop early.
      * walk the address one bit at a time. Each bit takes you to at most one
        child, so the work is bounded by the address width, not by the table size.

    The second is what hardware does. The first is easier and often enough.
    Say which you chose and what it cost you in memory.

    Chosen: a multibit trie with strides 16-8-8, the bit-walk taken 16 then 8
    bits at a time (DIR-24-8 style, but the first level is 2^16 not 2^24).

      level 1   list of 65,536 slots, indexed by address >> 16
      level 2   list of 256 slots, indexed by bits 15-8   (made only under a /16
                that holds a prefix longer than /16)
      level 3   list of 256 slots, indexed by bits 7-0    (only for /25-/32)

    A slot holds either the answer (next hop or None) or the next-level list.
    add() expands a prefix into every slot it covers, and a parallel list
    remembers the prefix length that owns each slot, so a shorter prefix never
    overwrites a longer one whatever order routes arrive in. The longest match
    is settled when the route is added; a lookup is at most three list indexes.
    """

    def __init__(self):
        self.root = [None] * 65536            # level 1 slots
        self.root_len = [-1] * 65536          # prefix length owning each slot
        self.lens = {}                        # id(node) -> its owner lengths

    def child(self, parent, plens, i):
        """The next-level list under parent[i], seeded with the answer already there."""
        slot = parent[i]
        if type(slot) is not list:
            slot = parent[i] = [slot] * 256
            self.lens[id(slot)] = [plens[i]] * 256
        return slot

    def paint(self, node, plens, lo, hi, plen, hop):
        """Give slots lo..hi-1 to this prefix wherever it is the longest so far."""
        for i in range(lo, hi):
            slot = node[i]
            if type(slot) is list:            # a deeper node: paint inside it
                self.paint(slot, self.lens[id(slot)], 0, 256, plen, hop)
            elif plens[i] < plen:             # equal length: first one added wins,
                node[i] = hop                 # as in LinearTable
                plens[i] = plen

    def add(self, network, prefix_len, next_hop):
        root, root_len = self.root, self.root_len
        if prefix_len <= 16:
            lo = network >> 16
            self.paint(root, root_len, lo, lo + (1 << (16 - prefix_len)),
                       prefix_len, next_hop)
            return
        node = self.child(root, root_len, network >> 16)
        node_len = self.lens[id(node)]
        if prefix_len <= 24:
            lo = (network >> 8) & 0xFF
            self.paint(node, node_len, lo, lo + (1 << (24 - prefix_len)),
                       prefix_len, next_hop)
            return
        leaf = self.child(node, node_len, (network >> 8) & 0xFF)
        lo = network & 0xFF
        self.paint(leaf, self.lens[id(leaf)], lo, lo + (1 << (32 - prefix_len)),
                   prefix_len, next_hop)

    def lookup(self, address):
        slot = self.root[address >> 16]
        if type(slot) is list:
            slot = slot[(address >> 8) & 0xFF]
            if type(slot) is list:
                slot = slot[address & 0xFF]
        return slot
