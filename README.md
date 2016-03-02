# OrderAPI

The order api is responsible for creating and handling the orders for DelegateIt by providing a REST based api. The three main clients that use this api are the delegator, sms, and ios clients.

## Creating/starting the api
[Docker](https://www.docker.com/) is used extensively thoughout the OrderApi and must be installed.
Once docker is installed, the env.py script will handle most of the environment related tasks.

To start the api run:
`env.py start`
This will pull the latest docker image, create the containers, then start them. `env.py start` also destroys any previous state from a previously running api. 

To stop the api run:
`env.py stop`

#### Aside for mac and windoze users
Setting up docker in these environments is a little different since docker relies on features in the linux kernel to work properly. Docker should be installed using the [Docker Toolbox](https://www.docker.com/docker-toolbox) which will create a linux vm for you then it'll run docker inside the vm. The Toolbox comes with a program called "Docker Quickstart Terminal" that will open your default shell and configure it with the correct environment variables for docker to work. It also ensures your linux vm is configured and running. All `docker` and `env.py` commands should be run inside the terminal that "Docker Quickstart Termainal" opens.


## Connecting to the api
Port mappings:
* 8000 - Flask API
* 8060 - Socket.io

The ip address for the docker containers is `127.0.0.1` on linux and for macs it is whatever ip your vm is assigned. The "Docker Quickstart Terminal" will print out this ip when it is opened. Alternatively, the command `docker-machine ip default` will print out the ip.

## Interacting with the API
Included within the repo is a client wrapper for the API called `apiclient.py`. With the client you can easily create/edit customers, delegators, transactions and more. To enter the python interactive shell run `docker exec -ti api python3`; from there you can import the apiclient and start sending api requests.
```
> from gator import apiclient
>
> # Look at the available methods to call and their arguments
> help(apiclient)
> 
> # simulate sending a sms to the api.
> apiclient.send_sms_to_api("+15555554444", "this is the message body")
> 
> # Create a delegator.
> apiclient.create_delegator(firstname, lastname, phone, email, fbuser_id, fbuser_token)
> # The locally running API does not validate the fbuser id or token so you can set whatever values
```

## Tests
Before you push any changes run through the testing framework to make sure nothing broke. Also add new tests if any new functionallity was added.

There are three different types of tests within `testlib`:
- `endpoint` tests just test the api by using http requests/responses
- `internal` tests the internal `gator` python package
- `notifier` tests the socket.io notification system

The tests are run using the *run_tests.py* script in the `testlib` directory. To tail output from the container you can use *docker logs -f api*.

NOTE: the docker containers must be created before the running the tests

## Extras
Sometimes it's neccessary to get a shell in a container and this command can be used `docker exec -t -i <container_name> /bin/bash`. You might notice that by default you won't have sudo access since the default user has no password. If you need root access pass the `-u root` argument into docker exec like this `docker exec -t -i -u root <container_name> /bin/bash`

To monitor the log output of a container run `docker log -tf <container_name>`.

To list all the containers and some info about them run `docker ps -a`.

There are a lot of other useful things docker can do and some of them are listed in the `docker --help` output.
