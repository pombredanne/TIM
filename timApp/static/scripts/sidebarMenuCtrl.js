/**
 * FILL WITH SUITABLE TEXT
 * @module sidebarMenuCtrl
 * @author Matias Berg
 * @author Bek Eljurkaev
 * @author Minna Lehtomäki
 * @author Juhani Sihvonen
 * @author Hannu Viinikainen
 * @licence MIT
 * @copyright 2015 Timppa project authors
 */
var angular;
var timApp = angular.module('timApp');

timApp.controller("SidebarMenuCtrl", ['$scope', "$http", "$window",

    function ($scope, $http, $window) {
        $scope.currentLecturesList = [];
        $scope.futureLecturesList = [];
        $scope.pastLecturesList = [];
        $scope.lectureQuestions = [];
        $scope.materialQuestions = [];

        $scope.active = -1;
        if ($window.showIndex) {
            $scope.active = 0;
        }
        $scope.lastTab = $scope.active;

        /**
         * FILL WITH SUITABLE TEXT
         * @memberof module:sidebarMenuCtrl
         */
        $scope.showSidebar = function () {
            var tabs = $("#menuTabs");
            if (tabs.is(":visible")) {
                if ($scope.active !== null) {
                    $scope.lastTab = $scope.active;
                    $scope.active = -1; // this will set the value to null and remove the "selected" state from tab
                    if ($('.device-xs').is(':visible') || $('.device-sm').is(':visible')) {
                        tabs.hide();
                    }
                } else {
                    $scope.active = $scope.lastTab;
                }
            } else {
                tabs.show();
                tabs.attr("class", "");
                if ($scope.active === null) {
                    $scope.active = $scope.lastTab || 0;
                }
            }
        };

        /**
         * FILL WITH SUITABLE TEXT
         * @memberof module:sidebarMenuCtrl
         */
        $scope.toggleLectures = function () {
            $http({
                url: '/getAllLecturesFromDocument',
                method: 'GET',
                params: {'doc_id': $scope.docId}
            })
                .success(function (lectures) {
                    $scope.currentLecturesList = lectures.currentLectures;
                    $scope.futureLecturesList = lectures.futureLectures;
                    $scope.pastLecturesList = lectures.pastLectures;
                })
                .error(function () {
                    console.log("Couldn't fetch the lectures");
                });
        };

        /**
         * FILL WITH SUITABLE TEXT
         * @memberof module:sidebarMenuCtrl
         */
        $scope.toggleQuestions = function () {
            $scope.lectureQuestions = [];
            $http({
                url: '/questions/' + $scope.docId,
                method: 'GET'
            })
                .success(function (questions) {
                    for (var i = 0; i < questions.length; i++) {
                        var question = {
                            "questionId": questions[i].question_id,
                            "questionTitle": (JSON.parse(questions[i].questionjson)).TITLE
                        };
                        $scope.lectureQuestions.push(question);
                    }
                })
                .error(function () {
                    console.log("Couldn't fetch the questions");
                });
        };
    }
])
;