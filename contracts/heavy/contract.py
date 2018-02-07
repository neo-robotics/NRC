from boa.blockchain.vm.Neo.Runtime import Notify, GetTrigger, CheckWitness
from boa.blockchain.vm.Neo.Action import RegisterAction
from boa.blockchain.vm.Neo.TriggerType import Application, Verification

from boa.blockchain.vm.Neo.TransactionType import InvocationTransaction
from boa.blockchain.vm.Neo.Transaction import *

from boa.blockchain.vm.System.ExecutionEngine import GetScriptContainer, GetExecutingScriptHash
from boa.blockchain.vm.Neo.TriggerType import Application, Verification
from boa.blockchain.vm.Neo.Output import GetScriptHash, GetValue, GetAssetId
from boa.blockchain.vm.Neo.Storage import GetContext, Get, Put, Delete

Name = "NEO Robot Communication"
Symbol = "NRC"

InitialSupply = 50000000
MaximumSupply = 100000000
GenerationPerBlock = 100

ADMIN = b'031a6c6fbbdf02ca351745fa86b9ba5a9452d785ac4f7fc2b7548ca2a46c4fcf4a'
FAILED = "FAILED"

def Main(method, args):
    Grow()

    if method == "name":
        return Name

    if method == "symbol":
        return Symbol

    if method == "deploy":
        return Deploy()

    if method == "supply":
        return GetSupply()

    if method == "balance":
        addr = args[0]
        return GetBalance(addr)

    if method == "request":
        addr = args[0]
        amount = args[1]
        return Request(addr, amount)

    if method == "post-geo":
        addr = args[0]
        geolocation = args[1]
        timestamp = args[2]
        return PostGeolocation(addr, geolocation, timestamp)

    if method == "request-geo":
        addr = args[0]
        since = args[1]
        return RequestGeolocations(addr, since)

    return FAILED


def Grow():
    context = GetContext()
    supply = Get(context, "Supply")
    if supply == "":
        return

    if supply >= MaximumSupply:
        return

    supply += GenerationPerBlock
    if supply > MaximumSupply:
        supply = MaximumSupply
    Put(context, "Supply", supply)


def GetSupply():
    context = GetContext()
    supply = Get(context, "Supply")
    if supply == "":
        print("Contract has not been initalized yet!")
        return FAILED

    return supply


def Deploy():
    r = CheckWitness(ADMIN)
    if not r:
        print("No Privilege!")
        return FAILED

    context = GetContext()

    supply = Get(context, "Supply")
    if supply != 0:
        print("Already deployed!")
        return FAILED

    Put(context, "Supply", InitialSupply)
    Put(context, "GeoCnt", 0)
    return True


def GetBalance(addr):
    context = GetContext()

    key = concat("balance/", addr)
    balance = Get(context, key)
    return balance


def Request(addr, amount):
    r = CheckWitness(ADMIN)
    if not r:
        print("No Privilege!")
        return FAILED

    context = GetContext()
    supply = Get(context, "Supply")
    if supply < amount:
        print("Insufficient supply to request!")
        return FAILED

    supply -= amount
    Put(context, "Supply", supply)

    key = concat("balance/", addr)
    balance = Get(context, key)
    balance += amount
    Put(context, key, balance)
    print("Amount requested.")

    return True


def PostGeolocation(addr, geolocation, timestamp):
    r = CheckWitness(addr)
    if not r:
        print("Invalid operation!")
        return FAILED

    context = GetContext()
    cnt = Get(context, "GeoCnt")
    
    key = concat("geo/ts/", cnt)
    Put(context, key, timestamp)

    key = concat("geo/addr/", cnt)
    Put(context, key, addr)

    key = concat("geo/loc/", cnt)
    Put(context, key, geolocation)

    cnt = cnt + 1
    Put(context, "GeoCnt", cnt)

    msg = concat("Geolocation ", geolocation)
    msg = concat(msg, " at ")
    msg = concat(msg, timestamp)
    msg = concat(msg, " is posted.")
    print(msg)

    return True


def Transfer(src, dst, amount):
    r = CheckWitness(src)
    if not r:
        print("Invalid operation!")
        return FAILED

    context = GetContext()

    key = concat("balance/", src)
    balanceSrc = Get(context, key)
    if balanceSrc < amount:
        print("Insufficient balance!")
        return FAILED

    balanceSrc -= amount
    Put(context, key, balanceSrc)

    key = concat("balance/", dst)
    balanceDst = Get(context, key)
    balanceDst += amount
    Put(context, key, balanceDst)

    return True


def RequestGeolocations(addr, since):
    r = CheckWitness(addr)
    if not r:
        print("Operation invalid!")
        return FAILED

    context = GetContext()
    cnt = Get(context, "GeoCnt")

    s = ""
    i = 0
    while i < cnt:
        key = concat("geo/ts/", i)
        ts = Get(context, key)
        if ts < since:
            i = i + 1
            continue

        key = concat("geo/addr/", i)
        poster = Get(context, key)
        r = Transfer(addr, poster, 1)
        if r == FAILED:
            print("Insufficient funds to request geolocations")
            return FAILED

        key = concat("geo/loc/", i)
        loc = Get(context, key)

        msg = concat("Geolocation ", loc)
        msg = concat(msg, " at ")
        msg = concat(msg, ts)
        msg = concat(msg, " is requested.")
        print(msg)

        data = concat(ts, "|")
        data = concat(data, poster)
        data = concat(data, "|")
        data = concat(data, loc)

        s = concat(s, "$*$")
        s = concat(s, data)
        
        i = i + 1

    return s


