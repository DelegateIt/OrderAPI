var http = require('http');
var gator = require("./gator.js");
gator.loadConfig("./aws-test-config.json");
gator.auth_token = gator.config["notifier_host"]["gator_key"];

exports.handler = function(event, context) {
    var uuid = event.Records[0].dynamodb.Keys.uuid.S;
    gator.notifyHandlers(uuid, function(err, rsp) {
        if (err)
            context.fail(err);
        else
            context.succeed();
    });
};
