var express = require('express');
var app = express();
var http = require('http').Server(app);
var bodyParser = require('body-parser');
var gator = require('./gator.js');
var port = 8061;

var lambda = require("./lambda.js")

var Context = function() {

    this.completed = null;
    this.timeoutId = null;

    this.fail = function(error) {
        this.completed = "fail";
        console.log("Error: " + error);
    }

    this.succeed = function() {
        this.completed = "success";
    }

    this.abort = function() {
        console.log("Timeout");
        clearTimeout(this.timeoutId);
    }
};

app.use(bodyParser.json());

app.get('/', function(req, res){
    res.send('gator psuedo lambda server');
});

app.post('/process_records', function(req, res){
    console.log("Received records", req.body);
    var context = new Context();
    context.timeoutId = setTimeout(function() {
        lambda.handler(req.body, context);
    }, 0);

    setTimeout(function() {
        if (context.completed == null)
            context.abort();
    }, 3000);

    res.send(JSON.stringify({'result': 0}));
});

http.listen(port, function(){
    console.log('lambda server listening on *:' + port);
});
