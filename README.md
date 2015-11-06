# OrderAPI

The order api is responsible for creating and handling the orders for DelegateIt by providing a REST based api. The three main clients that use this api are the delegator, sms, and ios clients.

To start your own local version of the api for developement or testing purpses, review the instructions found in the GatorCore repo. GatorCore is responsible for setting up the environment while OrderAPI focuses on code.

## Tests
Before you push any changes run through the testing framework to make sure nothing broke. Also add new tests if any new functionallity was added. Currently there are only endpoint tests which test the api through http requests. To run these tests, enter the `testlib` directory and run `nosetests endpoint`. You will need to install 'nose', 'requests', and 'boto' through pip with python version 3.4. Alternatively, you can run the tests from within the api docker container.
