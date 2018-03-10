# NRC: NEO Robot Communication

NRC (NEO Robot Communication) is a decentralized platform for human-robot communication. It allows an autonomous car to obtain other vehicles' information which may not be detectable by its onboard sensors to avoid potential collisions.

Whitepaper: https://github.com/neo-robotics/whitepaper/blob/master/ner.pdf

## Incentive

Vehicles can post their geolocations to the NRC platform. 
To obtain these geolocations, an autonomous car needs to pay some NRC token for a ticket which is valid within a certain amount of blocks. 
The NRC token paid are then distributed to the geolocation-posters, which motivates them to continue posting their geolocations.

## Demo

Watch our demo video on YouTube: <https://www.youtube.com/watch?v=R0IuDfLkoBs>

#### Without NRC

An autonomous white car is driving straight on a road: 
![D1](https://github.com/neo-robotics/NRC/blob/master/figures/D1.jpg)

Its onboard sensors could not detect any vehicles on the north-south road as they are blocked by the "walls". It keeps driving forward, and unfortunately, collides with a red car: 
![D2](https://github.com/neo-robotics/NRC/blob/master/figures/D2.jpg)

#### With NRC

The red car keeps posting its geolocations to the NRC platform. The autonomous white car, which has already purchased a ticket on the NRC platform, obtains the red car's geolocations (blue circle): 
![D3](https://github.com/neo-robotics/NRC/blob/master/figures/D3.jpg)

From the data it detects a potential collision. It then reduces its speed to avoid the collision:
![D4](https://github.com/neo-robotics/NRC/blob/master/figures/D4.jpg)
![D5](https://github.com/neo-robotics/NRC/blob/master/figures/D5.jpg)

