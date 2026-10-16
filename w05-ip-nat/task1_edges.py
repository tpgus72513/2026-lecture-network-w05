#!/usr/bin/env python3
"""Week 5 · Task 1 — the edge cases --verify does not cover.

    python3 task1_edges.py > out/task1-edges.txt
"""
from task1_forward import ForwardingTable, int_to_ip, network_range, parse_cidr


def show(label, fn, *args):
    try:
        print(f"  {label:<34} -> {fn(*args)}")
    except ValueError as e:
        print(f"  {label:<34} -> rejected: {e}")


print("== R1/R2 parse_cidr rejects")
for cidr in ["10.0.0.0/33", "10.0.0.0/-1", "10.0.0.0", "163.152.6.5/24",
             "256.0.0.0/8", "10.0.0/8"]:
    show(cidr, parse_cidr, cidr)

print("\n== R3 network_range at the edges")
for cidr in ["0.0.0.0/0", "192.168.0.0/30", "192.168.0.0/31",
             "192.168.0.7/32"]:
    show(cidr, network_range, cidr)

print("\n== R4/R5 every entry 10.20.30.70 falls inside, longest first")
t = ForwardingTable()
for cidr, hop in [("0.0.0.0/0", "default-gw"), ("10.0.0.0/8", "campus"),
                  ("10.20.0.0/16", "eng-building"), ("10.20.30.0/24", "lab-floor"),
                  ("10.20.30.64/26", "lab-rack-2"), ("192.168.1.0/24", "home")]:
    t.add(cidr, hop)
for plen, net, hop in t.matches("10.20.30.70"):
    print(f"  /{plen:<3} {int_to_ip(net):<14} -> {hop}")
print(f"  lookup picks -> {t.lookup('10.20.30.70')}")

print("\n== same prefix, same length, twice")
show("add 10.20.30.0/24 lab-floor again", t.add, "10.20.30.0/24", "lab-floor")
show("add 10.20.30.0/24 somewhere-else", t.add, "10.20.30.0/24", "somewhere-else")
print(f"  lookup 10.20.30.10 still -> {t.lookup('10.20.30.10')}")
