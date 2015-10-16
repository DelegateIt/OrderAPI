var http = require("http");

module.exports = {};

module.exports.apiHostName = ("GATOR_PRODUCTION" in process.env && process.env.GATOR_PRODUCTION == "true") ?
            "backend-lb-125133299.us-west-2.elb.amazonaws.com" : "localhost";
module.exports.apiHostPort = ("GATOR_PRODUCTION" in process.env && process.env.GATOR_PRODUCTION == "true") ?
            80 : 8000;

module.exports.request = function(host, port, path, method, json, callback) {
    var options = {
        hostname: host,
        port: port,
        path: path,
        method: method,
        headers: {}
    };
    if (json != null)
        options.headers['Content-Type'] = 'application/json';
    var req = http.request(options, function(res) {
        res.setEncoding('utf8');
        var allChunks = "";
        res.on('data', function (chunk) {
            allChunks += chunk;
        });
        res.on('end', function() {
            var error = null;
            try {
                allChunks = JSON.parse(allChunks);
            } catch (e) {
                console.warn("Error parsing json response", e, allChunks);
                error = e;
            }
            callback(error, allChunks);
        })
    });
    req.on('error', function(e) {
        console.warn("Error while sending request", e);
        callback(e, null);
    });
    if (json != null)
        req.write(JSON.stringify(json));
    req.end();
};

module.exports.updateHandler = function(callback) {
    module.exports.request(
            module.exports.apiHostName,
            module.exports.apiHostPort,
            '/notify/handler',
            'POST',
            null,
            callback);
};


module.exports.getHandlers = function(callback) {
    module.exports.request(
            module.exports.apiHostName,
            module.exports.apiHostPort,
            '/notify/handler',
            'GET',
            null,
            callback);
};

module.exports.notifyHandlers = function(transactionUuid, callback) {
    module.exports.request(
            module.exports.apiHostName,
            module.exports.apiHostPort,
            '/notify/broadcast/' + transactionUuid,
            'POST',
            null,
            callback);
};

var getTime = function() {
    return Math.floor(new Date() / 1000);
};
