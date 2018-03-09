#!/usr/bin/env python3

import os
import sys
import time
import math
import json
import pygame
from socket import *
from threading import Thread

# Settings
GridWidth = 32
GridHeight = 32

addr_sender = ("127.0.0.1", 35001)
addr_receiver = ("127.0.0.1", 35002)

# API for sender
def postGeolocation(timestamp, x, y, z):
    print("Posting (%s, %s, %s) at %s..." % (x, y, z, timestamp))
    s = socket(AF_INET, SOCK_STREAM)
    s.connect(addr_sender)
    msg = json.dumps({
        "timestamp": timestamp, 
        "x": x,
        "y": y,
        "z": z
    }).encode("UTF-8")
    s.send(msg)
    s.close()


# API for receiver
def requestTicket():
    print("Requesting ticket...")
    s = socket(AF_INET, SOCK_STREAM)
    s.connect(addr_receiver)
    msg = json.dumps({
        "method": "requestTicket",
        "nBlocks": 500
    }).encode("UTF-8")
    s.send(msg)

    data = s.recv(1024).decode("UTF-8")
    s.close()
    try:
        ok = json.loads(data)["ok"]
    except:
        print("Invalid data!")
        return False

    return True


def requestGeolocations():
    s = socket(AF_INET, SOCK_STREAM)
    s.connect(addr_receiver)
    msg = json.dumps({
        "method": "requestGeolocations",
        "since": time.time() - 300
    }).encode("UTF-8")
    s.send(msg)

    data = s.recv(40960).decode("UTF-8")
    s.close()
    try:
        geolocations = json.loads(data)
    except:
        print("Invalid data!")
        return []

    return geolocations


def loadMap(path):
    data = open(path).read().split('\n')
    if data[-1] == '':
        data = data[:-1]

    T = int(data[0])

    # generate the Map array
    Map = list(map(list, data[1:]))

    # find out location of sender, receiver and destination
    (W, H) = (len(Map[0]), len(Map))
    locSender = locReceiver = locDestination = None
    for x in range(H):
        for y in range(W):
            if Map[x][y] == 'S':
                locSender = (x, y)
                Map[x][y] = ' '
            elif Map[x][y] == 'R':
                locReceiver = (x, y)
                Map[x][y] = ' '
            elif Map[x][y] == 'D':
                locDestination = (x, y)
                Map[x][y] = ' '

    if locSender is None or \
        locReceiver is None or \
        locDestination is None:
        print("Invalid map!")
        sys.exit(1)

    return (T, Map, locSender, locReceiver, locDestination)


def loadImage(path):
    img = pygame.image.load(path)
    img = pygame.transform.scale(img, (GridWidth, GridHeight))
    return img


def interpolate(coord0, coord1, alpha):
    (x0, y0) = coord0
    (x1, y1) = coord1
    x = (x1 - x0) * alpha + x0
    y = (y1 - y0) * alpha + y0
    return (x, y)


def collisionQ(coord0, coord1):
    (x0, y0) = coord0
    (x1, y1) = coord1
    dist = math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2)
    return dist < 0.5


def willCollide(geolocations):
    global dx
    global dy
    global tLastDetection
    global locDetectedObj0

    if len(geolocations) < 2:
        return False

    # format data (assume 1 sender)
    data = map(lambda g: (g["timestamp"], g["location"]), geolocations)
    data = sorted(data, key = lambda k: k[0])

    # take the last two entries (assume constant speed)
    (g0, g1) = data[-2:]
    (t0, (x0, y0, z0)) = g0
    (t1, (x1, y1, z1)) = g1
    dx = (x1 - x0) / (t1 - t0)
    dy = (y1 - y0) / (t1 - t0)
    locDetectedObj0 = (x1, y1)
    tLastDetection = t1

    # estimate the sender's location at tStart + TSender
    t = tStartSender + TSender - t1
    x2 = x1 + dx * t
    y2 = y1 + dy * t

    # estimate the receiver's location at tStart + TSender
    alpha = (tStartSender + TSender - tStartReceiver) / TReceiver
    (xr, yr) = interpolate(locReceiver0, locDestination, alpha)

    print("sender will at (%s, %s), receiver will at (%s, %s)" % (x2, y2, xr, yr))

    return collisionQ((x2, y2), (xr, yr))


def overDestinationQ():
    alphaSender = (time.time() - tStartSender) / TSender
    alphaReceiver = (time.time() - tStartReceiver) / TReceiver
    return alphaSender > 1.1 and alphaReceiver > 1.1


def draw(img, coordinate):
    (x, y) = coordinate
    X = x * GridHeight
    Y = y * GridWidth
    gameDisplay.blit(img, (Y, X))


def drawMap():
    draw(grassImg, locDestination)
    draw(senderImg, locSender)

    for x in range(H):
        for y in range(W):
            if (x, y) == locDestination:
                continue

            if Map[x][y] == '.':
                draw(wallImg, (x, y))
            elif Map[x][y] == ' ':
                draw(grassImg, (x, y))

    draw(receiverImg, locReceiver)

    if locDetectedObj is not None:
        draw(detectedObjectImg, locDetectedObj)


# Load map and resources
(T, Map, locSender0, locReceiver0, locDestination) = loadMap("configs/map.txt")
(locSender, locReceiver, locDetectedObj) = (locSender0, locReceiver0, None)
locDetectedObj0 = None
TSender = TReceiver = T

wallImg = loadImage("resources/wall.png")
grassImg = loadImage("resources/grass.png")
senderImg = loadImage("resources/car-s.png")
receiverImg = loadImage("resources/car-r.png")
detectedObjectImg = loadImage("resources/detected.png")

# Compute Display Parameters
H = len(Map)
W = len(Map[0])
DisplayHeight = H * GridHeight
DisplayWidth = W * GridWidth

pygame.init()
gameDisplay = pygame.display.set_mode((DisplayWidth, DisplayHeight))
pygame.display.set_caption('NRC Demo: See Through The Wall')
clock = pygame.time.Clock()

tStartSender = tStartReceiver = time.time()
lastUpdatedTime = -1

# Purchase a ticket for receiver
if not requestTicket():
    print("Failed to request ticket!")
    sys.exit(1)

# Wait for the ticket to be included in blockchain
time.sleep(60)

# Run the sender thread
def senderAction():
    global locSender

    t0 = -1
    while True:
        timestamp = time.time()

        alpha = (timestamp - tStartSender) / TSender
        locSender = interpolate(locSender0, locDestination, alpha)
        (x, y) = locSender

        if timestamp - t0 > 30:
            t0 = timestamp
            postGeolocation(timestamp, x, y, 0)

        time.sleep(0.01)


tS = Thread(target=senderAction)
tS.daemon = True
tS.start()

Quit = False
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            Quit = True
            break

    if Quit:
        break

    t = time.time()
    if t - lastUpdatedTime > 30:
        lastUpdatedTime = t
        geos = requestGeolocations()
        if len(geos) > 0:
            print(geos)

        if willCollide(geos):
            print("Collision detected! Lower speed to avoid collision.")
            TReceiver = tStartReceiver + T - t + 20
            tStartReceiver = t
            locReceiver0 = locReceiver[:]
        else:
            print("No collision will occur.")

    # update detected object's location if applicable
    if locDetectedObj0 is not None:
        (xd0, yd0) = locDetectedObj0
        xd1 = xd0 + dx * (t - tLastDetection)
        yd1 = yd0 + dy * (t - tLastDetection)
        locDetectedObj = (xd1, yd1)

    alpha = (t - tStartReceiver) / TReceiver
    locReceiver = interpolate(locReceiver0, locDestination, alpha)

    drawMap()

    pygame.display.update()
    clock.tick(100)

    if collisionQ(locSender, locReceiver):
        print("Accident occured!")
        break

    if overDestinationQ():
        print("Game over!")
        break

time.sleep(10)
pygame.quit()

