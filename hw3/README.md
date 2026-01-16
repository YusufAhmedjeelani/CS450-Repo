# Homework 3: WAR: A Card game


This assignment will require you to write an implementation of a server for a very simple stateful network protocol. You will implement both the server and the client, and they will be expected both to speak the protocol correctly to each other as well as to speak the protocol correctly with our own reference implementation.

#### WAR: A Card game

Hearthstone: Heroes of Warcraft is a cross-platform online card game with “war” in the title. No matter whether using a Mac, PC, iOS, or Android device, anyone can play the game with anyone else. The original card game [war](https://en.wikipedia.org/wiki/War_(card_game)), however, is much simpler than that game (although probably not more popular). For this assignment, we will be programming a cross-platform implementation of the “war” card game server. If you implement the protocol correctly, your code will be able to communicate with any other student’s code regardless of the choice of language.

#### WAR: The simplified rules

The simplified rules for our version of war are as follows: the dealer (server) deals half of the deck, at random, to the two players (clients). Each player “turns over” (sends) one of their cards to the server, and the server responds to each player “win” “lose” or “draw.” Unlike normal war (as this class is about network programming not video game programming), in the event of a tie neither player receives a “point” and play simply moves on to the next round. After all of the cards have been used, play stops and each client knows (based on the number of points they received) whether they won or they lost. Once each player has received the results of 26 rounds, they disconnect.

#### WAR: The message format

All WAR game messages follow the WAR message format. Each type of message has a fixed size, but not all messages are the same size. Each message consist of a one byte “command” followed by either a one byte payload or a 26 byte payload. The command values map as such:

<table class="table table-striped">

<thead>

<tr>

<th>command</th>

<th>value</th>

</tr>

</thead>

<tbody>

<tr>

<td>want game</td>

<td>0</td>

</tr>

<tr>

<td>game start</td>

<td>1</td>

</tr>

<tr>

<td>play card</td>

<td>2</td>

</tr>

<tr>

<td>play result</td>

<td>3</td>

</tr>

</tbody>

</table>

For want game, play card, and play result, the payload is one byte long. For the “want game” message, the “result” should always be the value 0.

For the “game start” message (where the payload is a set of 26 cards), the payload is 26 bytes representing 26 cards. The byte representation of cards are a mapping between each of the 52 cards in a standard deck to the integers [0..51]. Mapping cards follows the suit order clubs, diamonds, hearts, spades, and within each suit, the rank order by value (i.e. 2, 3, 4, … , 10, Jack, Queen, King, Ace). Thus, 0, 1, and 2 map onto 2 of Clubs, 3 of Clubs, 4 of Clubs; 11, 12, 13, and 14 map onto the King of Clubs, the Ace of Clubs, the 2 of Diamonds, and the 3 of Diamonds; and finally 49, 50, and 51 map onto the Queen, King, and Ace of Spades. Note that you cannot compare card values directly to determine the winner of a “war” - you’ll need to write a custom comparison function which maps two different card values onto win, lose, or draw.

When sending a “game start” message, the server sends half of the deck, at random, to each player by sending 26 bytes with the values [0..51] to one player and the remaining 26 to the other player.

When sending a “play card” message, the client sends one byte which represents one of their cards. Which card to send is undefined, but you cannot send the same card twice within the same game.

Within a “play result” message, the one byte payload values map as such:

<table class="table table-striped">

<thead>

<tr>

<th>result</th>

<th>value</th>

</tr>

</thead>

<tbody>

<tr>

<td>win</td>

<td>0</td>

</tr>

<tr>

<td>draw</td>

<td>1</td>

</tr>

<tr>

<td>lose</td>

<td>2</td>

</tr>

</tbody>

</table>

#### WAR: the network protocol

Parallel to the simplified rules, the WAR protocol is as follows. A war server listens for new TCP connections on a given port. It waits until two clients have connected to that port. Once both have connected, the clients send a message containing the “want game” command. If both clients do this correctly, the server responds with a message containing the “game start” command, with a payload containing the list of cards dealt to that client.

After each client has received their half of the deck, the clients send messages including the “play card” message, and set the payload to their chosen card. After the server has received a “play card” message from both clients, it will respond with a “play result” message to both clients, telling each one whether they won or lost. This process continues until each player has sent all of their cards and received all of their play results; after receiving the last play result, the clients disconnect; after sending the last play result, the server also disconnects.

For War v.1, your server and client only need to play one game, and then exit.

#### Template

For this homework, We have provided a code with docstrings and call signatures, but no function bodies. Your job is to complete an implementation of the server program. You are not required to use the functions as declared in the skeleton, but using it would be a good approach. Additionally, we are also providing a sample Wireshark file in the repository for your reference. However, this file has raw TCP data which is a little bit difficult to comprehend at first glance. In order to help you out we have written a Wireshark dissector plugin for WAR protocol so that similar to TCP, Wireshark can dissect WAR protocol as well. In order to use dissector, Open Wireshark->Help->About Wireshark-> Folders-> "Personal Lua Plugins". You should paste the `WAR.lua` file into the folder mentioned in front of "Personal Lua Plugins". You may need to modify server port number as per your usage(I am using 4444).


##### Provided client

The provided python program also implements a client, using the built in python event loop. This client can be run one at a time, so that you could e.g. run two terminals that each run `python war.py client 127.0.0.1 4444`, and as long as you have a server listening on `127.0.0.1:4444`, each client will connect and play a game of war. Upon correct operation, the provided client outputs literally nothing. It does, however, have several log messages in the source.

The built in event loop enables event driven coding without having to write callbacks or use any extra libraries. This allows writing code in a synchronous style that all runs within one thread. 

The provided client will run one client with the argument `client`. It can also run an arbitrary number of clients with the first argument `clients`, and an additional argument that is the number of clients to run. You can use this to stress test your implementation, for instance by launching 1000 clients with the command `python war.py clients 127.0.0.1 444 1000`.

The provided `example_play.pcap` shows the correct run of a single full game played with a correctly functioning server.

The provided `laggy.py` has the same functionality as `war.py`, except that before sending every card, it waits for 1 second. Code which can play multiple games simultaneously are expected to be able to complete full speed `war.py` clients while several `laggy.py` clients are slowly playing their own games on the same server.

#### A short note on logging

Note that the skeleton file sets the global log level to info in the line `logging.basicConfig(level=logging.INFO)`, and various lines use the functions `logging.{debug, info, error}`. It’s good practice to use different log levels to report different types of events within your program. The tldr of log levels is that each log message has a priority, and the log level sets the lowest priority message that will be shown. Python has 5 built in log levels of increasing priority: `DEBUG, INFO, WARNING, ERROR, CRITICAL`. Thus, if you set your log level to `WARNING`, only `WARNING, ERROR, CRITICAL` will be shown. This is good for normal operation, to only report unexpected events. When you are debugging your code, it’s a great idea to set the log level to `DEBUG`, and litter your code with calls to `logging.debug`. In fact, it would be a great idea to add `logging.debug` statements liberally within the provided client code while you are debugging your server.

#### Handling multiple clients

Most servers are only useful if they can serve multiple requests simultaneously. We have several choices for how to serve multiple clients simultaneously. You will get basic credit for handling two clients playing one game, but the remainder of the credit will come from serving multiple games at the same time. It is up to you to choose how to implement such a server. Remember: code examples from the Python standard library documentation is okay to use, but any other code, even a single line, is not ok. If you would like to use a standard library module that is not included in the skeleton code, please ask. Not all of the libraries in the skeleton code are needed - anything unused in there is merely an option.

#### Grading

We will run your server against a few different reference client implementations. If at any time a client sends an _incorrect_ message, your code should close the connection for BOTH clients, but otherwise continue operating.

We will connect to your server with a combination of buggy clients (that either send the wrong thing, don’t send anything, or send something but not enough to kick them or continue), laggy clients, and correctly operating clients. Your server should not exit when anything unexpected happens, but rather close client connections and continue accepting new connections and supporting current games. We have provided implementations of a correctly operating and a laggy but correct client, but it’s up to you to provide incorrectly functioning clients. Incorrect functioning could mean sending the wrong message at the wrong time, sending the same card twice, or sending a card that isn’t one’s own. This version of the war game does not have a “turn timeout,” so if a client connects and doesn’t send anything, it’s okay if the game never finishes.

Any output to `stdout` or `stderr` will not be considered - feel free to send debugging output, the result of each war, etc, to the screen.

Except in exceptional cases, all games should complete in well under **one second**. Any games taking more than one second to complete will be treated as broken / non-functioning. Timing delays artifically introduced into gameplay would of course count as one of these exceptional cases.

#### Scoring

<table class="table table-striped">

<thead>

<tr>

<th>task</th>

<th>points</th>

</tr>

</thead>

<tbody>

<tr>

<td>Successfully run a game of war between two correctly functioning clients</td>

<td>20</td>

</tr>

<tr>

<td>Successfully handle an incorrect functioning client, with one game running</td>

<td>20</td>

</tr>

<tr>

<td>Run multiple games simultaneously using any technique</td>

<td>20</td>

</tr>

<tr>

<td>Run multiple games simultaneously using one thread</td>

<td>20</td>

</tr>

<tr>

<td>Run multiple games simultaneously with buggy clients</td>

<td>20</td>

</tr>

</tbody>

</table>


Files to be modified:
* `war.py`: This file will contain the implementation of the server

* Do not change the arguments to the `war.py` script or the `serve_game` function.







