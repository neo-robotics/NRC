#!/usr/bin/env python3

import sys
import time
import struct
import signal
import logging
from prompt_toolkit import prompt
from prompt_toolkit.token import Token
from base58 import b58encode
from threading import Thread
import json
from socket import *

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
    
class NRCSender:
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


    def test_invoke_contract(self, method, args=None):
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


    def postGeolocation(self, ts, x, y, z):
        geoloc = "$%s_%s_%s" % (x, y, z)
        addr = self.Wallet.Addresses[0]
        ts = int(ts * 1000)
        args = ['["%s","%s",%s]' % (addr, geoloc, ts)]
        ret = self.test_invoke_contract("postGeo", args)
        if ret is False:
            print("Failed to post geolocation!")
            return

        (tx, fee, results) = ret
        if not results[0].GetBoolean():
            print("Invoke failed!")
            return

        if self.invoke_contract(tx, fee):
            print("Geolocation posted successfully!")


    def get_bottom_toolbar(self, cli=None):
        out = []
        try:
            out = [(Token.Command, '[%s] Progress: ' % settings.net_name),
                   (Token.Number, str(Blockchain.Default().Height)),
                   (Token.Neo, '/'),
                   (Token.Number, str(Blockchain.Default().HeaderHeight))]
        except Exception as e:
            pass

        return out


    def prompt(self):
        while True:
            try:
                command = prompt("$ ", 
                    get_bottom_toolbar_tokens=self.get_bottom_toolbar,
                    refresh_interval=3
                )
                args = command.split(" ")
            except EOFError:
                return self.quit()
            except KeyboardInterrupt:
                continue

            if len(args) == 3:
                x = args[0]
                y = args[1]
                z = args[2]
                self.postGeolocation(time.time(), x, y, z)
            elif len(args) == 1 and args[0] == "rebuild":
                self.Wallet.Rebuild()
            else:
                print("Format should be: x y z")


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
        # reactor.callInThread(self.prompt)
        reactor.run(installSignalHandlers=False)


    def runBackground(self):
        t = Thread(target=self.run)
        t.daemon = True
        t.start()


sender = None

def createSender(config, wallet, pwd):
    global sender

    settings.setup(config)
    blockchain = LevelDBBlockchain(settings.LEVELDB_PATH)
    Blockchain.RegisterBlockchain(blockchain)
    sender = NRCSender(wallet, pwd)

    def signalHandler(signal, frame):
        sender.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signalHandler)
    sender.runBackground()
    return sender


if __name__ == "__main__":
    config = "configs/sender/protocol.json"
    wallet = "configs/sender/wallet.db"
    passwd = "nrc123456*"
    sender = createSender(config, wallet, passwd)

    sfd = socket(AF_INET, SOCK_STREAM)
    sfd.bind(("127.0.0.1", 35001))
    sfd.listen(10)

    while True:
        s, addr = sfd.accept()
        data = s.recv(1024).decode("UTF-8")
        s.close()
        try:
            d = json.loads(data)
        except:
            print("Invalid data!")
            continue

        timestamp = d["timestamp"]
        (x, y, z) = [d[k] for k in ("x", "y", "z")]
        sender.postGeolocation(timestamp, x, y, z)
        sender.rebuild_wallet()

