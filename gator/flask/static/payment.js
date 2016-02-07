"use strict";

angular.module("app", [])
.controller("mainCtrl", ["$scope", "$window", "$http", "$location", function($scope, $window, $http, $location) {

    var productionUrl = "https://api.godelegateit.com";
    var validTestHosts = {
        "localhost:8000": null,
        "test-gatorapi.us-west-2.elasticbeanstalk.com:80": null
    };

    var apiUrl = ($location.search().host in validTestHosts) ? "http://" + $location.search().host : productionUrl;
    var apiToken = $location.search().token;
    var transactionUuid = $location.search().transaction;

    console.log("api: ", apiUrl);
    console.log("token: ", apiToken);
    console.log("uuid: ", transactionUuid);

    $scope.loading = true;
    $scope.receipt = null;
    $scope.errorMsg = "";

    var stripe = StripeCheckout.configure({
        key: apiUrl == productionUrl ?  "pk_live_S32yhEieSboL59e75AWjUGBb" : "pk_test_ZoK03rN4pxc2hfeYTzjByrdV",
        //image: '/img/documentation/checkout/marketplace.png',
        locale: 'auto',
        token: function(token) { payTransaction(token); }
    });

    $window.onpopstate = function() {
        stripe.close();
    };

    $scope.onPayBtnClick = function($event) {
        stripe.open({
            name: 'DelegateIt',
            //description: '2 widgets',
            amount: $scope.total
        });
        $event.preventDefault();
    };

    $scope.hasPaid = function() {
        return $scope.receipt != null && "stripe_charge_id" in $scope.receipt;
    };

    $scope.isPayBtnDisabled = function() {
        return $scope.receipt == null || $scope.loading;
    };

    var loadTransaction = function() {
        $http({
            url: apiUrl + "/core/transaction/" + transactionUuid + "?token=" + apiToken,
            method: "GET",
        }).success(function(data, status, headers, config) {
            $scope.loading = false;
            if (data.result == 0) {
                if ("receipt" in data.transaction)
                    $scope.receipt = data.transaction.receipt;
                else
                    $scope.errorMsg = "The receipt has not been saved. Please contact your delegator";
            } else {
                $scope.errorMsg = data.error_message;
            }
        }).error(function(data, status, headers, config) {
            $scope.loading = false;
            if ("error_message" in data)
                $scope.errorMsg = data.error_message;
            else
                $scope.errorMsg = "The server incountered an error";
        });
    };

    var payTransaction = function(stripeSource) {
        $scope.loading = true;
        $http({
            url: apiUrl + "/payment/charge/" + transactionUuid + "?token=" + apiToken,
            method: "POST",
            data: {stripe_source: stripeSource.id}
        }).success(function(data) {
            $scope.loading = false;
            if (data.result == 0) {
                $scope.receipt.stripe_charge_id = data.charge.id;
            } else {
                $scope.errorMsg = data.error_message;
            }
        }).error(function(data) {
            $scope.loading = false;
            if ("error_message" in data)
                $scope.errorMsg = data.error_message;
            else
                $scope.errorMsg = "The server incountered an error";
        });
    };

    loadTransaction();

}]);
