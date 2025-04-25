from socket import *           # Import all socket functions (e.g., socket(), gethostbyname(), etc.)
import os                      # For getting process ID
import sys                     # For checking platform (e.g., Darwin/Mac)
import struct                  # For packing/unpacking binary data
import time                    # For timestamps and sleep
import select                  # For waiting on a socket with a timeout

ICMP_ECHO_REQUEST = 8          # ICMP type code for echo request packets (ping)

def checksum(source_bytes):
    """
    Compute the Internet Checksum of the supplied bytes.
    This function works correctly in Python 3.
    """
    csum = 0
    countTo = (len(source_bytes) // 2) * 2
    count = 0

    # Handle two bytes at a time
    while count < countTo:
        thisVal = source_bytes[count + 1] * 256 + source_bytes[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count += 2

    # Handle last byte if odd length
    if countTo < len(source_bytes):
        csum += source_bytes[-1]
        csum = csum & 0xffffffff

    # Final fold and complement
    csum = (csum >> 16) + (csum & 0xffff)
    csum += (csum >> 16)
    answer = ~csum & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)  # Swap bytes
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    """
    Wait for a ping reply from the socket.
    Match by packet ID.
    """
    timeLeft = timeout
    while True:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = time.time() - startedSelect

        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # ICMP header is after the first 20 bytes (IP header)
        icmpHeader = recPacket[20:28]
        type, code, checksum_recv, packetID, sequence = struct.unpack("bbHHh", icmpHeader)

        if packetID == ID:
            # Match found — extract the sent time from the payload
            timeSent = struct.unpack("d", recPacket[28:28 + 8])[0]
            rtt = (timeReceived - timeSent) * 1000  # Round-trip time in ms
            return f"Reply from {addr[0]}: time={rtt:.2f}ms"

        timeLeft -= howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    """
    Create and send one ICMP ECHO_REQUEST packet.
    """
    myChecksum = 0
    # Build ICMP header: type (8), code (0), checksum (0), ID, sequence number (1)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    # Payload is the current time as a double (8 bytes)
    data = struct.pack("d", time.time())
    # Compute checksum on header + data
    myChecksum = checksum(header + data)

    if sys.platform == 'darwin':
        myChecksum = htons(myChecksum) & 0xffff  # On macOS
    else:
        myChecksum = htons(myChecksum)           # On Linux/other

    # Final header with correct checksum
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    # Send packet to the destination address, port is irrelevant for ICMP
    mySocket.sendto(packet, (destAddr, 1))

def doOnePing(destAddr, timeout):
    """
    High-level function to perform one ping and return result.
    """
    icmp = getprotobyname("icmp")  # Get protocol number for ICMP (usually 1)
    mySocket = socket(AF_INET, SOCK_RAW, icmp)  # Create raw socket
    myID = os.getpid() & 0xFFFF                # Use process ID for packet ID

    sendOnePing(mySocket, destAddr, myID)      # Send one ping
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)  # Wait for reply

    mySocket.close()
    return delay

def ping(host, timeout=1):
    """
    Repeatedly ping a host once and return the response (break after one for now).
    """
    dest = gethostbyname(host)  # Resolve hostname to IP address
    print("Pinging " + dest + " using Python:")
    print("")

    delay = doOnePing(dest, timeout)  # Single ping
    print(delay)
    time.sleep(1)
    return delay

if __name__ == "__main__":
    # Four websites representing different continents
    continents = {
        "asia": "www.riken.jp",
        "europe": "www.cam.ac.uk",
        "north_america": "www.nrc-cnrc.gc.ca",
        "australia": "www.abc.net.au"
    }

    for key, value in continents.items():
        print("Ping {}: {}".format(key, value))
        ping(value)
