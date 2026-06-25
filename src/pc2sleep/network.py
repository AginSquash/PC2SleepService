"""LAN address detection for HTTP bind (VPN-safe)."""

from __future__ import annotations

import ipaddress
import logging
import socket
import subprocess
import sys

logger = logging.getLogger(__name__)


def _is_usable_lan_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.version != 4:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return False
    if ip in ipaddress.ip_network("169.254.0.0/16"):
        return False
    return ip.is_private


def _windows_lan_addresses() -> list[str]:
    """Enumerate IPv4 addresses on physical/LAN adapters via PowerShell."""
    script = """
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
      Where-Object {
        $_.PrefixOrigin -ne 'WellKnown' -and
        $_.IPAddress -notmatch '^(127\\.|169\\.254\\.)'
      } |
      ForEach-Object {
        $addr = $_.IPAddress
        $alias = $_.InterfaceAlias
        if ($alias -match '(WireGuard|Wintun|Amnezia|AWG|VPN|TAP|TUN|Tailscale|ZeroTier|Loopback|vEthernet|Hyper-V)') {
          return
        }
        $addr
      }
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Failed to enumerate LAN addresses via PowerShell: %s", exc)
        return _fallback_lan_addresses()

    if result.returncode != 0:
        logger.warning(
            "PowerShell LAN enumeration failed: %s",
            result.stderr.strip() or result.stdout.strip(),
        )
        return _fallback_lan_addresses()

    addresses: list[str] = []
    for line in result.stdout.splitlines():
        ip = line.strip()
        if ip and _is_usable_lan_ip(ip):
            addresses.append(ip)

    return _dedupe_preserve_order(addresses)


def _fallback_lan_addresses() -> list[str]:
    """Best-effort LAN IP list without platform-specific APIs."""
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if _is_usable_lan_ip(ip):
                addresses.append(ip)
    except OSError as exc:
        logger.warning("Failed to resolve hostname addresses: %s", exc)

    return _dedupe_preserve_order(addresses)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def get_lan_ipv4_addresses() -> list[str]:
    """Return private IPv4 addresses on non-VPN network adapters."""
    if sys.platform == "win32":
        addresses = _windows_lan_addresses()
    else:
        addresses = _fallback_lan_addresses()

    if not addresses:
        logger.warning("No LAN IPv4 addresses detected")
    else:
        logger.info("Detected LAN IPv4 addresses: %s", ", ".join(addresses))

    return addresses


def resolve_bind_hosts(bind: str) -> list[str]:
    """
    Resolve config bind value to one or more host addresses.

    - ``auto`` — all detected LAN IPs (excludes VPN adapters)
    - ``0.0.0.0`` — all interfaces (may break with active VPN)
    - ``<ipv4>`` — specific address
    """
    value = bind.strip()
    if value == "0.0.0.0":
        return ["0.0.0.0"]
    if value == "auto":
        hosts = get_lan_ipv4_addresses()
        if hosts:
            return hosts
        logger.warning("bind=auto found no LAN addresses, falling back to 0.0.0.0")
        return ["0.0.0.0"]

    ipaddress.ip_address(value)
    return [value]
