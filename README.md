# ds2022-mini-proj-1
## Distributed Systems mini project 1 - The Byzantine General’s problem with Consensus

Authors: Braian O. Dias,  Amey Chandrakant Dareka

Implementation of [Byzantine fault tolerance (BFT)](https://en.wikipedia.org/wiki/Byzantine_fault)

Full Description of the task is [here](https://courses.cs.ut.ee/LTAT.06.007/2022_spring/uploads/Main/Mini-project2-DS2022.pdf) 

Demo of the program can be seen [here](video/demo.mp4): 


## Usage

`requirements.txt` contains all packages needed to run the application on python 3.8.

To execute the progam run:

```
python byzantine_generals.py N
```
Where `N` is the number of processes (generals) to be created during initialization.

## Troubleshooting

In case the execution starts to hang during message exchange (i.e: execution of the command `actual-order`), it is likely that the OS is interfering in the communication.
The default port for communication start at `5000`, and each general has a different port for communicating between each other (e.g: 5001, 5002, 5003...).

To specify a new starting port run:

```
python byzantine_generals.py N STARTING_PORT
```

Where `STARTING_PORT` is the new starting port number.