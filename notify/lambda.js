var http = require('http');
var gator = require("./gator.js");
if (gator.config == null)
    gator.loadConfig("./config.json");

exports.handler = function(event, context) {
    var uuid = event.Records[0].dynamodb.Keys.uuid.S;
    console.log("Received update for " + uuid);
    gator.notifyHandlers(uuid, function(err, rsp) {
        if (err)
            context.fail(err);
        else
            context.succeed();
    });
};
