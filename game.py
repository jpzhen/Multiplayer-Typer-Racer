import pygame
import socket
import time
from _thread import *
from threading import Event
import pickle

# GLOBAL VARIABLES
# Store players using the playerID as key and the player object as value
playerDict = {}
ready = Event()

# Items for the chat room // Holds messages for the current lobby
playerMsg = ""
msgList = []

# Locks
playerLock = RLock()  # Controls when player objects are changed
mServLock = RLock()  # Controls when player connects with master server


# Player class
# Represents each player connected to a game
class Player(object):
    def __init__(self, addr, playID, points, name, posX, posY):
        self._addr = addr
        self._name = name
        self._playID = playID
        self._points = points
        self._posX = posX
        self._posY = posY
        self._oppoSet = set()
        self._active = 0
        self.lastMsg = ""
        self.sequenceNumber = 0

    def __repr__(self):
        return "Player # %s, %s" % (self._playID, self._active)


# Establishes a connection with a host
def getConnection(port, host='127.0.0.1'):
    time.sleep(.5)
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(("connecting server with port: %s") % (port))
    connection.connect((host, port))
    return connection


# Server handler
# Will talk to the game server and update player's points
def receivePointsFromServer(con):
    while True:
        try:
            # Receive list from server
            data = con.recv(4096)
            idpoints = None
            try:
                idpoints = pickle.loads(data)
            except Exception as exc:
                print ("Error: (%s)" % exc)
            print("Received: ", idpoints)
            # Determine if a new message is attached to this list
            if len(idpoints) > 3:
                if idpoints[3] != "" and int(idpoints[4]) > len(msgList):
                    msgList.append(idpoints[3])

            # Update player points
            with playerLock:
                playerDict[idpoints[0]]._points = idpoints[1]
        except Exception as e:
            print(e)
            break


# Second server handler. Deals with updating the player objects
def handleServer(con):
    while True:
        try:
            # Expecting either a player object or a new message for the chat
            data = con.recv(4096)
            newPlayer = pickle.loads(data)
            if isinstance(newPlayer, Player):  # Determine if this is actually a player object
                if newPlayer._playID not in playerDict:  # A new player -- Let's add him to our list
                    with playerLock:
                        playerDict[newPlayer._playID] = newPlayer  # Add new player
                ready.set()
            elif len(newPlayer) > 3:  # There is a possibility of a message being attached
                # Confirms if this is actually a message
                if newPlayer[3] != "" and int(newPlayer[4]) > len(msgList):
                    msgList.append(newPlayer[3])
        except Exception as e:
            print(e)

            break


# Main operation for game will happen in this class
class game:
    pygame.init()

    # Sets screen size
    displayWidth = 1024
    displayHeight = 426
    screen = pygame.display.set_mode((displayWidth, displayHeight))

    pygame.display.set_caption("Type Race 99")
    clock = pygame.time.Clock()

    # Colors to chose from
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    green = (0, 200, 0)
    bright_red = (255, 0, 0)
    bright_green = (0, 255, 0)
    blue = (0, 0, 255)

    # Fonts to choose from
    font = pygame.font.Font(None, 32)
    bigFont = pygame.font.Font(None, 48)
    smallText = pygame.font.Font("freesansbold.ttf", 20)
    color = pygame.Color('dodgerblue2')

    # Stores the current text box to write
    current_text = ''  # This determines where the user will write too
    player_name = 'default'  # Changed upon registration
    curScreen = "register"  # Which screen are we currently on
    mainServerCon = None  # Used to store connection to main server
    gameServerCon = None  # Used to store connection to game server
    results = {}  # Used for scoreboard results

    # Game object constructor
    def __init__(self):
        # See if we can connect to server.
        # Main logic
        self.main()

    # This controls which scene the user is on
    def main(self):
        while self.curScreen != 'exit':
            self.current_text = ''  # Reset upon switching screens
            if self.curScreen == 'register':
                self.register()
                # connecting to master server
                with mServLock:
                    self.mainServerCon = getConnection(1500)  # Main server normally instantiated to port 1500
                self.mainServerCon.send(self.player_name.encode())
                continue
            elif self.curScreen == 'unregister' or '':
                self.unregister()
                self.curScreen = 'register'  # Redirect user to registration screen
                continue
            elif self.curScreen == 'title' or '':
                self.titleScreen()
                continue
            elif self.curScreen == 'gamelist':
                self.gamelist()
                continue
            elif self.curScreen == 'playerlist':
                self.playerlist()
                continue
            elif self.curScreen == 'makegame':
                self.makegame()
                self.curScreen = 'lobby'
                continue
            elif self.curScreen == 'lobby':
                self.lobby()
                continue
            elif self.curScreen == 'core':
                self.coreGame()
                continue
            elif self.curScreen == 'scoreboard':
                self.scoreBoard()
                continue
            else:
                break
        pygame.quit()
        # Tries to disconnect from the main server
        if self.mainServerCon is not None:
            with mServLock:
                self.mainServerCon.close()
        # Tries to disconnect from the game server
        if self.gameServerCon is not None:
            self.gameServerCon.close()
        quit()

    def register(self):
        # This value determines when to leave this function
        regActive = True
        # Presents the very cool title of our game
        titleText = "Type Racer 99"
        # Sets background image
        Background = self.Background('static/Title2.jpg', [0, 0], self.displayWidth, self.displayHeight)

        text = ""
        while regActive:
            for event in pygame.event.get():
                # User presses X button
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    return
                elif event.type == pygame.KEYDOWN:
                    # Are we currently accepting input?
                    if self.current_text == '':
                        pass
                    # User presses enter
                    elif event.key == pygame.K_RETURN:
                        with playerLock:
                            self.player_name = text
                        self.curScreen = 'title'
                    # User presses backspace
                    elif event.key == pygame.K_BACKSPACE:
                        # Removes one letter from the back of input
                        text = text[:-1]
                    else:
                        # Add letter type unto user input
                        text += event.unicode

            # Check if we need to change screens
            if self.curScreen != 'register':
                return
            # Update background on screen
            Background.setBackground(self.screen)

            # button to click on for signing up
            self.button("register", self.displayWidth / 2, self.displayHeight / 2, 100, 50,
                        self.green, self.bright_green, '', 'Set name')
            # Should we make the text block appear?
            if self.current_text == 'Set name':
                self.textButton(text, self.displayWidth / 2, self.displayHeight * 2 / 3)

            # Print out title
            self.writeText(titleText, int(self.displayWidth / 2 + 50), int(self.displayHeight / 6))
            # Update screen
            pygame.display.flip()
            self.clock.tick(15)
        self.current_text = ''

    # Disconnects the user's connection to master server
    def unregister(self):
        with mServLock:
            if self.mainServerCon is not None:
                self.mainServerCon.close()
                self.mainServerCon = None
        return

    # Starting screen.
    def titleScreen(self):
        # This value determines when to leave this function
        titleActive = True
        # Text to inform user to proceed
        titleText = "Type Racer 99"
        Background = self.Background('static/Title2.jpg', [0, 0], self.displayWidth, self.displayHeight)

        while titleActive:
            for event in pygame.event.get():
                # User presses X button
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    return

            if self.curScreen != 'title':
                return
            Background.setBackground(self.screen)

            # Redirects to MakeGame
            self.button("Make Game", int(self.displayWidth / 2), int(self.displayHeight / 2), 100, 50,
                        self.green, self.bright_green, 'makegame')
            # Redirects to List of Games
            self.button("Join Game", int(self.displayWidth / 2), int(self.displayHeight / 3), 100, 50,
                        self.green, self.bright_green, 'gamelist')
            # Redirects to Unregister/Register Screen
            self.button("Unregister", int(self.displayWidth / 2), int(self.displayHeight * 2 / 3), 100, 50,
                        self.green, self.bright_green, 'unregister')
            # Redirects to player list
            self.button("Players", int(self.displayWidth / 2), int(self.displayHeight * 5 / 6), 100, 50,
                        self.green, self.bright_green, 'playerlist')
            # Exits game
            self.button("Exit", self.displayWidth * 5 / 6, self.displayHeight * 1 / 3, 100, 50,
                        self.red, self.bright_red, 'exit')

            # Print out title
            self.writeText(titleText, int(self.displayWidth / 2 + 50), int(self.displayHeight / 6))
            # Update screen
            pygame.display.flip()
            self.clock.tick(15)
        self.current_text = ''

    # Shows list of servers that we can actively join
    def gamelist(self):
        # Ask server for information
        self.mainServerCon.send("L".encode())
        data = self.mainServerCon.recv(4096)
        # Server sends a list back
        dictFromMS = pickle.loads(data)
        # This value determines when to leave this function
        listActive = True
        titleText = "Type Racer 99"
        # This while loop will continue until user presses enter or s
        Background = self.Background('static/Title2.jpg', [0, 0], self.displayWidth, self.displayHeight)

        while listActive:
            for event in pygame.event.get():
                # User presses X button
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    return

            # Do we need to switch screens?
            if self.curScreen != 'gamelist':
                return
            Background.setBackground(self.screen)

            # Prints out servers as buttons
            # Upon clicking them we will be connected to that server and redirected to it's lobby
            for i, item in enumerate(dictFromMS.keys()):
                self.specialButton(str(i) + ") " + str(dictFromMS[item]), self.displayWidth / 6,
                                   self.displayHeight * (i + 1) / 6, 100, 50,
                                   self.green, self.bright_green, 'lobby', str(item))

            # Redirects to title screen
            self.button("Title", self.displayWidth * 5 / 6, self.displayHeight * 1 / 6, 100, 50,
                        self.green, self.bright_green, 'title')
            # Exits game
            self.button("Exit", self.displayWidth * 5 / 6, self.displayHeight * 1 / 3, 100, 50,
                        self.red, self.bright_red, 'exit')

            # Print out title
            self.writeText(titleText, self.displayWidth / 2 + 50, self.displayHeight / 6)
            # Update screen
            pygame.display.flip()
            self.clock.tick(15)
        self.current_text = ''

    # Prints out a list of all registered players
    def playerlist(self):
        # Ask server for list of players
        self.mainServerCon.send("P".encode())
        # Receive a list of all players
        temp = self.mainServerCon.recv(2048)
        recvPlayerList = pickle.loads(temp)

        # This value determines when to leave this function
        listActive = True
        # Text to inform user to proceed
        titleText = "Type Racer 99"
        # This while loop will continue until user presses enter or s
        Background = self.Background('static/Title2.jpg', [0, 0], self.displayWidth, self.displayHeight)

        while listActive:
            for event in pygame.event.get():
                # User presses X button
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    return

            # Do we need to switch screens?
            if self.curScreen != 'playerlist':
                return
            Background.setBackground(self.screen)

            # Prints out all the current players
            self.writeText("Current Players:", int(self.displayWidth / 6),
                           int(self.displayHeight / 6))
            for i in range(len(recvPlayerList)):
                self.writeText(recvPlayerList[i], int(self.displayWidth / 6),
                               int(self.displayHeight / 6) + 50 * (i + 1))

            # Redirects to title screen
            self.button("Title", self.displayWidth * 5 / 6, self.displayHeight * 1 / 6, 100, 50,
                        self.green, self.bright_green, 'title')
            # Exits game
            self.button("Exit", self.displayWidth * 5 / 6, self.displayHeight * 1 / 3, 100, 50,
                        self.red, self.bright_red, 'exit')

            # Print out title
            self.writeText(titleText, self.displayWidth / 2 + 50, self.displayHeight / 6)
            # Update screen
            pygame.display.flip()
            self.clock.tick(15)
        self.current_text = 'title'

    # Requests server to host a new game session
    def makegame(self):
        self.current_text = ""
        # Ask server to create new game
        self.mainServerCon.send("C".encode())
        msg = self.mainServerCon.recv(1024).decode()
        # Server sends back a port number; Save it to class
        self.gameServerPort = int(msg)
        return  # Redirect to lobby

    # Waiting screen for game
    def lobby(self):
        # Clears previously stored data
        with playerLock:
            ready.clear()
            playerDict.clear()
            msgList.clear()
        # Connect to game
        try:
            self.gameServerCon = getConnection(self.gameServerPort)
        except:
            self.curScreen = 'title'
            return
        self.current_text = ""
        # Send player name
        self.gameServerCon.send(self.player_name.encode())
        # Start receiving new messages about other players
        start_new_thread(handleServer, (self.gameServerCon,))
        text = ""

        # Receive starttime from server
        startTime = self.gameServerCon.recv(128).decode()
        past = float(startTime)
        # This value determines when to leave this function
        lobbyActive = True
        # Text to inform user to proceed
        titleText = "Type Racer 99"
        # This while loop will continue until user presses enter or s
        Background = self.Background('static/Title2.jpg', [0, 0], self.displayWidth, self.displayHeight)

        text = ''
        while lobbyActive:
            present = time.time()
            currentTime = int(present - past)
            for event in pygame.event.get():
                # User presses X button
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    if self.gameServerCon is not None:
                        self.gameServerCon.close()
                    return
                elif event.type == pygame.KEYDOWN:
                    if self.current_text == '':
                        pass
                    # User presses enter
                    elif event.key == pygame.K_RETURN:
                        # Send a chat message to server
                        self.gameServerCon.send(("/M" + text).encode())
                        text = ''
                    # User presses backspace
                    elif event.key == pygame.K_BACKSPACE:
                        # Removes one letter from the back of input
                        text = text[:-1]
                    else:
                        # Add letter type unto user input
                        text += event.unicode

            # User wants to leave
            if self.curScreen != 'lobby':
                return
            # After 30 seconds, start game
            if int(currentTime) > 30:
                self.curScreen = "core"
                return
            Background.setBackground(self.screen)

            # Print out the player's stats text
            if len(playerDict) > 0:
                for i, item in enumerate(sorted(playerDict)):
                    self.writeText(str(i + 1) + ") " + playerDict[item]._name, int(self.displayWidth / 2 + 50),
                                   int(self.displayHeight / 2 + i * 50))
            self.button("Start", self.displayWidth * 1 / 6, self.displayHeight * 5 / 6, 100, 50,
                        self.green, self.bright_green, 'core')
            self.button("Quit", self.displayWidth * 1 / 2, self.displayHeight * 5 / 6, 100, 50,
                        self.red, self.bright_red, 'exit')

            # Gives option to send message in chat
            self.button("Message", self.displayWidth * 5 / 6, self.displayHeight * 5 / 6, 100, 50,
                        self.green, self.bright_green, '', 'Send Message')
            # Shows user what they currently typed in
            if self.current_text == 'Send Message':
                self.textButton(text, self.displayWidth * 5 / 6, self.displayHeight * 2 / 3)
            # Prints out previously sent messages
            for i, msg in enumerate(msgList, start=-len(msgList)):
                self.writeText(msg, int(self.displayWidth * 5 / 6 + 50), int(self.displayHeight * 2 / 3 + i * 20))
            # Print out title
            self.writeText(titleText, int(self.displayWidth / 2 + 50), int(self.displayHeight / 6))
            # Prints timer until game starts
            self.writeText(str(currentTime), 350, int(self.displayHeight * 2 / 3))
            # Update screen
            pygame.display.flip()
            self.clock.tick(15)
        self.current_text = ''

    # Main game logic
    def coreGame(self):
        # Requires connection to game server
        if self.gameServerCon is None:
            self.curScreen = 'title'
            return
        # Waits for players to load in
        if not ready.is_set():
            while not ready.wait(timeout=0.100):
                print("Waiting for server to give us players...")
        # Expecting server to update point values
        start_new_thread(receivePointsFromServer, (self.gameServerCon,))
        # Opens file
        fileDict = []  # Store all the words in the game here
        with open('wordList.txt') as f:
            for line in f:
                fileDict.append(line.rstrip('\n'))
                fileDict.append(' ')

        # Used to determine time elapse
        startTimer = pygame.time.get_ticks()
        # Holds user input
        text = ''
        # Current word to type
        curLetter = fileDict[0][0]

        # Remove first letter of first element
        fileDict[0] = fileDict[0][1:]

        # Counters for words typed
        count = 0
        wordCount = 0
        Background = self.Background('static/Track1.jpg', [0, 0], self.displayWidth, self.displayHeight)

        # Set game to start typing into the game -- not the chat
        self.current_text = 'main'

        # Holds list of player's cars
        cars = []

        for i, player in enumerate(playerDict):
            # make sure i is an index into cars (it is a key for playerDict also)
            cars.insert(i, self.Racecar('static/racecar.png', playerDict[player]._name,
                                        [playerDict[player]._posX, playerDict[player]._posY], 50, 30))

        # Main logic
        while True:
            # Update list of cars
            for i, player in enumerate(playerDict):
                if len(cars) < i + 1:
                    print("adding" + str(i))
                    cars.append(self.Racecar('static/racecar.png', playerDict[player]._name,
                                             [playerDict[player]._posX, playerDict[player]._posY], 50, 30))

            currentTime = (pygame.time.get_ticks() - startTimer) / 1000
            # Game ends after 1 minute
            if currentTime > 60:
                self.popup("Game over")
                # Send user to scoreboard
                self.curScreen = 'scoreboard'
                break
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    return
                elif event.type == pygame.KEYDOWN:
                    # User is playing game
                    if self.current_text == 'main' and curLetter == event.unicode:
                        count += 1
                        wordCount += 1
                        text = ''
                        curLetter = fileDict[0][0]
                        fileDict[0] = fileDict[0][1:]
                        if len(fileDict[0]) == 0:
                            fileDict.remove(fileDict[0])
                            try:
                                self.gameServerCon.send(str(count).encode('utf8'))  # send points over to server
                                wordCount = 0
                            except:
                                print("Connection error!")
                    # User is sending message
                    elif self.current_text == 'Send Message':
                        if event.key == pygame.K_RETURN:
                            self.gameServerCon.send(("/M" + text).encode())
                            self.current_text = 'main'
                            text = ''
                        # User presses backspace
                        elif event.key == pygame.K_BACKSPACE:
                            # Removes one letter from the back of input
                            text = text[:-1]
                        else:
                            # Add letter type unto user input
                            text += event.unicode
                    else:
                        # Add letter type unto user input
                        text = ""
            if self.curScreen != 'core':
                break

            # Prepare objects for the screen
            Background.setBackground(self.screen)

            self.writeText(text, 60, int(self.displayHeight * 5 / 6))

            c_Surf, c_Rect = self.textObj(curLetter, self.bigFont, self.green)
            c_Rect.left = 50
            c_Rect.top = self.displayHeight * 5 / 6 - 10
            self.screen.blit(c_Surf, c_Rect)

            paragraphText = ""
            for x, line in enumerate(fileDict):
                if x > 9:
                    break
                if len(line) < 1:
                    pass
                paragraphText += line + " "
            t_Surf, t_Rect = self.textObj(paragraphText, self.font, self.white)
            t_Rect.left = 75
            t_Rect.top = self.displayHeight * 5 / 6
            self.screen.blit(t_Surf, t_Rect)

            self.writeText(str(currentTime), 350, int(self.displayHeight * 2 / 3))
            self.writeText(str(count), 200, int(self.displayHeight * 2 / 3))

            self.button("Leave", self.displayWidth * 5 / 6, self.displayHeight * 1 / 6, 100, 50,
                        self.green, self.bright_green, 'title')
            self.button("Exit", self.displayWidth * 5 / 6, self.displayHeight * 1 / 3, 100, 50,
                        self.red, self.bright_red, 'exit')

            # Draw the players on the screen using i as an index into cars - see line 452
            for i, player in enumerate(playerDict):
                playerDict[player]._posX = 50 + playerDict[player]._points
                if i < len(cars):
                    cars[i].updatePos(self.screen, playerDict[player]._posX)

            # button to click on for signing up
            self.button("Message", self.displayWidth * 5 / 6, self.displayHeight * 5 / 6, 100, 50,
                        self.green, self.bright_green, '', 'Send Message')
            if self.current_text == 'Send Message':
                self.textButton(text, self.displayWidth * 5 / 6, self.displayHeight * 2 / 3)
            for i, msg in enumerate(msgList, start=-len(msgList)):
                self.writeText(msg, int(self.displayWidth * 5 / 6 + 50),
                               int(self.displayHeight * 2 / 3 + i * 20))

            # Update game
            pygame.display.flip()
            self.clock.tick(30)
        # Send user to scoreboard
        self.curScreen = 'scoreboard'

        # delete self.gameServerCon
        self.gameServerCon.close()
        self.gameServerCon = None

    def scoreBoard(self):
        # Controls the while loop
        scoreboardActive = True

        playerNameText = ['']
        playerResultsText = ['']

        # Update player's statistics
        for i, player in enumerate(playerDict):
            self.results[playerDict[player]._name] = str(playerDict[player]._points)
        scoreList = sorted(self.results, key=self.results.__getitem__, reverse=True)

        # Grabs the player's stats
        for i, item in enumerate(scoreList):
            if self.results[item] == "" or item == "":
                pass
            else:
                pNameText = item
                pResText = self.results[item]
                if len(playerNameText) > i:
                    playerNameText[i] = pNameText
                    playerResultsText[i] = pResText
                else:
                    playerNameText.append(pNameText)
                    playerResultsText.append(pResText)

        Background = self.Background('static/victory.jpg', [0, 0], self.displayWidth, self.displayHeight)
        # Keeps displaying this scene until user asks to leave
        while scoreboardActive:
            for event in pygame.event.get():
                # User presses exit button
                if event.type == pygame.QUIT:
                    self.curScreen = 'exit'
                    return

            if self.curScreen != 'scoreboard':
                return
            Background.setBackground(self.screen)

            # Print out the player's stats text
            self.writeText("Player Name", int(self.displayWidth / 6), int(self.displayHeight / 6), self.font, self.red)
            self.writeText("Letters Typed", int(self.displayWidth / 2), int(self.displayHeight / 6), self.font,
                           self.red)
            self.writeText("Position", int(self.displayWidth * 5 / 6), int(self.displayHeight / 6), self.font, self.red)
            for i in range(len(playerNameText)):
                self.writeText(playerNameText[i], int(self.displayWidth / 6),
                               int(self.displayHeight / 6) + 50 * (i + 1), self.font, self.red)
                self.writeText(playerResultsText[i], int(self.displayWidth / 2),
                               int(self.displayHeight / 6) + 50 * (i + 1), self.font, self.red)
                self.writeText(str(i + 1), int(self.displayWidth * 5 / 6), int(self.displayHeight / 6) + 50 * (i + 1),
                               self.font, self.red)

            self.button("Title", self.displayWidth / 3, self.displayHeight * 2 / 3, 100, 50,
                        self.green, self.bright_green, 'title')
            self.button("Quit", self.displayWidth * 2 / 3, self.displayHeight * 2 / 3, 100, 50,
                        self.red, self.bright_red, 'exit')

            # Update screen
            pygame.display.flip()
            self.clock.tick(15)

    def writeText(self, text, width=200, height=300, t_font=font, t_color=white):
        textToWrite, textRect = self.textObj(text, t_font, t_color)
        textRect.center = (width - 50, height)
        self.screen.blit(textToWrite, textRect)

    def textObj(self, text, t_font, t_color):
        textSurface = t_font.render(text, True, t_color)
        return textSurface, textSurface.get_rect()

    def button(self, text, recvX, y, w, h, startColor, hoverColor, to_next="", set_button=""):
        x = recvX - 50
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        if x + w > mouse[0] > x and y + h > mouse[1] > y:
            pygame.draw.rect(self.screen, hoverColor, (x, y, w, h))
            if click[0] == 1 and to_next != "":
                print("Going to, ", to_next)
                self.curScreen = to_next
                return
            elif click[0] == 1 and set_button != "":
                self.current_text = set_button
                return
        else:
            pygame.draw.rect(self.screen, startColor, (x, y, w, h))

        smallText = pygame.font.Font("freesansbold.ttf", 20)
        textSurf, textRect = self.textObj(text, smallText, self.black)
        textRect.center = ((x + (w / 2)), (y + (h / 2)))
        self.screen.blit(textSurf, textRect)

    def specialButton(self, text, x, y, w, h, startColor, hoverColor, to_next="", set_button=""):
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        if x + w > mouse[0] > x and y + h > mouse[1] > y:
            # BUGBUG needs to properly use int and not float
            pygame.draw.rect(self.screen, hoverColor, (x, y, w, h))
            if click[0] == 1 and to_next != "":
                self.curScreen = to_next
                self.gameServerPort = int(set_button)
                return
            elif click[0] == 1 and set_button != "":
                self.current_text = set_button
                return
        else:
            pygame.draw.rect(self.screen, startColor, (x, y, w, h))

        smallText = pygame.font.Font("freesansbold.ttf", 20)
        textSurf, textRect = self.textObj(text, smallText, self.black)
        textRect.center = ((x + (w / 2)), (y + (h / 2)))
        self.screen.blit(textSurf, textRect)

    def textButton(self, text, recvX=displayWidth / 2, y=displayHeight / 2, w=100, h=50, toMod=None):
        x = recvX - 50
        t_width, t_height = self.font.size(text)
        if t_width < 80:
            pygame.draw.rect(self.screen, self.red,
                             (x, y, w, h))
            self.writeText(text, int(x + w / 2 + 50), int(y + h / 2), self.smallText)
        else:
            pygame.draw.rect(self.screen, self.red,
                             (x - ((t_width + 20) / 2),
                              y, t_width + 20, h))
            self.writeText(text, int(x + 50),
                           int(y + h / 2), self.smallText)
        if toMod is not None:
            toMod = text

    def popup(self, text):
        self.button(text, 200, 100, self.displayWidth / 2 - 25,
                    self.displayHeight / 2, self.green, self.bright_green)
        pygame.display.flip()
        time.sleep(2)

    class Background(pygame.sprite.Sprite):
        def __init__(self, image_file, location, width, height):
            pygame.sprite.Sprite.__init__(self)  # call Sprite initializer
            self.image = pygame.image.load(image_file)
            self.image = pygame.transform.scale(self.image, (width, height))
            self.rect = self.image.get_rect()
            self.rect.left, self.rect.top = location

        def setBackground(self, screen):
            screen.fill((255, 255, 255))
            screen.blit(self.image, self.rect)

    class Racecar(pygame.sprite.Sprite):
        def __init__(self, image_file, username, location, width, height):
            pygame.sprite.Sprite.__init__(self)
            self.image = pygame.image.load(image_file)
            self.image = pygame.transform.scale(self.image, (width, height))
            self.rect = self.image.get_rect()
            self.rect.left, self.rect.top = location
            self.name = username
            self.smallText = pygame.font.Font("freesansbold.ttf", 20)
            self.textSurface = self.smallText.render(username, True, (255, 255, 255))

        def updatePos(self, screen, dx=0):
            t_width, t_height = self.smallText.size(self.name)
            self.rect.left = dx
            text_Rect = self.textSurface.get_rect()
            text_Rect.left = (self.rect.left + self.rect.right) / 2 - t_width / 2
            text_Rect.top = self.rect.top - 30
            screen.blit(self.textSurface, text_Rect)
            screen.blit(self.image, self.rect)


if __name__:
    game = game()
