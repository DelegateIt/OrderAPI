var http = require('http');
var gator = require("./gator.js");
if (gator.config == null)
    gator.loadConfig("./config.json");

exports.handler = function(event, context) {
    console.log("Received event", JSON.stringify(event));
    if ("uuid" in event.Records[0].dynamodb.Keys)
        var uuid = event.Records[0].dynamodb.Keys.uuid.S;
    else
        var uuid = event.Records[0].dynamodb.Keys.customer_uuid.S + "-" +
                event.Records[0].dynamodb.Keys.timestamp.N;
    gator.notifyHandlers(uuid, function(err, rsp) {
        if (err)
            context.fail(err);
        else
            context.succeed();
    });
};
