var child_process = require("child_process")
var http = require("http");
var fs = require("fs");

module.exports = {};

module.exports.config = null;

module.exports.loadConfig = function(filepath) {
    contents = fs.readFileSync(filepath, 'utf8')
    module.exports.config = JSON.parse(contents);
};

module.exports.request = function(host, port, path, method, json, callback) {
    path += "?token=" + encodeURIComponent(module.exports.config["notifier_host"]["gator_key"]);
    var options = {
        hostname: host,
        port: port,
        path: path,
        method: method,
        headers: {}
    };
    if (json != null) {
        options.headers['Content-Type'] = 'application/json';
        options.headers['Content-Length'] = JSON.stringify(json).length;
    }
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

    var wrapped = function(err, resp) {
        if (err != null)
            setTimeout(function() { module.exports.updateHandler(callback) }, 5000);
        else
            return callback(err, resp);
    };

    module.exports.request(
            module.exports.config.api_host.name,
            module.exports.config.api_host.recv_port,
            '/notify/handler',
            'POST',
            {"port": module.exports.config.notifier_host.recv_port},
            wrapped);

};


module.exports.getHandlers = function(callback) {
    module.exports.request(
            module.exports.config.api_host.name,
            module.exports.config.api_host.recv_port,
            '/notify/handler',
            'GET',
            null,
            callback);
};

module.exports.notifyHandlers = function(transactionUuid, callback) {
    module.exports.request(
            module.exports.config.api_host.name,
            module.exports.config.api_host.recv_port,
            '/notify/broadcast/' + transactionUuid,
            'POST',
            null,
            callback);
};

module.exports.execApiClient = function(method, args, callback) {
    var argString = "";
    if (args.length > 0) {
        argString = "\"";
        for (var i = 0; i < args.length - 1; i++)
            argString += args[i] + "\", \"";
        argString += args[args.length - 1] + "\"";
    }

    var cmd = "/usr/bin/python3 -c '" +
              "import json; " +
              "from gator import apiclient; " +
              "print(json.dumps(apiclient." + method + "(" + argString + ")))'";

    return child_process.exec(cmd, function(error, stdout) {
        var result = null;
        try {
            result = JSON.parse(stdout);
        } catch (e) {
            //do nothing
        }
        callback(error, result);
    });
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
