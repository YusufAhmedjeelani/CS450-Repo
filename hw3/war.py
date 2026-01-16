"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import _thread
import sys

"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""
Game = namedtuple("Game", ["p1", "p2"])
WAITING = []

class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2

def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return those. If EOF is found
    before numbytes have been received, be sure to account for that here or in
    the caller.
    """
    chunks = []
    remaining = numbytes
    while remaining > 0:
        try:
            chunk = sock.recv(remaining)
        except BlockingIOError:
            continue
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)

def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    # Loop over players and endpints
    for side in (game.p1, game.p2):
        if side is None: # Missing endpoint
            continue
        # Close 
        try:
            if isinstance(side, tuple) and len(side) == 2: # asyncio style tuple
                writer = side[1] # Get writer
                try:
                    writer.close() # Close writer
                    logging.info("Closed writer")
                except Exception:
                    pass

            elif hasattr(side, "close"): # socket style
                try:
                    side.close() # Close socket
                except Exception:
                    pass
        except Exception:
            pass
       
            

def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """
    r1 = card1 % 13 
    r2 = card2 % 13
    if r1 < r2:
        return -1
    if r1 > r2:
        return 1
    return 0

def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    deck = list(range(52))
    random.shuffle(deck)
    return deck[:26], deck[26:]

async def play_one_game(p1, p2):
    #TODO handle single game of war between two clients
    r1, w1 = p1 #Player 1 read write
    r2, w2 = p2 #Player 2 read write

    #Game loop
    try:
        #Wait for players to want game
        (m1, m2) = await asyncio.gather(r1.readexactly(2), r2.readexactly(2))

        #Check valid WANTGAME
        if not (m1[0] == Command.WANTGAME.value and m1[1] == 0):
            logging.error("bad WANTGAME from p1")
            kill_game(Game(r1, r2), (r2, w2))
            return
        if not (m2[0] == Command.WANTGAME.value and m2[1] == 0):
           logging.error("bad WANTGAME from p2")
           kill_game(Game(r1, r2), (r2, w2))
           return

        hand1, hand2 = deal_cards() #Deal cards to players

        # Send GAMESTART and hands
        w1.write(bytes([Command.GAMESTART.value]) + bytes(hand1))
        w2.write(bytes([Command.GAMESTART.value]) + bytes(hand2))
        await asyncio.gather(w1.drain(), w2.drain()) 

        hand1_set, hand2_set = set(hand1), set(hand2)
        used1, used2 = set(), set()

        # Play 26 rounds

        for _ in range(26): 
            # Wait for PLAYCARD from players
            (cmsg1, cmsg2) = await asyncio.gather(r1.readexactly(2), r2.readexactly(2))

            # Check valid PLAYCARD protocol
            if cmsg1[0] != Command.PLAYCARD.value:
                logging.error("expected PLAYCARD from p1")
                kill_game(Game(r1, w1), (r2, w2))
                return
            if cmsg2[0] != Command.PLAYCARD.value:
                logging.error("expected PLAYCARD from p2")
                kill_game(Game(r1, w1), (r2, w2))
                return
            c1, c2 = cmsg1[1], cmsg2[1] #Cards played

            # Validate cards by game rules
            if not (0 <= c1 <= 51):
                logging.error("p1 card out of range: %d", c1)
                kill_game(Game((r1, w1), (r2, w2)))
                return

            if not (0 <= c2 <= 51):
                logging.error("p2 card out of range: %d", c2)
                kill_game(Game((r1, w1), (r2, w2)))
                return

            if c1 not in hand1_set:
                logging.error("p1 played non-hand card: %d", c1)
                kill_game(Game((r1, w1), (r2, w2)))
                return

            if c2 not in hand2_set:
                logging.error("p2 played non-hand card: %d", c2)
                kill_game(Game((r1, w1), (r2, w2)))
                return

            if c1 in used1:
                logging.error("p1 repeated a card: %d", c1)
                kill_game(Game((r1, w1), (r2, w2)))
                return

            if c2 in used2:
                logging.error("p2 repeated a card: %d", c2)
                kill_game(Game((r1, w1), (r2, w2)))
                return

            #Compare cards and send results
            used1.add(c1); used2.add(c2)
            cmpv = compare_cards(c1, c2)  
            if cmpv > 0:
                rsl1, rsl2 = Result.WIN.value,  Result.LOSE.value
            elif cmpv < 0:
                rsl1, rsl2 = Result.LOSE.value, Result.WIN.value
            else:
                rsl1 = rsl2 = Result.DRAW.value

            w1.write(bytes([Command.PLAYRESULT.value, rsl1]))
            w2.write(bytes([Command.PLAYRESULT.value, rsl2]))
            await asyncio.gather(w1.drain(), w2.drain())

    # Handle disconnects and errors
    except (asyncio.IncompleteReadError, ConnectionResetError, OSError, RuntimeError) as e:
        logging.error(f"Game aborted: {e}")
        kill_game(Game((r1, w1), (r2, w2)))
        return


    # Ensure sockets are closed
    finally:
        try:
            w1.close(); w2.close() #Close writers
            await asyncio.gather(w1.wait_closed(), w2.wait_closed())
            kill_game(Game((r1, w1), (r2, w2)))
            return
        except Exception:
            pass

async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername") # Get client address
    logging.info(f"client connected: {peer}")
    # Add to waiting list
    WAITING.append((reader, writer))
    # Start game if more than 2 clients
    if len(WAITING) >= 2:
        p1 = WAITING.pop(0)
        p2 = WAITING.pop(0)
        asyncio.create_task(play_one_game(p1, p2))


async def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    # Use asyncio start_server to handle clients
    server = await asyncio.start_server(handle_client, host, port, backlog=1024)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets) # Get server addresses
    logging.info(f"server listening on {addrs}")
    async with server:
        await server.serve_forever()

async def limit_client(host, port, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port)

async def client(host, port):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "draw"
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch a client/server
    """
    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            asyncio.run(serve_game(host, port))
        except KeyboardInterrupt:
            pass
        return

    if args[0] == "client":
        asyncio.run(client(host, port))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            """
            use `as_completed` to spawn all clients simultaneously
            and collect their results in arbitrary order.
            """
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = asyncio.run(run_all_clients())
        logging.info("%d completed clients", res)

    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1:])
