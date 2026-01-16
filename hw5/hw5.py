"""
Where solution code to HW5 should be written.  No other files should
be modified.
"""

import socket
import io
import time
import typing
import struct
import homework5
import homework5.logging

HEADERFMT = "!BIIH"   
HEADERSIZE = struct.calcsize(HEADERFMT)

# Packet flag types
DATA = 0
ACK = 1
FINISH = 2
FINISH_ACK = 3

MAX_PAYLOAD = homework5.MAX_PACKET - HEADERSIZE


def makePacket(packetType, seq, ack, payload):
    length = len(payload)
    header = struct.pack(HEADERFMT, packetType, seq, ack, length)
    return header + payload

def checkPacket(raw):
    packetType, seq, ack, length = struct.unpack(HEADERFMT, raw[:HEADERSIZE])
    payload = raw[HEADERSIZE:HEADERSIZE + length]
    return packetType, seq, ack, payload

def updateRTT(RTT, devRTT, sampleRTT):
    alpha = 0.125
    beta = 0.25

    newRTT = (1 - alpha) * RTT + alpha * sampleRTT
    newDevRTT = (1 - beta) * devRTT + beta * abs(sampleRTT - newRTT)
    timeout = newRTT + 4 * newDevRTT

    if timeout < 0.01:
        timeout = 0.01
    if timeout > 2.0:
        timeout = 2.0

    return newRTT, newDevRTT, timeout


def send(sock: socket.socket, data: bytes):
    """
    Implementation of the sending logic for sending data over a slow,
    lossy, constrained network.

    Args:
        sock -- A socket object, constructed and initialized to communicate
                over a simulated lossy network.
        data -- A bytes object, containing the data to send over the network.
    """

    # Naive implementation where we chunk the data to be sent into
    # packets as large as the network will allow, and then send them
    # over the network, pausing half a second between sends to let the
    # network "rest" :)
    logger = homework5.logging.get_logger("hw5-sender")
    
    chunks = []
    offset = 0
    while offset < len(data):
        chunks.append(data[offset:offset + MAX_PAYLOAD])
        offset += MAX_PAYLOAD

    numChunks = len(chunks)
    base = 0              
    nextSeq = 0           
    unackedPackets = {} #Keep track unackedPackets packets             
    #RTT Estimation
    RTT = 0.5    
    devRTT = 0.25
    timeout = RTT + 4 * devRTT # Initial timeout amount
    sock.settimeout(timeout)

    #Sliding window setup
    cwnd = 1.0
    ssthresh = max(2.0, float(numChunks)) 
    rwnd = 2.0

    # Main sending loop
    while base < numChunks:
        #Set send window
        sendWindow = min(int(cwnd), int(rwnd), 2)
        if sendWindow < 1:
            sendWindow = 1

        # Send packets in window 
        while nextSeq < numChunks and len(unackedPackets) < sendWindow:
            payload = chunks[nextSeq]
            pkt = makePacket(DATA, nextSeq, 0, payload)
            sock.send(pkt)
            unackedPackets[nextSeq] = (pkt, time.time())
           # logger.debug("Sent DATA seq=%d (cwnd=%.2f, rwnd=%.2f)",nextSeq, cwnd, rwnd)
            nextSeq += 1

        # Wait for ACK or timeout
        try:
            raw = sock.recv(homework5.MAX_PACKET)
        except socket.timeout:
            #logger.debug("Timeout congestion (cwnd=%.2f)", cwnd)
            ssthresh = max(cwnd / 2.0, 1.0) 
            cwnd = 1.0

            for seq, (pkt, _) in list(unackedPackets.items()):
                sock.send(pkt)
                unackedPackets[seq] = (pkt, time.time())
                #logger.debug("Retransmit DATA seq=%d", seq)
            continue

        #Connection closed and no response
        if not raw:
            return

        packetType, responseSeq, responseAck, _ = checkPacket(raw)

        #ACK received
        if packetType == ACK:
            ackNum = responseAck
            #logger.debug("Got ACK ack=%d (base=%d, nextSeq=%d, cwnd=%.2f)",ackNum, base, nextSeq, cwnd)

            newlyAcked = 0
            # Slide window
            while base <= ackNum and base in unackedPackets:
                _, sendTime = unackedPackets.pop(base)
                sampleRTT = time.time() - sendTime
                RTT, devRTT, timeout = updateRTT(RTT, devRTT, sampleRTT)
                sock.settimeout(timeout)
                base += 1
                newlyAcked += 1

            # Slow start update cwnd
            if newlyAcked > 0:
                if cwnd < ssthresh:
                    cwnd += float(newlyAcked)
                else:
                    cwnd += newlyAcked / cwnd

    # Send FINISH packet
    finSeq = numChunks
    finPkt = makePacket(FINISH, finSeq, 0, b"")

    while True:
        sock.send(finPkt)
        finSendTime = time.time()
        sock.settimeout(timeout)

        try:
            raw = sock.recv(homework5.MAX_PACKET)
        except socket.timeout:
            continue   

        if not raw:
            return

        packetType, responseSeq, responseAck, _ = checkPacket(raw)

        # Check for FINISH_ACK
        if (packetType == FINISH_ACK or packetType == ACK) and responseAck == finSeq:
            sampleRTT = time.time() - finSendTime
            RTT, devRTT, timeout = updateRTT(RTT, devRTT, sampleRTT)
            sock.settimeout(timeout)
            #logger.debug("Got FINISH_ACK/ACK for FINISH seq=%d", finSeq)
            break

    return


def recv(sock: socket.socket, dest: io.BufferedIOBase) -> int:
    """
    Implementation of the receiving logic for receiving data over a slow,
    lossy, constrained network.

    Args:
        sock -- A socket object, constructed and initialized to communicate
                over a simulated lossy network.

    Return:
        The number of bytes written to the destination.
    """
    logger = homework5.logging.get_logger("hw5-receiver")
    
    expectedSeq = 0          
    lastAcked = -1          
    bufferedPackets = {}        
    numBytes = 0

# Main loop
    while True:
        raw = sock.recv(homework5.MAX_PACKET)
        if not raw:
            break

        packetType, seq, ack, payload = checkPacket(raw)

        if packetType == DATA:
            #Re ack received packet
            if seq < expectedSeq:
                if lastAcked >= 0:
                    ackPkt = makePacket(ACK, 0, lastAcked, b"")
                    sock.send(ackPkt)
                continue

            # Store packet in buffer
            if seq not in bufferedPackets:
                bufferedPackets[seq] = payload

            # Deliver in order
            while expectedSeq in bufferedPackets:
                chunk = bufferedPackets.pop(expectedSeq)
                dest.write(chunk)
                numBytes += len(chunk)
                expectedSeq += 1

            # Send last in order ack
            lastAcked = expectedSeq - 1
            if lastAcked >= 0:
                ackPkt = makePacket(ACK, 0, lastAcked, b"")
                sock.send(ackPkt)

        elif packetType == FINISH:
            # Send Finish ACk
            finAckPkt = makePacket(FINISH_ACK, 0, seq, b"")
            sock.send(finAckPkt)
            break

        else:
            continue

    dest.flush()
    return numBytes