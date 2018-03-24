# NRC: NEO Robot Communication

NRC (NEO Robot Communication) is a decentralized platform for human-robot communication. It allows an autonomous car to obtain other vehicles' information which may not be detectable by its onboard sensors to avoid potential collisions.

Whitepaper: https://github.com/neo-robotics/whitepaper/blob/master/ner.pdf

## Incentive

Vehicles can post their geolocations to the NRC platform. 
To obtain these geolocations, an autonomous car needs to pay some NRC token for a ticket which is valid within a certain amount of blocks. 
The NRC token paid are then distributed to the geolocation-posters, which motivates them to continue posting their geolocations.

## Demo

Watch our demo video:

YouTube: <https://youtu.be/u59L_q37pxc>
YouKu: <http://v.youku.com/v_show/id_XMzQ4ODQ1MzQxNg==.html>

A human driver and an autonomous car tried to navigate through an intersection at the same time:
![setup](https://github.com/neo-robotics/NRC/blob/master/figures/0.setup.png)

#### Without NRC

The human driven car was driving straight forward:
![human-wo](https://github.com/neo-robotics/NRC/blob/master/figures/1.human-wo.png)

The autonomous car was driving forward. Its onboard sensors could not detect anything on the right side road as they were blocked by the bushes:
![robot-wo](https://github.com/neo-robotics/NRC/blob/master/figures/2.robot-wo.png)

The autonomous car was not aware that a human driven car was nearby, and unfortunately, it collided with the human car:
![collision](https://github.com/neo-robotics/NRC/blob/master/figures/3.collision.png)

#### With NRC

The human driven car kept posting its position to the blockchain:
![human-w](https://github.com/neo-robotics/NRC/blob/master/figures/4.human-w.png)

The position was broadcast to the blockchain:
![post](https://github.com/neo-robotics/NRC/blob/master/figures/5.post.png)

The autonomous car received positions of nearby objects from the blockchain:
![robot-w](https://github.com/neo-robotics/NRC/blob/master/figures/6.robot-w.png)

The positions of the human driven car were received:
![receive](https://github.com/neo-robotics/NRC/blob/master/figures/7.receive.png)

The autonomous detected a potential collision, and consequently, it stopped for a while, which avoided such a collision.
![stop](https://github.com/neo-robotics/NRC/blob/master/figures/8.stop.png)

The human driven car was rewarded with NRC tokens.
![reward](https://github.com/neo-robotics/NRC/blob/master/figures/9.reward.png)


