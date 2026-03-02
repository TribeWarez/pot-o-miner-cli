#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────────
# pot-o-mine-dashboard – Live stats TUI for PoT-O RPC & RPC Gateway Status API
# Uses Status API (status.rpc.gateway.tribewarez.com): /status, /api/live, /api/miners.
# Uses Pot RPC (pot.rpc.gateway.tribewarez.com): /pool, /miners/:pubkey.
# Refresh: 5s or press 'r'. Quit: 'q'.
# Requirements: Python 3 (stdlib only: urllib, json, curses)
# ──────────────────────────────────────────────────────────────────────────────

import os
import sys
import json
import time
import urllib.request
import urllib.error

try:
    import curses
except ImportError:
    sys.stderr.write("curses not available (e.g. Windows). Run with: ./pot-o-mine --status\n")
    sys.exit(1)

# Pot validator RPC (challenges, submit, pool, miner account)
RPC_URL = os.environ.get("POT_RPC_URL", "https://pot.rpc.gateway.tribewarez.com").rstrip("/")
# RPC Gateway Status API (all services status, PoT-O live, miners by device)
STATUS_URL = os.environ.get("POT_STATUS_URL", "https://status.rpc.gateway.tribewarez.com").rstrip("/")
MINER_PUBKEY = os.environ.get("POT_MINER_PUBKEY", "Cycv3ov14zd2dXMUfS2JPMz9r4bpQAPLfQDKxis2tjCg")
REFRESH_SEC = 5
TIMEOUT = 10


def fetch(base_url, path, method="GET", data=None):
    url = base_url + path
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": "HTTP {}: {}".format(e.code, e.reason), "_code": e.code}
    except Exception as e:
        return {"_error": str(e)}


def fetch_pot(path, method="GET", data=None):
    return fetch(RPC_URL, path, method, data)


def fetch_status(path, method="GET", data=None):
    return fetch(STATUS_URL, path, method, data)


def get_gateway_status():
    """GET /status – aggregate status of all RPC services."""
    return fetch_status("/status")


def get_api_live():
    """GET /api/live – aggregate status + PoT-O validator live (challenge, stats, engine, network, miners_by_device)."""
    return fetch_status("/api/live")


def get_api_miners():
    """GET /api/miners – miners by device type (ESP32, native, etc.)."""
    return fetch_status("/api/miners")


def get_pool():
    return fetch_pot("/pool")


def get_peers():
    return fetch_pot("/network/peers")


def get_devices():
    return fetch_pot("/devices")


def get_miner(pubkey):
    if not pubkey:
        return None
    return fetch_pot("/miners/" + urllib.parse.quote(pubkey, safe=""))


def get_pot_status():
    """Fallback: direct Pot RPC /status when Status API /api/live has no PoT-O data."""
    return fetch_pot("/status")


def safe_get(obj, *keys, default="—"):
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return default
    return obj if obj is not None else default


def format_peers(data):
    if isinstance(data, dict) and "_error" in data:
        return [data["_error"]]
    if isinstance(data, dict) and "peers" in data:
        data = data["peers"]
    if isinstance(data, list):
        return [str(p) if not isinstance(p, dict) else json.dumps(p)[:60] for p in data[:20]]
    return [str(data)]


def draw_box(win, y, x, h, w, title=""):
    try:
        win.border("|", "|", "-", "-", "+", "+", "+", "+")
        if title:
            win.addstr(0, 2, " " + title + " ", curses.A_BOLD)
    except curses.error:
        pass


def run_dashboard(stdscr):
    curses.curs_set(0)
    stdscr.timeout(1000)
    last_refresh = 0
    data = {}

    while True:
        now = time.time()
        if now - last_refresh >= REFRESH_SEC:
            data["gateway_status"] = get_gateway_status()
            data["api_live"] = get_api_live()
            data["api_miners"] = get_api_miners()
            data["pool"] = get_pool()
            data["peers"] = get_peers()
            data["devices"] = get_devices()
            data["miner"] = get_miner(MINER_PUBKEY) if MINER_PUBKEY else None
            # Fallback: PoT-O data from direct RPC if /api/live didn't return pot_o
            api_live_raw = data.get("api_live", {})
            pot_o = api_live_raw.get("pot_o") if isinstance(api_live_raw, dict) else None
            if api_live_raw.get("_error") or not (isinstance(pot_o, dict) and ("node_id" in pot_o or "stats" in pot_o)):
                data["pot_status"] = get_pot_status()
            else:
                data["pot_status"] = None
            last_refresh = now

        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key == ord("q") or key == ord("Q"):
            break
        if key == ord("r") or key == ord("R"):
            last_refresh = 0

        h, w = stdscr.getmaxyx()
        stdscr.clear()

        # Title: Gateway Status API + Pot RPC
        title = " PoT-O Dashboard | Status: " + STATUS_URL[:40] + ("..." if len(STATUS_URL) > 40 else "") + " "
        try:
            stdscr.addstr(0, 0, title[: w - 1], curses.A_BOLD | curses.A_REVERSE)
        except curses.error:
            pass

        row = 2

        # ── Gateway: GET /status (all services)
        gs = data.get("gateway_status", {})
        row += 1
        try:
            stdscr.addstr(row, 2, "── Gateway (all services) ──", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        if gs.get("_error"):
            try:
                stdscr.addstr(row, 2, gs["_error"][: w - 4], curses.A_BOLD)
            except curses.error:
                pass
            row += 1
        else:
            ok = gs.get("ok", False)
            summary = gs.get("summary", {})
            up = summary.get("up", 0)
            degraded = summary.get("degraded", 0)
            down = summary.get("down", 0)
            total = summary.get("total", 0)
            try:
                stdscr.addstr(row, 2, "ok: " + str(ok) + "  up: " + str(up) + "  degraded: " + str(degraded) + "  down: " + str(down) + "  total: " + str(total))
            except curses.error:
                pass
            row += 1
            for svc in gs.get("services", [])[:8]:
                sid = svc.get("id", "?")
                name = (svc.get("name") or sid)[:22]
                status_s = svc.get("status", "?")
                lat = svc.get("latency_ms")
                lat_s = str(lat) + "ms" if lat is not None else "—"
                url_s = (svc.get("url") or "")[:36]
                try:
                    stdscr.addstr(row, 2, "  " + sid + " " + status_s + " " + lat_s + "  " + name[: w - 24])
                except curses.error:
                    pass
                row += 1

        # ── PoT-O Live: from /api/live (under "pot_o") or fallback to Pot RPC /status
        row += 1
        api_live_raw = data.get("api_live", {})
        live = (api_live_raw.get("pot_o") if isinstance(api_live_raw.get("pot_o"), dict) else None) or api_live_raw
        if api_live_raw.get("_error") or ("node_id" not in live and "stats" not in live):
            live = data.get("pot_status") or live
        try:
            stdscr.addstr(row, 2, "── PoT-O Validator (live) ──", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        if live.get("_error"):
            try:
                stdscr.addstr(row, 2, live["_error"][: w - 4], curses.A_BOLD)
            except curses.error:
                pass
            row += 1
        else:
            # current_challenge, stats, engine, network, connected_peers, miners_by_device
            node_id = str(safe_get(live, "node_id"))[:28]
            try:
                stdscr.addstr(row, 2, "node_id: " + node_id)
            except curses.error:
                pass
            row += 1
            try:
                stdscr.addstr(row, 2, "difficulty: " + str(safe_get(live, "difficulty")) + "  max_tensor_dim: " + str(safe_get(live, "max_tensor_dim")))
            except curses.error:
                pass
            row += 1
            try:
                stdscr.addstr(row, 2, "peer_network_mode: " + str(safe_get(live, "peer_network_mode")) + "  pool_strategy: " + str(safe_get(live, "pool_strategy")))
            except curses.error:
                pass
            row += 1
            stats = live.get("stats", {})
            try:
                stdscr.addstr(row, 2, "stats: challenges=" + str(safe_get(stats, "total_challenges_issued")) + "  proofs_valid=" + str(safe_get(stats, "total_proofs_valid")))
            except curses.error:
                pass
            row += 1
            engine = live.get("engine", {})
            try:
                stdscr.addstr(row, 2, "engine: tasks=" + str(safe_get(engine, "tasks_processed")) + "  ok=" + str(safe_get(engine, "successful")) + "  failed=" + str(safe_get(engine, "failed")))
            except curses.error:
                pass
            row += 1
            net = live.get("network", {})
            try:
                stdscr.addstr(row, 2, "network: total_nodes=" + str(safe_get(net, "total_nodes")) + "  synced=" + str(safe_get(net, "synced")))
            except curses.error:
                pass
            row += 1
            # current_challenge (id, slot, expires_at, etc.)
            ch = live.get("current_challenge", {})
            if ch:
                try:
                    stdscr.addstr(row, 2, "challenge: id=" + str(ch.get("id", "?"))[:24] + "  slot=" + str(ch.get("slot", "?")))
                except curses.error:
                    pass
                row += 1
            # miners_by_device (counts per device type)
            mbd = live.get("miners_by_device") or (data.get("api_miners") or {}).get("miners_by_device")
            if mbd and isinstance(mbd, dict):
                parts = [k + ":" + str(v.get("count", 0) if isinstance(v, dict) else v) for k, v in mbd.items()]
                try:
                    stdscr.addstr(row, 2, "miners_by_device: " + "  ".join(parts)[: w - 22])
                except curses.error:
                    pass
                row += 1
            # connected_peers
            conn = live.get("connected_peers", [])
            if conn:
                try:
                    stdscr.addstr(row, 2, "connected_peers: " + str(len(conn)))
                except curses.error:
                    pass
                row += 1

        # ── Devices (Pot RPC GET /devices)
        row += 1
        try:
            stdscr.addstr(row, 2, "── Devices ──", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        devices_data = data.get("devices", {})
        if isinstance(devices_data, dict) and devices_data.get("_error"):
            try:
                stdscr.addstr(row, 2, devices_data["_error"][: w - 4], curses.A_BOLD)
            except curses.error:
                pass
        else:
            dev_count = None
            if isinstance(devices_data, dict):
                dev_count = devices_data.get("device_count")
                if dev_count is None and "devices" in devices_data:
                    dev_list = devices_data["devices"]
                    if isinstance(dev_list, list):
                        dev_count = len(dev_list)
                # Public RPC may return miners_by_device only (no device_count)
                if dev_count is None and "miners_by_device" in devices_data:
                    mbd = devices_data["miners_by_device"]
                    if isinstance(mbd, dict):
                        dev_count = sum(
                            (v.get("count") if isinstance(v, dict) else 0) or 0
                            for v in mbd.values()
                        )
            elif isinstance(devices_data, list):
                dev_count = len(devices_data)
            try:
                stdscr.addstr(row, 2, "device_count: " + str(dev_count) if dev_count is not None else "—")
            except curses.error:
                pass
            row += 1

        # ── Pool (from Pot RPC)
        row += 1
        try:
            stdscr.addstr(row, 2, "── Pool ──", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        pool = data.get("pool", {})
        if pool.get("_error"):
            try:
                stdscr.addstr(row, 2, pool["_error"][: w - 4], curses.A_BOLD)
            except curses.error:
                pass
        else:
            try:
                ptype = safe_get(pool, "pool_type") if safe_get(pool, "pool_type") != "—" else safe_get(pool, "type")
                miners = safe_get(pool, "total_miners") if safe_get(pool, "total_miners") != "—" else safe_get(pool, "miners")
                stake = safe_get(pool, "total_stake") if safe_get(pool, "total_stake") != "—" else safe_get(pool, "stake")
                stdscr.addstr(row, 2, "type: " + str(ptype) + "  miners: " + str(miners) + "  stake: " + str(stake) + "  minimum_stake: " + str(safe_get(pool, "minimum_stake")))
            except curses.error:
                pass
        row += 2

        # ── Miner account (Pot RPC; 404 = not on-chain)
        if MINER_PUBKEY:
            try:
                miner_label = (MINER_PUBKEY[:20] + "...") if len(MINER_PUBKEY) > 20 else MINER_PUBKEY
                stdscr.addstr(row, 2, "── Miner (" + miner_label + ") ──", curses.A_BOLD)
            except curses.error:
                pass
            row += 1
            miner = data.get("miner")
            if miner and not miner.get("_error"):
                try:
                    stdscr.addstr(row, 2, json.dumps(miner)[: w - 4])
                except curses.error:
                    pass
            elif miner and miner.get("_error"):
                err = miner["_error"]
                code = miner.get("_code")
                if code == 404 or "404" in str(err):
                    msg = "Not on-chain (miner not yet registered)"
                else:
                    msg = "Error: " + err[: w - 12]
                try:
                    stdscr.addstr(row, 2, msg[: w - 4], curses.A_BOLD)
                except curses.error:
                    pass
            row += 2

        # ── Network Peers
        try:
            stdscr.addstr(row, 2, "── Network Peers ──", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        peers_data = data.get("peers", [])
        if isinstance(peers_data, dict) and peers_data.get("_error"):
            try:
                stdscr.addstr(row, 2, peers_data["_error"][: w - 4], curses.A_BOLD)
            except curses.error:
                pass
        else:
            peers_list = peers_data if isinstance(peers_data, list) else (peers_data.get("peers", []) if isinstance(peers_data, dict) else [])
            for line in format_peers(peers_list)[:6]:
                try:
                    stdscr.addstr(row, 2, line[: w - 4])
                except curses.error:
                    pass
                row += 1
            if not peers_list:
                try:
                    stdscr.addstr(row, 2, "(none or local_only)")
                except curses.error:
                    pass
        row += 2

        # Help
        try:
            stdscr.addstr(h - 1, 2, " [r] refresh  [q] quit  (auto-refresh " + str(REFRESH_SEC) + "s) ", curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()

    return 0


def main():
    try:
        return curses.wrapper(run_dashboard)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
