from boa.blockchain.vm.Neo.Runtime import Notify, GetTrigger, CheckWitness
from boa.blockchain.vm.Neo.Action import RegisterAction
from boa.blockchain.vm.Neo.TriggerType import Application, Verification

from boa.blockchain.vm.Neo.TransactionType import InvocationTransaction
from boa.blockchain.vm.Neo.Transaction import *

from boa.blockchain.vm.System.ExecutionEngine import GetScriptContainer, GetExecutingScriptHash
from boa.blockchain.vm.Neo.TriggerType import Application, Verification
from boa.blockchain.vm.Neo.Output import GetScriptHash, GetValue, GetAssetId
from boa.blockchain.vm.Neo.Storage import GetContext, Get, Put, Delete
from boa.blockchain.vm.Neo.Blockchain import GetHeight

Name = "NEO Robot Communication"
Symbol = "NRC"
Decimals = 0

InitialSupply = 50000000
MaximumSupply = 100000000
GenerationPerBlock = 100
FeePerBlock = 10

OnTransfer = RegisterAction('transfer', 'addr_from', 'addr_to', 'amount')

ADMIN = b'031a6c6fbbdf02ca351745fa86b9ba5a9452d785ac4f7fc2b7548ca2a46c4fcf4a'

def Main(method, args):
    if method == "test":
        return test()

    if method == "deploy":
        return Deploy()

    if not Grow():
        return False

    if method == "name":
        return Name

    if method == "symbol":
        return Symbol

    if method == "decimals":
        return Decimals

    if method == "totalSupply":
        context = GetContext()
        return Get(context, "supply")

    if method == "balanceOf":
        addr = args[0]
        return GetBalance(addr)

    if method == "transfer":
        addr_from = args[0]
        addr_to = args[1]
        amount = args[2]
        return Transfer(addr_from, addr_to, amount)

    if method == "transferFromPool":
        addr_to = args[0]
        amount = args[1]
        return TransferFromPool(addr_to, amount)

    if method == "postGeo":
        addr = args[0]
        geolocation = args[1]
        timestamp = args[2]
        return PostGeolocation(addr, geolocation, timestamp)

    if method == "requestGeo":
        addr = args[0]
        nBlocks = args[1]
        return RequestGeolocations(addr, nBlocks)

    if method == "requestTicket":
        addr = args[0]
        nBlocks = args[1]
        return RequestTicket(addr, nBlocks)


def Deploy():
    print("********deploy()")
    if not CheckWitness(ADMIN):
        print("No privilege!")
        return False

    context = GetContext()
    Put(context, "supply", InitialSupply)
    Put(context, "block/NRC", 0) 
    Put(context, "block/height", -1)

    Put(context, "balance/pool", InitialSupply)

    return True


def IncBlk():
    print("********IncBlk()")
    height = GetHeight()

    context = GetContext()
    h = Get(context, "block/height")
    if h == height:
        return False

    b = Get(context, "block/NRC") + 1
    Put(context, "block/NRC", b)
    Put(context, "block/height", height)

    SettleCredit()
    return True


def SettleCredit():
    print("********SettleCredit()")
    context = GetContext()
    b = Get(context, "block/NRC") - 1
    key = concat("credit/", b)
    credit = Get(context, key)
    if credit == 0:
        return

    key = concat(b, "/cnt")
    cnt = Get(context, key)
    if cnt == 0:
        # accumulate the credit to the next block
        t = b + 1
        key = concat("credit/", t)
        credit = Get(context, key) + credit
        Put(context, key, credit)
        return

    # NEO VM does not support floating point
    # credit_m is an integer
    credit_m = credit / cnt
    credit_left = credit - credit_m * cnt
    if credit_left > 0:
        # accumulate the rest credit to the next block
        t = b + 1
        key = concat("credit/", t)
        credit = Get(context, key) + credit_left
        Put(context, key, credit)

    if credit_m == 0:
        return

    # credit location-posters
    i = 1
    while i <= cnt:
        key = Concat4(b, "/", i, "/addr")
        addr = Get(context, key)

        key = concat("balance/", addr)
        balance = Get(context, key) + credit_m
        Put(context, key, balance)
        OnTransfer(0, addr, credit_m)
        i = i + 1


def Grow():
    print("********Grow()")
    context = GetContext()

    supply0 = Get(context, "supply")
    if supply0 == 0:
        print("Not yet deployed!")
        return False
    elif not IncBlk():
        print("Transaction is within the same block.")
        return True
    elif supply0 == MaximumSupply:
        return True

    supply = supply0 + GenerationPerBlock
    if supply > MaximumSupply:
        supply = MaximumSupply
    Put(context, "supply", supply)

    n = supply - supply0
    balance_pool = Get(context, "balance/pool") + n
    Put(context, "balance/pool", balance_pool)

    return True


def PostGeolocation(addr, geolocation, timestamp):
    print("********PostGeolocation")
    if len(addr) != 20:
        print("Invalid address!")
        return False

    if not CheckWitness(addr):
        print("No privilege!")
        return False

    context = GetContext()
    b = Get(context, "block/NRC")

    key = concat(b, "/cnt")
    cnt = Get(context, key) + 1
    Put(context, key, cnt)

    key = Concat4(b, "/", cnt, "/ts")
    Put(context, key, timestamp)

    key = Concat4(b, "/", cnt, "/addr")
    Put(context, key, addr)

    key = Concat4(b, "/", cnt, "/geo")
    Put(context, key, geolocation)

    return True


def GetBalance(addr):
    print("********GetBalance()")
    context = GetContext()
    key = concat("balance/", addr)
    return Get(context, key)


def Transfer(addr_from, addr_to, amount):
    print("********Transfer()")
    if amount <= 0:
        print("Invalid amount!")
        return False

    if len(addr_to) != 20:
        print("Invalid addr_to!")
        return False

    if not CheckWitness(addr_from):
        print("No privilege!")
        return False

    context = GetContext()

    key_from = concat("balance/", addr_from)
    balance_from = Get(context, key_from)
    if balance_from < amount:
        print("Insufficient balance!")
        return False

    key_to = concat("balance/", addr_to)
    balance_to = Get(context, key_to)

    balance_from -= amount
    balance_to += amount
    Put(context, key_from, balance_from)
    Put(context, key_to, balance_to)

    OnTransfer(addr_from, addr_to, amount)

    return True


def TransferFromPool(addr_to, amount):
    print("********TransferFromPool()")
    if amount <= 0:
        return False

    if len(addr_to) != 20:
        return False

    # only the admin can transfer from pool
    if not CheckWitness(ADMIN):
        print("No privilege!")
        return False

    context = GetContext()
    balance_pool = Get(context, "balance/pool")
    if balance_pool < amount:
        print("Insufficient balance in pool!")
        return False

    balance_pool -= amount
    Put(context, "balance/pool", balance_pool)

    key_to = concat("balance/", addr_to)
    balance_to = Get(context, key_to) + amount
    Put(context, key_to, balance_to)
    OnTransfer(0, addr_to, amount)

    return True


def RequestTicket(addr, nBlocks):
    print("********RequestTicket()")
    if nBlocks <= 0:
        print("Invalid nBlocks!")
        return False

    if not CheckWitness(addr):
        print("No privilege!")
        return False

    context = GetContext()
    key = concat("balance/", addr)
    balance = Get(context, key)

    fee = FeePerBlock * nBlocks
    if balance < fee:
        print("Insufficient balance to request ticket!")
        return False

    balance -= fee
    Put(context, key, balance)
    OnTransfer(addr, 0, fee)

    bl = Get(context, "block/NRC")
    br = bl + nBlocks - 1
    while bl <= br:
        key = concat("credit/", bl)
        Put(context, key, FeePerBlock)
        bl = bl + 1

    # Register the user
    key = concat("ticket/", addr)
    Put(context, key, br)
    print("User registered.")

    return True


# no need to actually invoke.
def RequestGeolocations(addr, nBlocks):
    print("********RequestGeolocations()")
    if not CheckWitness(addr):
        print("No privilege!")
        return False

    if nBlocks < 1:
        print("Invalid nBlocks!")
        return False

    context = GetContext()
    b = Get(context, "block/NRC")
    fromBlock = b - nBlocks + 1
    if fromBlock < 1:
        fromBlock = 1

    # check if the user holds a valid ticket 
    key = concat("ticket/", addr)
    br = Get(context, key)
    if br < b:
        print("User does not hold a valid ticket!")
        return False

    i = fromBlock
    while i <= b:
        key = concat(i, "/cnt")
        cnt = Get(context, key)

        j = 1
        while j <= cnt:
            key = Concat4(i, "/", j, "/ts")
            timestamp = Get(context, key)

            key = Concat4(i, "/", j, "/addr")
            addr = Get(context, key)

            key = Concat4(i, "/", j, "/geo")
            geolocation = Get(context, key)

            payload = [timestamp, addr, geolocation]
            Notify(payload)

            j = j + 1

        i = i + 1

    return True


def Concat3(a, b, c):
    s = concat(a, b)
    s = concat(s, c)
    return s


def Concat4(a, b, c, d):
    s = Concat3(a, b, c)
    s = concat(s, d)
    return s


def Test(method, args):
    print("====================================================")
    msg = concat("Testing ", method)
    msg = concat(msg, "...")
    print(msg)

    r = Main(method, args)
    msg = concat("Return: ", r)
    print(msg)


def test():
    addr_admin = b'#\xba\'\x03\xc52c\xe8\xd6\xe5"\xdc2 39\xdc\xd8\xee\xe9'
    addr_test = b'Ua\x10\xb9\xc58|\x13\x88m0{\xa0\xbb\xe4l\xe6\xd3\xac\x80'

    args = []
    Test("deploy", args)
    Test("name", args)

    args = [addr_admin,1024]
    Test("transferFromPool", args)

    args = [addr_admin, addr_test, 150]
    Test("transfer", args)

    args = [addr_admin, "$123_456_789", 1234567891000]
    Test("postGeo", args)

    args = [addr_admin, "$12_45_78", 1234567893000]
    Test("postGeo", args)

    args = [addr_admin, 5]
    Test("requestTicket", args)

    addr_admin = b'#\xba\'\x03\xc52c\xe8\xd6\xe5"\xdc2 39\xdc\xd8\xee\xe9'
    args = [addr_admin, 1]
    Test("requestGeo", args)

    addr_admin = b'#\xba\'\x03\xc52c\xe8\xd6\xe5"\xdc2 39\xdc\xd8\xee\xe9'
    args = [addr_admin]
    Test("balanceOf", args)

    # Force grow
    context = GetContext()
    Put(context, "block/height", -1)

    addr_admin = b'#\xba\'\x03\xc52c\xe8\xd6\xe5"\xdc2 39\xdc\xd8\xee\xe9'
    args = [addr_admin, "$x_y_z", 1234567993000]
    Test("postGeo", args)

    addr_admin = b'#\xba\'\x03\xc52c\xe8\xd6\xe5"\xdc2 39\xdc\xd8\xee\xe9'
    args = [addr_admin, 1]
    Test("requestGeo", args)

    # Force grow
    context = GetContext()
    Put(context, "block/height", -1)
    Test("symbol", args)

    # Force grow
    context = GetContext()
    Put(context, "block/height", -1)
    Test("name", args)

    return True

