var http = require('http');
var gator = require('./gator.js')

gator.apiHostName = "backend-lb-125133299.us-west-2.elb.amazonaws.com";
gator.apiHostPort = 80;

exports.handler = function(event, context) {
    var uuid = event.Records[0].dynamodb.Keys.uuid.S;
    gator.notifyHandlers(uuid, function(err, rsp) {
        if (err)
            context.fail(err);
        else
            content.succeed();
    });
};
