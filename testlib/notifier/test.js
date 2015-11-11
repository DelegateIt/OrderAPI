var assert = require("assert");
var gator = require("../../notify/gator.js");
var io = require("socket.io-client");

var test = function(name, func) {
    var returned = false;
    var callback = function(success) {
        returned = true;
        if (success === true || typeof(success) === "undefined") {
            console.log("Passed test: " + name);
            process.exit(0);
        } else {
            console.log("Failed test: " + name);
            process.exit(1);
        }
    };
    var fail_test = function() {
        if (returned === false) {
            console.log("Failed test - timedout: " + name);
            process.exit(1);
        }
    };
    func(callback);
    setTimeout(fail_test, 5000);
};

test("invoke-lambda-and-receive-socketio-emit", function(done) {
    if (process.argv.length != 3)
        throw "The uuid of the transaction must be passed in as a argument"
    var uuid = process.argv[2];
    console.log("Using transaction with uuid: " + uuid);
    gator.updateHandler(function(err) {
        assert(!err);
        console.log("Added handler to database");
        var options ={
            "transports": ["websocket"],
            "force new connection": true
        };
        var client = io.connect("http://0.0.0.0:8060", options);
        client.on('connect', function(data){
            client.emit('register_transaction', {"transaction_uuid": uuid});
            console.log("Client emited `register_transaction` socket.io event");
            client.on(uuid, function(data){
                console.log("Client received transaction change event");
                done(data["uuid"] === uuid);
            });
            console.log("Notifying handlers");
            gator.notifyHandlers(uuid, function(err, rsp) {
                assert(!err);
                console.log("Notified handlers", rsp);
            });
        });
    });
});
