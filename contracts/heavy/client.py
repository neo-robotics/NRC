#!/usr/bin/env python3

import sys
import time
import json
import struct
from prompt_toolkit import prompt
from base58 import b58encode

from neo.Settings import settings
from neocore.Cryptography.Crypto import Crypto
from neo.Core.Blockchain import Blockchain
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import LevelDBBlockchain
from neo.Implementations.Wallets.peewee.UserWallet import UserWallet
from neo.Network.NodeLeader import NodeLeader
from neo.Prompt.Commands.Invoke import InvokeContract, TestInvokeContract
from neocore.Fixed8 import Fixed8
from twisted.internet import reactor, task

contract_address = "b7bb3e5e71e848136795d418ab7672a2efd8c852"

class NRCClient:
    def __init__(self, walletPath, walletPwd):
        self.open_wallet(walletPath, walletPwd)
        self.log = True


    def info(self, msg):
        if self.log:
            print(msg)


    def error(self, msg):
        if self.log:
            print(msg)


    def scriptHashToAddrStr(self, h):
        d = chr(settings.ADDRESS_VERSION).encode("UTF-8") + h
        checksum = Crypto.Default().Hash256(d)[:4]
        return b58encode(d + checksum)


    def open_wallet(self, path, pwd):
        try:
            self.Wallet = UserWallet.Open(path, pwd)
            self._walletdb_loop = task.LoopingCall(self.Wallet.ProcessBlocks)
            self._walletdb_loop.start(1)
            print("Wallet %s is opened successfully!" % path)
        except Exception as e:
            print("Could not open wallet: %s" % e)
            sys.exit(1)


    def close_wallet(self):
        if hasattr(self, "Wallet") and self.Wallet:
            path = self.Wallet._path
            self._walletdb_loop.stop()
            self.Wallet = None
            print("Wallet %s is closed." % path)


    def test_invoke_contract(self, method, args=None):
        arguments = [contract_address, method]
        if args is not None:
            arguments.extend(args)

        (tx, fee, results, num_ops) = TestInvokeContract(self.Wallet, arguments)
        if tx is None or results is None or results[0].GetString() == "FAILED":
            self.error("Error testing contract invoke")
            return False

        self.info("Test invoke successful")
        self.info("Total operations: %s " % num_ops)
        self.info("Results %s " % [str(item) for item in results])
        self.info("Invoke TX gas cost: %s " % (tx.Gas.value / Fixed8.D))
        self.info("Invoke TX Fee: %s " % (fee.value / Fixed8.D))
        return [tx, fee, results]


    def invoke_contract(self, tx, fee):
        if not InvokeContract(self.Wallet, tx, fee):
            self.error("Invoke contract failed!")
            return False

        self.info("Invoke successfully!")
        return True


    def getName(self):
        ret = self.test_invoke_contract("name")
        if ret is False:
            self.error("Failed to obtain Name")
            return

        (tx, fee, results) = ret
        print("Name: %s" % results[0].GetString())


    def getSymbol(self):
        ret = self.test_invoke_contract("symbol")
        if ret is False:
            self.error("Failed to obtain Symbol")
            return

        (tx, fee, results) = ret
        print("Symbol: %s" % results[0].GetString())


    def getSupply(self):
        ret = self.test_invoke_contract("supply")
        if ret is False:
            self.error("Failed to obtain Supply")
            return

        (tx, fee, results) = ret
        print("supply: %s" % results[0].GetBigInteger())


    def getBalance(self, addr=None):
        if addr is None:
            addr = self.Wallet.Addresses[0]

        args = ['["%s"]' % addr]
        ret = self.test_invoke_contract("balance", args)
        if ret is False:
            self.error("Failed to obtain balance")
            return

        (tx, fee, results) = ret
        print("balance: %s" % results[0].GetBigInteger())


    def request(self, addr, amount):
        args = ['["%s",%s]' % (addr, amount)]
        ret = self.test_invoke_contract("request", args)
        if ret is False:
            self.error("Failed to request asset!")
            return

        (tx, fee, results) = ret
        if self.invoke_contract(tx, fee):
            print("Requested successfully!")


    def deploy(self):
        ret = self.test_invoke_contract("deploy")
        if ret is False:
            self.error("Failed to Deploy")
            return

        (tx, fee, results) = ret
        if self.invoke_contract(tx, fee):
            print("Deploy successfully!")


    def postGeolocation(self, geoloc):
        addr = self.Wallet.Addresses[0]
        ts = int(time.time() * 1000)
        args = ['["%s","%s",%s]' % (addr, geoloc, ts)]
        ret = self.test_invoke_contract("post-geo", args)
        if ret is False:
            self.error("Failed to post geolocation!")
            return

        (tx, fee, results) = ret
        if self.invoke_contract(tx, fee):
            print("Geolocation posted successfully!")


    def requestGeolocations(self):
        addr = self.Wallet.Addresses[0]
        since = int(1000 * (time.time() - 12*60*60))
        args = ['["%s",%s]' % (addr, since)]
        ret = self.test_invoke_contract("request-geo", args)
        if ret is False:
            self.error("Failed to request geolocations!")
            return

        (tx, fee, results) = ret
        data = results[0].GetByteArray().split(b'$*$')[1:]
        for t in data:
            (ts, owner, loc) = t.split(b'|')
            ts = struct.unpack('Q', ts + b'\x00' * (8 - len(ts)))[0] / 1000.
            tstr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            owner = self.scriptHashToAddrStr(owner)
            (x, y, z) = map(float, loc.decode("UTF-8").replace("$", "").split("_"))
            print("[%s] [%s] <%s, %s, %s>" % (tstr, owner, x, y, z))

#        if self.invoke_contract(tx, fee):
#            print("Geolocations requested successfully!")
#
#        data = results[0].GetString()
#        print(data)


    def prompt(self):
        dbloop = task.LoopingCall(Blockchain.Default().PersistBlocks)
        dbloop.start(0.1)

        while True:
            try:
                command = prompt("$ ")
                args = command.split(" ")
            except EOFError:
                return self.quit()
            except KeyboardInterrupt:
                continue

            if args[0] == "name":
                self.getName()
            elif args[0] == "symbol":
                self.getSymbol()
            elif args[0] == "supply":
                self.getSupply()
            elif args[0] == "deploy":
                self.deploy()
            elif args[0] == "balance-of" and len(args) == 2:
                addr = args[1]
                self.getBalance(addr)
            elif args[0] == "balance" and len(args) == 1:
                self.getBalance()
            elif args[0] == "request" and len(args) == 3:
                addr = args[1]
                amount = args[2]
                self.request(addr, amount)
            elif args[0] == "post-geo" and len(args) == 4:
                x = args[1]
                y = args[2]
                z = args[3]
                geoloc = "$%s_%s_%s" % (x, y, z)
                self.postGeolocation(geoloc)
            elif args[0] == "request-geo" and len(args) == 1:
                self.requestGeolocations()
            elif args[0] == "rebuild":
                self.Wallet.Rebuild()
            elif args[0] == "address":
                print("Address: %s" % self.Wallet.Addresses[0])
            else:
                print("Invalid command: %s" % args[0])
                print("Possible commands are: ")
                print("    name")
                print("    symbol")
                print("    supply")
                print("    balance")
                print("    balance-of")
                print("    request")
                print("    post-geo")
                print("    request-geo")
                print("    rebuild")
                print("    address")


    def quit(self):
        print("Shutting down...")
        Blockchain.Default().Dispose()
        reactor.stop()
        NodeLeader.Instance().Shutdown()


    def run(self):
        NodeLeader.Instance().Start()
        reactor.suggestThreadPoolSize(15)
        reactor.callInThread(self.prompt)
        reactor.run()



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: wallet")
        exit()

    settings.setup_privnet()
    blockchain = LevelDBBlockchain(settings.LEVELDB_PATH)
    Blockchain.RegisterBlockchain(blockchain)

    walletPath = sys.argv[1]
    password = prompt("[Password] ", is_password=True)
    client = NRCClient(walletPath, password)
    client.run()

