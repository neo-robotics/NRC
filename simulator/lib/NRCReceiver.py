#!/usr/bin/env python3

import sys
import time
import struct
import signal
import logging
import json
from socket import *
from base58 import b58encode
from threading import Thread

from neo.Settings import settings
from neocore.Cryptography.Crypto import Crypto
from neo.Core.Blockchain import Blockchain
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import LevelDBBlockchain
from neo.Implementations.Wallets.peewee.UserWallet import UserWallet
from neo.Network.NodeLeader import NodeLeader
from neo.Prompt.Commands.Invoke import InvokeContract, TestInvokeContract
from neo.contrib.smartcontract import SmartContract
from twisted.internet import reactor, task

contract_address = "3c6a0ee4cecadfd6d3fd06fd7e7eedfa6d57dfe1"
smart_contract = SmartContract(contract_address)
    
@smart_contract.on_notify
def sc_notify(event):
    global receiver

    if len(event.event_payload) != 3:
        return

    receiver.addGeo(event.event_payload)


class NRCReceiver:
    def __init__(self, walletPath, walletPwd):
        self.open_wallet(walletPath, walletPwd)
        self.geolocations = []


    def open_wallet(self, path, pwd):
        try:
            self.Wallet = UserWallet.Open(path, pwd)
            self._walletdb_loop = task.LoopingCall(self.Wallet.ProcessBlocks)
            self._walletdb_loop.start(1)
            print("Wallet %s is opened successfully!" % path)
        except Exception as e:
            print("Could not open wallet: %s" % e)
            sys.exit(1)


    def rebuild_wallet(self):
        self.Wallet.Rebuild()


    def wait_contract(self):
        while True:
            contract = Blockchain.Default().GetContract(contract_address)
            if contract is not None:
                print("Contract is ready.")
                break

            print("[%s] Progress: %s/%s" % (settings.net_name, \
                Blockchain.Default().Height, Blockchain.Default().HeaderHeight))
            print("Waiting contract...")
            time.sleep(1)


    def scriptHashToAddrStr(self, h):
        d = chr(settings.ADDRESS_VERSION).encode("UTF-8") + h
        checksum = Crypto.Default().Hash256(d)[:4]
        return b58encode(d + checksum)


    def bytes2timestamp(self, ts):
        bytes8 = ts + b'\x00' * (8 - len(ts))
        ts = struct.unpack('Q', bytes8)[0] / 1000.
        return ts


    def test_invoke_contract(self, method, args=None):
        print("Test invoke...")
        print("method: |%s|" % method)
        print("args: %s" % args)
        arguments = [contract_address, method]
        if args is not None:
            arguments.extend(args)

        (tx, fee, results, num_ops) = TestInvokeContract(self.Wallet, arguments)
        if tx is None or results is None:
            return False

        return [tx, fee, results]


    def invoke_contract(self, tx, fee):
        if not InvokeContract(self.Wallet, tx, fee):
            print("Invoke contract failed!")
            return False

        print("Invoke successfully!")
        return True


    def updateGeolocations(self):
        print("[%s] Progress: %s/%s" % (settings.net_name, \
            Blockchain.Default().Height, Blockchain.Default().HeaderHeight))

        self.geolocations = []
        args = ['["%s",%s]' % (self.Wallet.Addresses[0], 10)]
        ret = self.test_invoke_contract("requestGeo", args)
        if ret is False:
            print("Failed to request geolocations!")
            return


    def addGeo(self, payload):
        [ts, sh, geo] = payload
        ts = self.bytes2timestamp(ts)
        receiver = self.scriptHashToAddrStr(sh)
        (x, y, z) = map(float, geo.decode("UTF-8").replace("$", "").split("_"))
        self.geolocations.append({
            "timestamp": ts, 
            "receiver": receiver, 
            "location": (x, y, z)
        })


    def getGeolocations(self, since):
        self.updateGeolocations()

        geolocs = []
        for loc in self.geolocations:
            if loc["timestamp"] >= since:
                geolocs.append(loc)

        return geolocs


    def requestTicket(self, nBlocks):
        addr = self.Wallet.Addresses[0]
        args = ['["%s",%s]' % (addr, nBlocks)]
        ret = self.test_invoke_contract("requestTicket", args)
        if ret is False:
            print("Failed to request ticket!")
            return False

        (tx, fee, results) = ret
        if not results[0].GetBoolean():
            print("Invoke failed!")
            return False

        if self.invoke_contract(tx, fee):
            print("Ticket requested successfully!")
            return True

        return False


    def quit(self):
        print("Shutting down...")
        Blockchain.Default().Dispose()
        reactor.stop()
        NodeLeader.Instance().Shutdown()


    def run(self):
        dbloop = task.LoopingCall(Blockchain.Default().PersistBlocks)
        dbloop.start(0.1)
        NodeLeader.Instance().Start()
        reactor.suggestThreadPoolSize(15)
        reactor.run(installSignalHandlers=False)


    def runBackground(self):
        t = Thread(target=self.run)
        t.daemon = True
        t.start()


receiver = None

def createReceiver(config, wallet, pwd):
    global receiver

    settings.setup(config)
    blockchain = LevelDBBlockchain(settings.LEVELDB_PATH)
    Blockchain.RegisterBlockchain(blockchain)
    receiver = NRCReceiver(wallet, pwd)
    receiver.runBackground()

    def signalHandler(signal, frame):
        receiver.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signalHandler)

    return receiver


if __name__ == "__main__":
    config = "configs/receiver/protocol.json"
    wallet = "configs/receiver/wallet.db"
    passwd = "nrc123456*"
    receiver = createReceiver(config, wallet, passwd)
    receiver.rebuild_wallet()

    sfd = socket(AF_INET, SOCK_STREAM)
    sfd.bind(("127.0.0.1", 35002))
    sfd.listen(16)

    while True:
        s, addr = sfd.accept()
        data = s.recv(1024).decode("UTF-8")
        try:
            data = json.loads(data)
        except:
            print("Invalid data!")
            s.close()
            continue

        if data["method"] == "requestTicket":
            nBlocks = data["nBlocks"]
            r = receiver.requestTicket(nBlocks)
            msg = json.dumps({"ok": r}).encode("UTF-8")
            s.send(msg)
        elif data["method"] == "requestGeolocations":
            since = data["since"]
            geos = receiver.getGeolocations(since)
            msg = json.dumps(geos).encode("UTF-8")
            s.send(msg)

        s.close()
        receiver.rebuild_wallet()

