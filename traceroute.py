from socket import *
import os
import sys
import struct
import time
import select
import binascii
import ipaddress
import requests

ICMP_ECHO_REQUEST = 8
MAX_HOPS = 30
TIMEOUT = 2.0
TRIES = 2
# The packet that we shall send to each router along the path is the ICMP echo
# request packet, which is exactly what we had used in the ICMP ping exercise.
# We shall use the same packet that we built in the Ping exercise

# --- bonus variables ---
GEO_API_URL = "http://ip-api.com/json/{}"
GEO_RATE_LIMIT = 45
GEO_FIELDS = "status,message,continent,country,regionName,city,isp,org,query"
_geo_request_timestamps = []

def checksum(string):
# In this function we make the checksum of our packet
# hint: see icmpPing lab
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = string[count+1] * 256 + string[count] #removed ord
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
    if countTo < len(string):
        csum = csum + string[len(string) - 1] # removed ord 
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def build_packet():
# In the sendOnePing() method of the ICMP Ping exercise ,firstly the header of our
# packet to be sent was made, secondly the checksum was appended to the header and
# then finally the complete packet was sent to the destination.

    # Make the header in a similar way to the ping exercise.
    # Append checksum to the header.

    checkSum = 0
    pID = os.getpid() & 0xFFFF

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, checkSum, pID, 1)
    data = struct.pack("d", time.time())

    checkSum = checksum(header + data)

    if sys.platform == 'darwin':
        checkSum = htons(checkSum) & 0xffff
    else:
        checkSum = htons(checkSum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, checkSum, pID, 1)

    # Don’t send the packet yet , just return the final packet in this function.
    # So the function ending should look like this
    packet = header + data
    return packet

# start --- bonus functions ---
def _respect_rate_limit():
    now = time.time()

    while _geo_request_timestamps and now - _geo_request_timestamps[0] > 60:
        _geo_request_timestamps.pop(0)

    if len(_geo_request_timestamps) >= GEO_RATE_LIMIT:
        sleep = 60 - (now - _geo_request_timestamps[0]) + 0.1
        if sleep > 0:
            print(f"    (pausing {sleep:.1f}s to respect ip-api.com rate limit)")
            time.sleep(sleep)

def get_geolocation(ip_address):
    try:
        if ipaddress.ip_address(ip_address).is_private:
            return None
    except ValueError:
        return None

    _respect_rate_limit()

    try:
        _geo_request_timestamps.append(time.time())
        response = requests.get(
            GEO_API_URL.format(ip_address),
            params={"fields": GEO_FIELDS},
            timeout=3
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None
    except ValueError:
        return None

    if data.get("status") != "success":
        return None

    return {
        "city": data.get("city") or "N/A",
        "region": data.get("regionName") or "N/A",
        "country": data.get("country") or "N/A",
        "continent": data.get("continent") or "N/A",
        "org": data.get("isp") or data.get("org") or "N/A",
    }

def format_geolocation(geo):
    if geo is None:
        return "geo: private/unresolvable"
    return f"{geo['city']}, {geo['region']}, {geo['country']}, {geo['continent']} | {geo['org']}"

# end --- bonus functions ---

def get_route(hostname):
    timeLeft = TIMEOUT
    for ttl in range(1,MAX_HOPS):
        for tries in range(TRIES):
            destAddr = gethostbyname(hostname)
            #Fill in start
            # Make a raw socket named mySocket

            icmp = getprotobyname("icmp")
            mySocket = socket(AF_INET, SOCK_RAW, icmp)

            #Fill in end

        
            mySocket.setsockopt(IPPROTO_IP, IP_TTL, struct.pack('I', ttl))
            mySocket.settimeout(TIMEOUT)
            try:
                d = build_packet()
                mySocket.sendto(d, (hostname, 0))
                t= time.time()
                startedSelect = time.time()
                whatReady = select.select([mySocket], [], [], timeLeft)
                howLongInSelect = (time.time() - startedSelect)
                
                if whatReady[0] == []: # Timeout
                    print(" * * * Request timed out.")
                recvPacket, addr = mySocket.recvfrom(1024)
                timeReceived = time.time()
                timeLeft = timeLeft - howLongInSelect
                
                if timeLeft <= 0:
                    print(" * * * Request timed out.")
            
            except timeout:
                continue

            else:
                #Fill in start
                #Fetch the icmp type from the IP packet

                icmp_header = recvPacket[20:28]
                types, code, checkSum, pID, sequence = struct.unpack("bbHHh", icmp_header)


                #Fill in end
                if types == 11:
                    bytes = struct.calcsize("d")
                    timeSent = struct.unpack("d", recvPacket[28:28 + bytes])[0]
                    geo_info = format_geolocation(get_geolocation(addr[0]))
                    print(" %d rtt=%.0f ms %s [%s]" %(ttl, (timeReceived -t)*1000, addr[0], geo_info))
                    break

                elif types == 3:
                    bytes = struct.calcsize("d")
                    timeSent = struct.unpack("d", recvPacket[28:28 + bytes])[0]
                    geo_info = format_geolocation(get_geolocation(addr[0]))
                    print(" %d rtt=%.0f ms %s [%s]" %(ttl, (timeReceived-t)*1000, addr[0], geo_info))
                    break
                    
                elif types == 0:
                    bytes = struct.calcsize("d")
                    timeSent = struct.unpack("d", recvPacket[28:28 + bytes])[0]
                    geo_info = format_geolocation(get_geolocation(addr[0]))
                    print(" %d rtt=%.0f ms %s [%s]" %(ttl, (timeReceived - timeSent)*1000, addr[0], geo_info))
                    print("\nTrace complete. Destination reached in %d hops." % ttl)
                    return
                    
                else:
                    print("error")
                    break

            finally:
                mySocket.close()

    print("\nTrace complete. Maximum of %d hops reached without finding the destination." % MAX_HOPS)

def run_traceroute(hostname):
    print(f"\nRouting to {hostname}")
    try:
        get_route(hostname)
    except gaierror as e:
        print(f"    Could not resolve {hostname}: {e}")

run_traceroute("google.com")
run_traceroute("dlsu.instructure.com")
run_traceroute("www.dlsu.edu.ph")
run_traceroute("dlsu.edu.ph")