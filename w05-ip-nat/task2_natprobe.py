#!/usr/bin/env python3
"""Week 5 · Task 2 A5 — how many NATs are between this machine and the internet?

    python3 task2_natprobe.py "home Wi-Fi" >> out/nat-evidence.txt

Two independent pieces of evidence, both raw:

  1. traceroute to 8.8.8.8. Every NAT box is a router, so it shows up as a hop.
     Private (RFC 1918) or shared (100.64.0.0/10, RFC 6598) hops after the first
     one mean another layer of private addressing - another NAT - upstream.
  2. UPnP IGD GetExternalIPAddress: ask the home router for the address on its
     WAN side. If that equals the public address the outside world saw, the
     router's NAT is the only one. If it is private or 100.64/10, there is a
     carrier NAT above it. Phones and campus networks usually do not answer.
"""
import datetime, platform, re, socket, subprocess, sys, urllib.request
from urllib.parse import urljoin


def sh(*cmd, timeout=90):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        for enc in ("utf-8", "cp949"):
            try:
                return r.stdout.decode(enc)
            except UnicodeDecodeError:
                pass
        return r.stdout.decode("latin-1")
    except Exception as e:
        return f"<failed: {e}>"


def traceroute(target="8.8.8.8", hops=8):
    if platform.system() == "Windows":
        return sh("tracert", "-d", "-h", str(hops), "-w", "1000", target)
    return sh("traceroute", "-n", "-m", str(hops), "-w", "1", target)


def upnp_external_ip():
    """SSDP M-SEARCH for an Internet Gateway Device, then one SOAP call."""
    msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
           'MAN: "ssdp:discover"\r\nMX: 2\r\n'
           "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(msg.encode(), ("239.255.255.250", 1900))
    try:
        reply, (who, _) = s.recvfrom(4096)
    except socket.timeout:
        return "no UPnP gateway answered"
    finally:
        s.close()
    loc = re.search(rb"(?i)location:\s*(\S+)", reply)
    if not loc:
        return f"{who} answered without a LOCATION header"
    loc = loc.group(1).decode()
    desc = urllib.request.urlopen(loc, timeout=5).read().decode("utf-8", "replace")
    for svc in ("WANIPConnection:1", "WANIPConnection:2", "WANPPPConnection:1"):
        m = re.search(r"urn:schemas-upnp-org:service:" + svc + r".*?<controlURL>(.*?)</controlURL>",
                      desc, re.S)
        if m:
            break
    else:
        return f"{who} ({loc}) has no WAN connection service"
    urn = "urn:schemas-upnp-org:service:" + svc
    body = ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
            ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            f'<u:GetExternalIPAddress xmlns:u="{urn}"/></s:Body></s:Envelope>')
    req = urllib.request.Request(urljoin(loc, m.group(1)), data=body.encode(), headers={
        "Content-Type": 'text/xml; charset="utf-8"',
        "SOAPAction": f'"{urn}#GetExternalIPAddress"'})
    xml = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", "replace")
    ext = re.search(r"<NewExternalIPAddress>(.*?)</NewExternalIPAddress>", xml)
    return (f"gateway {who} ({svc}) says its WAN address is "
            f"{ext.group(1) if ext else '<none in reply>'}")


def public_address():
    return sh("curl", "-s", "--max-time", "10", "https://api.ipify.org").strip()


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "unlabelled"
    print(f"===== {label}  ({datetime.datetime.now():%Y-%m-%d %H:%M})")
    print(f"public address seen from outside: {public_address()}")
    try:
        print(f"UPnP: {upnp_external_ip()}")
    except Exception as e:
        print(f"UPnP: failed - {e!r}")
    print("traceroute to 8.8.8.8:")
    print(traceroute().strip())
    print()
