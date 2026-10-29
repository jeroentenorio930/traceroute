# Traceroute Tool using ICMP

A traceroute implementation in Python built on raw sockets. It maps the hop-by-hop path from your machine to a destination by sending ICMP Echo Requests with an increasing Time-To-Live (TTL), and it enriches every public hop with IP geolocation data (city, region, country, ISP).

**Course:** NSCOM02 (De La Salle University) | **Machine Project:** MCO2 | **Group 4:** Andrea Gayle Garcia, Jeroen Ralph Tenorio

---

## How it works

1. A raw ICMP socket is opened and an Echo Request (type 8) is built by hand: header, timestamp payload, and the Internet checksum. The packet-building and checksum logic reuses what we wrote for the ICMP ping exercise (MCO1).
2. The packet is sent with `TTL = 1`, then `2`, `3`, and so on, up to `MAX_HOPS` (30).
3. Each router that decrements the TTL to zero drops the packet and replies with **ICMP Time Exceeded (type 11)**. The sender of that reply is the hop at that distance.
4. The trace ends when the destination answers with an **Echo Reply (type 0)**. Destination Unreachable (type 3) replies are also handled.
5. For each responding hop, the round-trip time is measured and the IP is looked up for geolocation.

### Defaults

| Setting | Value |
|---|---|
| Max hops | 30 |
| Timeout per probe | 2.0 s |
| Tries per hop | 2 |

Hops that never answer are printed as `* * * Request timed out.` Many routers deliberately ignore ICMP, so gaps in the middle of a trace are normal.

## Geolocation (bonus feature)

Each hop's IP is resolved through the free [ip-api.com](https://ip-api.com/) JSON API.

- **Minimal requests:** only the fields we need are requested (continent, country, region, city, ISP/org), and anything missing is shown as `N/A`.
- **Private IPs are skipped:** the first hops are usually local gateways (`192.168.x.x`, `10.x.x.x`) with no public geolocation. The `ipaddress` module checks `is_private` before any request is made, and these hops are tagged `geo: private/unresolvable`. This avoids wasting API calls.
- **Rate limiting:** the free plan allows 45 requests per minute. A queue of request timestamps (`_geo_request_timestamps`) is kept; entries older than 60 seconds are dropped, and if 45 requests are already in the window the script sleeps exactly until the oldest one expires. A long trace to several hosts therefore never trips the limit.
- **Graceful failure:** network errors, bad responses, and non-success API statuses all fall back to an unresolvable tag instead of crashing the trace.
- **Clean output:** `format_geolocation()` turns the result into a single `[City, Region, Country, Continent | ISP]` string.

## Requirements

- Python 3
- The `requests` library: `pip install requests`
- **Administrator / root privileges.** Raw sockets require elevated rights.
- Internet access (ICMP out, plus HTTP to ip-api.com for geolocation)

Developed and tested on Windows.

## Usage

Run from an elevated terminal.

**Windows** (open Command Prompt or PowerShell as Administrator):

```
py traceroute.py
```

**Linux / macOS:**

```
sudo python3 traceroute.py
```

The target hosts are set at the bottom of `traceroute.py`. To trace a different destination, edit or add a `run_traceroute("your-host.example")` line there:

```python
run_traceroute("google.com")
run_traceroute("dlsu.instructure.com")
run_traceroute("www.dlsu.edu.ph")
run_traceroute("dlsu.edu.ph")
```

If a hostname cannot be resolved, the tool reports it and moves on to the next target:

```
Routing to dlsu.edu.ph
    Could not resolve dlsu.edu.ph: [Errno 11001] getaddrinfo failed
```

## Sample output

Trimmed (first hops omitted). Format: `hop  rtt  address  [location | organization]`.

```
Routing to www.dlsu.edu.ph
 ...
 7 rtt=38 ms 162.158.160.226 [Singapore, North West, Singapore, Asia | Cloudflare, Inc.]
 8 rtt=196 ms 172.69.117.60 [Singapore, North West, Singapore, Asia | Cloudflare, Inc.]
 9 rtt=73 ms 172.69.117.51 [Singapore, North West, Singapore, Asia | Cloudflare, Inc.]
10 rtt=69 ms 104.20.42.168 [Toronto, Ontario, Canada, North America | Cloudflare, Inc.]

Trace complete. Destination reached in 10 hops.
```

## Limitations

- Geolocation reflects where an IP is registered or announced, which is not always where the router physically sits. Treat it as approximate.
- The free ip-api.com tier is served over plain HTTP and is rate limited; the tool only sends public IPs of hops, never your own data.
- Hosts are hardcoded rather than taken from command-line arguments.
- ICMP can be filtered by firewalls and some networks, which will show up as timeouts.

## Tools and AI use

Gemini was used to sanity-check whether the traceroute results we observed were expected network behavior rather than a bug in our code.

## References

- IP-API. *IP geolocation API.* https://ip-api.com/
