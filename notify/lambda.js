var http = require('http');
var gator = require('./gator.js')

gator.loadConfig("production-config.json");

exports.handler = function(event, context) {
    var uuid = event.Records[0].dynamodb.Keys.uuid.S;
    gator.notifyHandlers(uuid, function(err, rsp) {
        if (err)
            context.fail(err);
        else
            content.succeed();
    });
};