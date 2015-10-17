var http = require("http");
var fs = require("fs");

module.exports = {};

module.exports.config = {};

module.exports.loadConfig = function(filepath) {
    contents = fs.readFileSync(filepath, 'utf8')
    module.exports.config = JSON.parse(contents);
};

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
            module.exports.config.api_host.name,
            module.exports.config.api_host.port,
            '/notify/handler',
            'POST',
            null,
            callback);
};


module.exports.getHandlers = function(callback) {
    module.exports.request(
            module.exports.config.api_host.name,
            module.exports.config.api_host.port,
            '/notify/handler',
            'GET',
            null,
            callback);
};

module.exports.notifyHandlers = function(transactionUuid, callback) {
    module.exports.request(
            module.exports.config.api_host.name,
            module.exports.config.api_host.port,
            '/notify/broadcast/' + transactionUuid,
            'POST',
            null,
            callback);
};

var getTime = function() {
    return Math.floor(new Date() / 1000);
};

var tryLoadingEnvConfig = function() {
    if ("GATOR_CONFIG_PATH" in process.env)
        module.exports.loadConfig(process.env["GATOR_CONFIG_PATH"]);
    else
        console.warn("'GATOR_CONFIG_PATH' not found in the environment variables; cannot load config");
};
tryLoadingEnvConfig();

