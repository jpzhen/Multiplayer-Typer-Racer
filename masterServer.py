
import pygame
import socket
from _thread import *
import pickle
import time
import random 
from datetime import datetime
#hold a list of server objects
serverList = []
#hold the port number and number of players
serverDict = {}
#holds all the player names
playerNameList = []
host = "10.156.9.25"
port = 1500
playerLock = RLock()
masterServerLock = RLock()

# Create a object for each player
class Player(object):
    def __init__(self, addr, playID, points, name, posX, posY):
        self._addr = addr
        self._name = name
        self._playID = playID
        self._points = points
        self._posX = posX
        self._posY = posY
        self._oppoSet = set()
        self._active = 1
        self._lastMsg = " "

    def __repr__(self):
        return "Player # %s Player Address %s " % (self._playID, self._addr)


class GameServer(object):
    def __init__(self, port, ipaddr):
        # Global variables to keep track of all players
        self.listOfPlayers = []  # just hold the ip of players. Reducant, too lazy to replace and delete
        self.playerDict = {}  # holds the player object as key and connection (fd) as value
        self.offset = 0
        self.sequenceNum = 0
        self.port = port
        self.ipaddr = ipaddr
        self.conn = None
        self.INTERRUPT = True
        self.serverLock = RLock()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.ipaddr, self.port))
        server.listen(10)
        print("socket is listening")

        # start a new thread to handle the server
        start_new_thread(self.runServer, (server,))
        time.sleep(10)
        # use to lock server
        minPlayer = 1
        while self.INTERRUPT:
            if(len(self.listOfPlayers) < minPlayer):
                self.INTERRUPT = False
        print ('Server is empty, closing session...')
        # Acquire server lock to modify server data
        with self.serverLock:
            del serverDict[self.port]
            serverList.remove(self)
        server.close()

    def updateMainServer(self):
        return [self.port, len(self.listOfPlayers)]

    # Recieve the points player gain and update all other players
    def handleClients(self, conn, addr, player):
        while self.INTERRUPT:
            try:
                # Getting the points
                msg = conn.recv(1024).decode()
                # Modify player object; Acquire the lock
                # Do we need to send a message?
                if len(msg) > 1:
                    if msg[0] == '/' and msg[1] == 'M':
                        with playerLock:
                            self.sequenceNum += 1
                            player._lastMsg = player._name + ": " + msg[2:]
                else:
                    with playerLock:
                            player._points = int(msg)
                # Updating all players
                for key in self.playerDict:
                    msg = pickle.dumps([player._playID, player._points, player._active, player._lastMsg, self.sequenceNum])
                    self.playerDict[key].send(msg)
                    print([player._playID, player._points, player._active, player._lastMsg, self.sequenceNum])
            except:
                print ("Connection broken")
                break

        # When a player close connection, remove them from data structure
        # self.playerDict[player]._active = 0
        for key in self.playerDict:
            try:
                print (([player._playID, player._points, player._active, player._lastMsg, self.sequenceNum]))
                msg = pickle.dumps([player._playID, player._points, player._active, player._lastMsg, self.sequenceNum])
                self.playerDict[key].send(msg)
                print([player._playID, player._points, player._active, player._lastMsg, self.sequenceNum])
            except:
                print("Connection closed by client")
        try:
            conn.close()
        except:
            print("Connection already closed")
        with playerLock:
            del self.playerDict[player]
            self.listOfPlayers.remove(player)
        print("Closing connection with ", addr)

    # Tell the players how many players they are playing against
    def updatePlayers(self):
        count = 0
        for key in self.playerDict.keys():
            for player in self.listOfPlayers:
                if player._playID not in key._oppoSet:
                    try:
                        with playerLock:
                            key._oppoSet.add(player._playID)
                        msg = pickle.dumps(player)
                        self.playerDict[key].send(msg)
                        print("Updating players:", player)
                        count += 1
                        time.sleep(.5)

                    except:
                        print("ERROR AT UPDATEPLAYERS()")
        print(("Updated %d players") % (count))

    # establish the connection and make a thread for each player
    def runServer(self, server):
        # a forever loop until client wants to exit
        past = time.time()
        while self.INTERRUPT:
            try:
                # establish connection with client
                connection, addr = server.accept()
                print("connected with: ", addr[0])

                # receive player name
                name = connection.recv(1024).decode()

                # Send current time
                connection.send(str(past).encode("utf8"))

                # Create player object
                # addr, playID, points, name, posX, posY
                newPlayer = Player(addr[0], addr[1], 0, name, 50, 50 + self.offset)
                self.offset += 50

                # updating data structures
                with playerLock:
                    newPlayer._oppoSet.add(newPlayer._playID)
                    self.playerDict[newPlayer] = connection
                    self.listOfPlayers.append(newPlayer)

                # Send player back their a player object
                msg = pickle.dumps(newPlayer)
                self.playerDict[newPlayer].send(msg)
                print ("New Player:", newPlayer)
                with playerLock:
                    self.updatePlayers()
                print("Player Count: ", len(self.playerDict))

                # Start thread to listen on player progress
                start_new_thread(self.handleClients, (connection, addr, newPlayer))
            except:
                break
        server.close()


def createServer(port):
    server = GameServer(port, host)
    print(("Server with port %s is up") % (port))
    with masterServerLock:
        serverList.append(server)
    #creating the dict
    with masterServerLock:
        serverDict[port] = 0
    start_new_thread(server.start, ())

def getUpdates(argv):
    if len(argv) == 0:
        pass
    else:
        #update the dict
        with masterServerLock:
            serverDict[argv[0]] = argv[1]


def generatePort():
    portNum = random.randint(1500,2000)
    return portNum

def runMainServer(socket):
        # a forever loop until client wants to exit
        while True:
            try:
                # establish connection with client
                connection, addr = socket.accept()
                print("connected with: ", addr[0])
                name = connection.recv(1024).decode()
                with masterServerLock:
                    playerNameList.append(name)
                start_new_thread(handleClient, (connection, addr, name))
            except:
                break
                print("BREAK RUN MAIN SERVER")

def handleClient(con, addr, pname):
    count = 100
    while True:
        try:
            count -= 1
            if (count < 0):
                break
            print("Ready to receive...", count)
            request = con.recv(32).decode()
            print (request)
            #user requesting a list of all games
            if request == "L":
                print("Load Results")
                time.sleep(.2)
                msg = pickle.dumps(serverDict)
                con.send(msg)
            #user requesting to make a game
            elif request == "C":
                servPort = generatePort()
                print("Create Server")
                start_new_thread(createServer, (servPort,))
                #msg = str(servPort).decode()
                con.send(str(servPort).encode('utf8'))
                print (servPort)
            #user requesting a list of all players
            elif request == "P":
                print("Get Player List")
                with masterServerLock:
                    msg = pickle.dumps(playerNameList)
                con.send(msg)
        except:
            print("Closing with: ", addr )
            con.close()
            break
    with masterServerLock:
        playerNameList.remove(pname)
#start_new_thread(self.runServer, (server,))

if __name__:
    openSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    openSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    openSock.bind((host, port))
    openSock.listen(10)
    start_new_thread(runMainServer, (openSock,))

    while True:
        if(len(serverList) > 0):
            for serv in serverList:
                getUpdates (serv.updateMainServer())
                #print(serverDict)
    # while True:
    #     pass
    # print("---MASTER SERVER---")


