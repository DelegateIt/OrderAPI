# OrderAPI

The order api is responsible for creating and handling the orders for DelegateIt by providing a REST based api. The three main clients that use this api are the delegator, sms, and ios clients.

To start your own local version of the api for developement or testing purpses, review the instructions found in the GatorCore repo. GatorCore is responsible for setting up the environment while OrderAPI focuses on code.

## Interacting with the API
Included within the repo is a client wrapper for the API called `apiclient.py`. With the client you can easily create/edit customers, delegators, transactions and more. To enter the python interactive shell run `docker exec -ti api python3`; from there you can import the apiclient and start sending api requests.
```
> from gator import apiclient
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
