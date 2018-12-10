# disable intro message of pygame
import contextlib
with contextlib.redirect_stdout(None):
    import pygame
try:
   import cPickle as pickle
except:
   import pickle
import math
import socket
import threading
import sys
import select
from classes.Player import *
from classes.Arrow import *
from chat import chat_box

# constants
WAITING         = 0
GAME_START      = 1
GAME_END        = 2

WIDTH = 500
HEIGHT = 500

# dictionaries
playerId        = -1
players         = {}
arrows          = {}

# flags and state identifier
connected       = False
player_leap     = False
arrReady        = False
exited          = False
running         = True
gameState       = WAITING

player_sprites  =   [   
                        pygame.Surface((50, 50)),
                        pygame.Surface((50, 50)),
                        pygame.Surface((50, 50)),
                        pygame.Surface((50, 50))
                    ]
arrow_sprites   =   [   
                        pygame.Surface((20, 20)),
                        pygame.Surface((20, 20)),
                        pygame.Surface((20, 20)),
                        pygame.Surface((20, 20))
                    ]
colors          =   [   
                        (255, 0, 0),
                        (0, 255, 0),
                        (0, 0, 255),
                        (0, 255, 255)
                    ]

active_sprite = pygame.Surface((50, 50))
active_sprite.fill((255,255,255))
inactive_sprite = pygame.Surface((50, 50))
inactive_sprite.fill((150,150,150))

for i in range(0,4):
    player_sprites[i].fill(colors[i])
    arrow_sprites[i].fill(colors[i])

# establish connection
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    server_address = (sys.argv[1], 10000)
except IndexError:
    print("Correct usage: python3 main.py <server_ip_address>")
    raise SystemExit
try:
    client_socket.connect(server_address)
except:
    raise SystemExit

def canLevelUp(playerId):
    if players[playerId].xp % 100 == 0:
        return True
    return False

def receiver():
    global exited
    while not exited:
        global connected, playerId, players, arrows, gameState, client_socket
        data = client_socket.recv(4096)
        keyword, data = pickle.loads(data)
        print(keyword)
        if keyword == "CONNECTED":
            if connected == False:
                playerId = data[0]
                connected = True
            players = data[1]
            print("%s connected. player ID: %i" % (players[data[0]].name, data[0]))
        if keyword == "GAME_START":
            gameState = GAME_START
        if keyword == "PLAYER":
            p_id,xpos,ypos = data
            players[p_id].setXPos(xpos)
            players[p_id].setYPos(ypos)
        if keyword == "PLAYER_DIED":
            players[data].playerDied()
        if keyword == "PLAYER_RESPAWNED":
            p_id,xpos,ypos = data
            players[p_id].playerRespawned(xpos,ypos)
        if keyword == "PLAYER_RECOVERED":
            players[data].setStunDuration(0)
        if keyword == "ARROW":
            p_id,xpos,ypos = data
            arrows[p_id].setXPos(xpos)
            arrows[p_id].setYPos(ypos)
        if keyword == "ARROW_ADDED":
            p_id, arrow = data
            arrows[p_id] = arrow
            players[p_id].setArrowCd(True)
        if keyword == "ARROW_HIT":
            p_id,hits,xp,k_id,hp,stunDuration = data
            players[p_id].setHits(hits)
            players[p_id].setXP(xp)
            if canLevelUp(p_id):
                players[p_id].levelUp()
            players[k_id].setHP(hp)
            players[k_id].setStunDuration(stunDuration)
        if keyword == "ARROW_DONE":
            arrows.pop(data)
        if keyword == "ARROW_READY":
            p_id = data
            players[p_id].setArrowCd(False)
        if keyword == "LEAP_CD":
            p_id = data
            players[p_id].setLeapCd(True)
        if keyword == "LEAP_READY":
            p_id = data
            players[p_id].setLeapCd(False)
        if keyword == "GAME_END":
            players = data
            gameState = GAME_END
        if keyword == "UPGRADED_POWER":
            # unpack/retrieve data
            p_id, power, upgrades = data
            # upgrade this player's arrow power
            players[p_id].setPower(power)
            players[p_id].setUpgrades(upgrades)
            # print for debug
            print(str(p_id) + "UP POW: " + str(players[p_id].power))
        if keyword == "UPGRADED_DISTANCE":
            # unpack/retrieve data
            p_id, distance, upgrades = data
            # upgrade this player's arrow distance
            players[p_id].setDistance(distance)
            players[p_id].setUpgrades(upgrades)
            # print for debug
            print(str(p_id) + "UP DST: " + str(players[p_id].distance))
        if keyword == "UPGRADED_SPEED":
            # unpack/retrieve data
            p_id, speed, upgrades = data
            # upgrade this player's arrow speed
            players[p_id].setSpeed(speed)
            players[p_id].setUpgrades(upgrades)
            # print for debug
            print(str(p_id) + " UP SPD: " + str(players[p_id].speed))
        if keyword == "INCREASE_XP":
            p_id, xp = data
            players[p_id].setXP(xp)
            print("{} XP up by {}".format(p_id, xp))
            if canLevelUp(p_id):
                players[p_id].levelUp()
                print("{} level up!".format(p_id))

receiverThread = threading.Thread(target=receiver, name = "receiveThread", args = [])
receiverThread.start()

name = input("Enter name: ")
client_socket.sendall(pickle.dumps(("CONNECT",name),pickle.HIGHEST_PROTOCOL))

pygame.init()

chat_display = chat_box.Chat_Display( font_size = chat_box.DEF_FONTSIZE )
chat_input   = chat_box.Chat_In( 0, HEIGHT, name, chat_display, font_size = chat_box.DEF_FONTSIZE )


screen = pygame.display.set_mode((WIDTH,HEIGHT),pygame.HWSURFACE)
clock = pygame.time.Clock()
chat_box.PYGAME_SCREEN = screen

i = 0
while running:
    if connected:
        if gameState == GAME_START:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    exited = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if players[playerId].isDead():
                        print("You are still dead...")
                        break
                    if players[playerId].isStunned():
                        print("You are still stunned...")
                        break
                    # left click detected
                    if event.button == 1:
                        if arrReady and not players[playerId].arrowOnCd():
                            mouse_x, mouse_y = pygame.mouse.get_pos()
                            client_socket.sendall(pickle.dumps(("ARROW",(playerId,mouse_x,mouse_y)),pickle.HIGHEST_PROTOCOL))
                            arrReady = False
                    # right click detected
                    if event.button == 3:
                        if arrReady:
                            arrReady = False
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        client_socket.sendall(pickle.dumps(("PLAYER",(playerId,mouse_x,mouse_y)),pickle.HIGHEST_PROTOCOL))

                elif event.type == pygame.KEYDOWN:
                    if chat_input.chat_mode:
                        chat_input.handle_event( event )
                        break
                    if players[playerId].isDead():
                        print("You are still dead...")
                        break
                    if players[playerId].isStunned():
                        print("You are still stunned...")
                        break
                    if arrReady and event.key != pygame.K_w:
                        arrReady = False
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_e and not players[playerId].leapOnCd() and not players[playerId].isStunned():
                        client_socket.sendall(pickle.dumps(("LEAP",playerId),pickle.HIGHEST_PROTOCOL))
                    elif event.key == pygame.K_s:
                        client_socket.sendall(pickle.dumps(("STOP",playerId),pickle.HIGHEST_PROTOCOL))
                    elif event.key == pygame.K_w and not players[playerId].isStunned():
                        arrReady = True
                    
                    if players[playerId].upgrades > 0:
                        if event.key == pygame.K_z:
                            # immediately decrement current upgrade points to avoid spamming
                            players[playerId].decreaseUpgrades()
                            # request upgrade from server
                            client_socket.sendall(pickle.dumps(("UPGRADE_POWER", (playerId)), pickle.HIGHEST_PROTOCOL))
                        elif event.key == pygame.K_x:
                            # immediately decrement current upgrade points to avoid spamming
                            players[playerId].decreaseUpgrades()
                            # request upgrade from server
                            client_socket.sendall(pickle.dumps(("UPGRADE_DISTANCE", (playerId)), pickle.HIGHEST_PROTOCOL))
                        elif event.key == pygame.K_c:
                            # immediately decrement current upgrade points to avoid spamming
                            players[playerId].decreaseUpgrades()
                            # request upgrade from server
                            client_socket.sendall(pickle.dumps(("UPGRADE_SPEED", (playerId)), pickle.HIGHEST_PROTOCOL))
                    chat_input.handle_event( event )

            if player_leap:
                player_move = False
                player.leap()
                client_socket.sendall(pickle.dumps(("PLAYER",player),pickle.HIGHEST_PROTOCOL))
                if i==8:
                    player_leap = False
                    i = 0
                i+=1

            # clear screen
            screen.fill((0, 0, 0))
            # repaint player sprites
            for k,v in players.items():
                if v.isDead():
                    continue
                screen.blit(player_sprites[k], (v.getXPos(), v.getYPos()))
            # repaint arrow sprites
            for k,v in arrows.items():
                screen.blit(arrow_sprites[k], (v.getXPos(), v.getYPos()))
            
            if not players[playerId].arrowOnCd():
                screen.blit(active_sprite, (WIDTH-110,HEIGHT-50))
            else:
                screen.blit(inactive_sprite, (WIDTH-110,HEIGHT-50))

            if not players[playerId].leapOnCd():
                screen.blit(active_sprite, (WIDTH-50,HEIGHT-50))
            else:
                screen.blit(inactive_sprite, (WIDTH-50,HEIGHT-50))
        if gameState == GAME_END:
            for k,v in players.items():
                print("%s's score: %d" % (v.getName(),v.getHits()+v.getKills()*2))
    chat_input.update_width()
    chat_input.draw_chat_input()
    chat_display.print_buffer()
    pygame.display.update()
pygame.quit()
sys.exit(0)
