# NRC Simulator

This simulator demonstrates how an autonomous white car utilizes the NRC platform to avoid a potential collision with a red car. The red car keeps posting its geolocations to the NRC platform. The autonomous white car obtains its geolocations from which it detects a potential collision. It then reduces its speed to avoid such a collision. It is noted that in order to obtain geolocations from NRC, the autonomous car must hold a valid ticket which could be purchased by paying a certain amount of NRC token to the NRC platform. The longer is the ticket validity, the more fee should the autonomous car pay. The NRC token paid will then be credited to the red car to motivate its service.

## Installation and Contract Deployment

1. Install [neo-python](https://github.com/CityOfZion/neo-python) and pygame. 

2. Setup a NEO privnet by following the instruction on https://github.com/CityOfZion/neo-privatenet-docker.

3. Use `neo-python` to open the wallet located at `configs/sender/wallet.db` (password is `nrc123456*`), and deploy the contract with `import contract contract.avm 0710 05 True False`.

4. Invoke the contract with the `deploy` method: `testinvoke 3c6a0ee4cecadfd6d3fd06fd7e7eedfa6d57dfe1 deploy []`.

5. The sender wallet is the administrator who has the privlege to transfer NRC token from the NRC pool to a NEO address. Invoke the contract with the `transferFromPool` method to send some NRC token to the sender and the receiver for testing:

```
testinvoke 3c6a0ee4cecadfd6d3fd06fd7e7eedfa6d57dfe1 transferFromPool ["APZKN2CuaB73i4LamV6RwySWjYVCRph5e8",10000]
testinvoke 3c6a0ee4cecadfd6d3fd06fd7e7eedfa6d57dfe1 transferFromPool ["AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y",10000]
```

6. Send some gas to the receiver for testing:

```
send gas APZKN2CuaB73i4LamV6RwySWjYVCRph5e8 2000
```

## Testing

To run the simulator, first run the `NRCSender` on a terminal:

```bash
$ ./lib/NRCSender.py
```

Then run the `NRCReceiver` on another terminal:

```bash
$ ./lib/NRCReceiver.py
```

Finally, run the simulator:

```
$ ./simulator.py
```

To demonstrate the collision, comment out the `postGeolocation()` in the `senderAction()` function in `simulator.py` and then run the simulator.

## Screenshots

![D3](https://github.com/neo-robotics/NRC/blob/master/figures/D3.jpg)
![D4](https://github.com/neo-robotics/NRC/blob/master/figures/D4.jpg)

