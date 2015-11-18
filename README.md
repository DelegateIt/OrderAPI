# OrderAPI

The order api is responsible for creating and handling the orders for DelegateIt by providing a REST based api. The three main clients that use this api are the delegator, sms, and ios clients.

To start your own local version of the api for developement or testing purpses, review the instructions found in the GatorCore repo. GatorCore is responsible for setting up the environment while OrderAPI focuses on code.

## Tests
Before you push any changes run through the testing framework to make sure nothing broke. Also add new tests if any new functionallity was added.

There are three different types of tests within `testlib`. `endpoint` tests just test the api by using http requests/responses. `internal` tests the internal `gator` python package. `notifier` tests the socket.io notification system. The tests are run by gaining a shell within the respective container (`api` container for `endpoint` and `internal`, `ntfy` for `notifier` tests) then entering the `testlib` directory. Running `nosetests endpoint`, `nosetests internal`, `nosetests notifier` will run their respective tests.
