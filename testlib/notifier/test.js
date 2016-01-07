var assert = require("assert");
var gator = require("../../notify/gator.js");
var io = require("socket.io-client");

describe("Notification system test", function() {

    var setup = function(callback) {
        gator.execApiClient("clear_database", [], function(err) {
            assert(err == null);
            console.log("Cleared database");

            gator.updateHandler(function(err, result) {
                assert(err == null);
                console.log("Added handler to database", result);

                gator.execApiClient("create_customer", ["fname", "lname", "15555551234", "1", ""], function(err, result) {
                    assert(err == null);
                    console.log("Created customer", result);

                    gator.execApiClient("create_transaction", [result.uuid, "ios"], function(err, result) {
                        assert(err == null);
                        console.log("Created Transaction", result);
                        callback(result.uuid);
                    });
                });
            });
        });
    };

    it('test socket.io', function(done) {
        setup(function(transactionUuid) {

            var client = io.connect("http://0.0.0.0:8060");
            client.on('connect', function(data){

                client.emit('register_transaction', {"transaction_uuid": transactionUuid});
                console.log("Client emited `register_transaction` socket.io event");

                client.on(transactionUuid, function(data){
                    console.log("Client received transaction change event");
                    assert(data["uuid"] === transactionUuid);
                    done();
                });

                // This will cause a long chain of events to occure:
                // Reverse dynamo proxy detects transaction write -> sends event to
                // lambda server -> executes lambda function -> POST /notify/broadcast/ to api ->
                // POST to socket.io servers from flask api -> socket.io servers notify clients of
                // change. Jesus fuck, that's a lot
                gator.execApiClient("send_message", [transactionUuid, true, "hello"], function(err) {
                    assert(err == null);
                    console.log("Updated transaction. Lambda should be invoked soon");
                });
            });
        });
    });
});
