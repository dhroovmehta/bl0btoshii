# Mootoshi VPS — Security Configuration

**Server:** srv1353416
**OS:** Ubuntu 24.04.3 LTS
**IP:** 187.77.8.89
**Date configured:** 2026-02-20

---

## 1. SSH Key-Only Authentication

**What it does:** Only allows login via SSH key. Password login is completely disabled — no one can brute-force their way in by guessing passwords.

**How it works:**
- Your Mac has a private key (`~/.ssh/id_mootoshi`) that only exists on your machine
- The VPS has the matching public key in `/root/.ssh/authorized_keys`
- When you connect, SSH verifies the pair — no password involved

**Config files changed:**
- `/etc/ssh/sshd_config` → `PasswordAuthentication no`
- `/etc/ssh/sshd_config.d/50-cloud-init.conf` → `PasswordAuthentication no`
- `/etc/ssh/sshd_config` → `PubkeyAuthentication yes`

**How to connect:**
```bash
ssh mootoshi
```
That's it. The SSH config on your Mac (`~/.ssh/config`) maps "mootoshi" to the correct IP, user, and key.

**If you ever lose access:**
- You would need to use your VPS provider's web console (emergency/recovery console) to re-enable password auth or add a new key
- Keep a backup of `~/.ssh/id_mootoshi` somewhere safe (e.g., encrypted USB drive)

---

## 2. UFW Firewall

**What it does:** Blocks ALL incoming traffic except the three ports we need. Think of it as a locked door with only three keyholes.

**Current rules:**

| Port | Protocol | Purpose |
|------|----------|---------|
| 22   | TCP      | SSH (remote access) |
| 80   | TCP      | HTTP (web traffic) |
| 443  | TCP      | HTTPS (secure web traffic) |

Everything else is **denied by default**. Outgoing traffic is allowed (so the server can make API calls, download updates, etc.).

**Useful commands (run on VPS or via `ssh mootoshi`):**
```bash
# Check firewall status
ufw status verbose

# Open a new port (example: port 8080)
ufw allow 8080/tcp comment 'My app'

# Close a port
ufw delete allow 8080/tcp

# See numbered rules (for deletion by number)
ufw status numbered
```

---

## 3. Fail2Ban

**What it does:** Monitors SSH login attempts and automatically bans IP addresses that fail too many times. Stops brute-force attacks dead in their tracks.

**Current settings:**

| Setting | Value | Meaning |
|---------|-------|---------|
| maxretry | 3 | Ban after 3 failed login attempts |
| findtime | 600 | Count failures within a 10-minute window |
| bantime | 3600 | Ban lasts 1 hour |

**Config file:** `/etc/fail2ban/jail.local`

**Useful commands (run on VPS or via `ssh mootoshi`):**
```bash
# Check Fail2Ban status for SSH
fail2ban-client status sshd

# See currently banned IPs
fail2ban-client status sshd | grep "Banned IP"

# Manually unban an IP (e.g., if you accidentally got yourself banned)
fail2ban-client set sshd unbanip YOUR_IP_ADDRESS

# Check Fail2Ban logs
tail -50 /var/log/fail2ban.log
```

---

## Security Summary

| Layer | Protection | Status |
|-------|-----------|--------|
| SSH key-only auth | Eliminates password brute-force attacks | Active |
| UFW firewall | Blocks all ports except 22, 80, 443 | Active |
| Fail2Ban | Auto-bans IPs after 3 failed SSH attempts | Active |

---

## Important Notes

- **SSH key backup:** Your private key lives at `~/.ssh/id_mootoshi` on your Mac. If you lose this file and don't have a backup, you will need your VPS provider's emergency console to regain access.
- **Adding ports:** If you deploy an app on a non-standard port, you must open it in UFW first (`ufw allow PORT/tcp`).
- **Fail2Ban self-lockout:** If you somehow get your own IP banned, wait 1 hour or use the VPS provider's web console to run `fail2ban-client set sshd unbanip YOUR_IP`.
