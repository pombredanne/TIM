import {timApp} from "tim/app";
import angular = require("angular");
import $ = require("jquery");

/**
 * Lecture creation controller which is used to handle and validate the form data.
 * @module createLectureCtrl
 * @author Matias Berg
 * @author Bek Eljurkaev
 * @author Minna Lehtomäki
 * @author Juhani Sihvonen
 * @author Hannu Viinikainen
 * @licence MIT
 * @copyright 2015 Timppa project authors
 */

timApp.controller("CreateLectureCtrl", ['$scope', "$http", "$window",

    function ($scope, $http, $window) {
        "use strict";
        $scope.showLectureCreation = false;
        $scope.useDate = false;
        $scope.useDuration = false;
        $scope.dateChosen = false;
        $scope.durationChosen = false;
        $scope.durationHour = "";
        $scope.durationMin = "";
        $scope.lectureId = null;
        $scope.dateCheck = false;
        $scope.dueCheck = false;
        $scope.error_message = "";
        $scope.lectureCode = "";
        $scope.lectureEncoded = "";
        $scope.password = "";
        $scope.startDate = "";
        $scope.startHour = "";
        $scope.maxStudents = "";
        $scope.startMin = "";
        $scope.earlyJoining = true;
        var date = new Date();
        $scope.editMode = false;
        $scope.startDate = date.getDate() + "." + (date.getMonth() + 1) + "." + date.getFullYear();
        angular.element('#startDate').datepicker({dateFormat: 'dd.m.yy'}); //calendar for start date initalized
        angular.element('#endDate').datepicker({dateFormat: 'dd.m.yy'}); //calendar for start date initalized

        /**
         * Function called when new lecture form button is pressed.
         * @memberof module:createLectureCtrl
         */
        $scope.$on('initLectureFormVals', function () {
            $scope.initLectureForm();
        });

        $scope.splitDate = function(d) {
            var p = new Date(Date.parse(d));
               //       0              1             2           3           4
            return [p.getFullYear(),p.getMonth()+1,p.getDate(),p.getHours(),p.getMinutes()];
        }

        $scope.$on('editLecture', function (event, data) {
            $scope.lectureCode = data.lecture_name;
            $scope.lectureCodeEncoded = encodeURIComponent($scope.lectureCode);

            $scope.hostName = encodeURIComponent(location.host);
            $scope.lectureId = data.lecture_id;
            // start_date is of the form: 2016-07-13T12:33:00+00:00
            //var splittedStart = data.start_date.split("T");
            // var splittedStartTime = splittedStart[1].split('+')[0].split(":");
            var splittedStartDate = $scope.splitDate(data.start_date);
            var splittedEndDate = $scope.splitDate(data.end_date);
            $scope.startMin = splittedStartDate[4];
            $scope.startHour = splittedStartDate[3];
            $scope.startDate = splittedStartDate[2] + "." + splittedStartDate[1] + "." + splittedStartDate[0];
            // var splittedEnd = data.end_date.split("T");
            // var splittedEndTime = splittedEnd[1].split('+')[0].split(":");
            // var splittedEndDate = splittedEnd[0].split("-");
            $scope.enableDate2();
            $scope.endMin = splittedEndDate[4];
            $scope.endHour = splittedEndDate[3];
            $scope.endDate = splittedEndDate[2] + "." + splittedEndDate[1] + "." + splittedEndDate[0];
            if (data.password !== undefined) {
                $scope.password = data.password;
            }
            $scope.editMode = data.editMode;
            $scope.addKeyListeners();
        });


        $scope.addKeyListeners = function() {
            if ( $scope.dataform ) return; // allready keys binded
            $scope.dataform = $("#lectureForm")[0];

            $scope.dataform.addEventListener('keydown', function(event) {
                if (event.ctrlKey || event.metaKey) {
                    switch (String.fromCharCode(event.which).toLowerCase()) {
                    case 's':
                        event.preventDefault();
                        $scope.submitLecture();
                        break;
                    }
                }
            });
        }


        /**
         * Lecture form initialized to have the current date and time as default starting time.
         * @memberof module:createLectureCtrl
         */
        $scope.initLectureForm = function () {
            $window.console.log("Lecture initialized.");
            var date = new Date();
            $scope.startDate = date.getDate() + "." + (date.getMonth() + 1) + "." + date.getFullYear();
            $scope.startHour = $scope.leftPadder(date.getHours(), 2);
            $scope.startMin = $scope.leftPadder(date.getMinutes(), 2);
            $scope.dueCheck = true;
            $scope.earlyJoining = true;
            $scope.enableDue2();
            $scope.addKeyListeners();

        };

        $scope.populateLectureForm = function (name) {
            $scope.lectureCode = name;
        };

        /**
         * This function is called if end date is selected. Sets boolean values to reflect this choice and sets
         * the default end time to 2 hours ahead of start time.
         * @memberof module:createLectureCtrl
         */
        $scope.enableDate2 = function () {
            $scope.dateCheck = true;
            $scope.dueCheck = false;
            $scope.endDate = $scope.startDate;
            $scope.endHour = $scope.leftPadder(parseInt($scope.startHour) + 2, 2);
            $scope.endMin = $scope.leftPadder($scope.startMin, 2);

            $scope.useDate = true;
            $scope.useDuration = false;
            $scope.durationHour = "";
            $scope.durationMin = "";
        };

        /**
         * Function for enabling fields and buttons for "Duration" and disabling them for "Use date". This function
         * is called when duration is chosen and is chosen by default.
         * @memberof module:createLectureCtrl
         */
        $scope.enableDue2 = function () {
            $scope.dateCheck = false;
            $scope.dueCheck = true;
            $scope.useDuration = true;
            $scope.useDate = false;
            $scope.endDay = "";
            $scope.endMonth = "";
            $scope.endYear = "";
            $scope.endHour = "";
            $scope.endMin = "";
            $scope.durationHour = "02";
            $scope.durationMin = "00";
        };

        /**
         * Remove border from given element.
         * @param element ID of the field whose border will be removed.
         * @memberof module:createLectureCtrl
         */
        $scope.defInputStyle = function (element) {
            if (element !== null || !element.isDefined) {
                angular.element("#" + element).css("border", "");
            }
        };

        /**
         * Checks if the value is between 0-23
         * @param element The value of the element to be validated.
         * @param val The ID of the input field so user can be notified of the error.
         * @memberof module:createLectureCtrl
         */
        $scope.isHour = function (element, val) {
            if (element === "" || isNaN(element) || element > 23 || element < 0) {
                $scope.errorize(val, "Hour has to be between 0 and 23.");
            }
        };

        $scope.isNumber = function (element, val) {
            console.log(element);
            if (!(element === "") && (isNaN(element) || element < 0)) {
                $scope.errorize(val, "Max number of students must be a positive number or empty.");
            }
        };

        /**
         * Checks if the value is between 0-59
         * @param element The value of the element to be validated.
         * @param val The ID of the input field so user can be notified of the error.
         * @memberof module:createLectureCtrl
         */
        $scope.isMinute = function (element, val) {
            if (element === "" || isNaN(element) || element > 59 || element < 0) {
                $scope.errorize(val, "Minutes has to be between 0 and 59.");
            }
        };

        /**
         * Checks if the number given is positive.
         * @param element The value of the element to be validated.
         * @param val The ID of the input field so user can be notified of the error.
         * @memberof module:createLectureCtrl
         */
        $scope.isPositiveNumber = function (element, val) {
            if (element === "" || isNaN(element) || element < 0) {
                $scope.errorize(val, "Number has to be positive.");
            }
        };

        /**
         * Function for validating that the date is of the format dd.mm.yyyy.
         * @param element The value of the element to be validated.
         * @param val The ID of the input field so user can be notified of the error.
         * @memberof module:createLectureCtrl
         */
        $scope.isDateValid = function (element, val) {
            var reg = new RegExp("^(0?[1-9]|[12][0-9]|3[01])[.]((0?[1-9]|1[012])[.](19|20)?[0-9]{2})*$");
            if (!reg.test(element)) {
                $scope.errorize(val, "Date is not of format dd.mm.yyyy or date is invalid.");
            }
        };

        /**
         * Translates date object to string in the form yyyy-mm-dd hh:mm
         * @param input JavaScript date object
         * @param include_time Boolean value whether to include the time or not
         * @returns {string} yyyy-mm-dd( hh:mm)
         * @memberof module:createLectureCtrl
         */
        $scope.dateObjectToString = function (input, include_time) {
            var output = $scope.leftPadder(input.getFullYear(), 4) + "-" +
                $scope.leftPadder(input.getMonth() + 1, 2) + "-" +
                $scope.leftPadder(input.getDate(), 2);
            if (include_time) {
                output += " " + $scope.leftPadder(input.getHours(), 2) + ":" +
                    $scope.leftPadder(input.getMinutes(), 2);
            }
            return output;
        };
        /**
         * Creates a new date object with the specified date and time
         * @param date_to_be_validated Date as a string in either seperated by dots or dashes.
         * @param time_hours
         * @param time_mins
         * @param splitter Date seperator.
         * @returns {Date} Returns a JavaScript date object.
         * @memberof module:createLectureCtrl
         */
        $scope.translateToDateObject = function (date_to_be_validated, time_hours, time_mins, splitter) {
            var parms = date_to_be_validated.split(splitter);
            var dd;
            var mm;
            var yyyy;

            if (splitter === ".") {
                dd = parseInt(parms[0], 10);
                mm = parseInt(parms[1], 10);
                yyyy = parseInt(parms[2], 10);
            } else {
                dd = parseInt(parms[2], 10);
                mm = parseInt(parms[1], 10);
                yyyy = parseInt(parms[0], 10);
            }
            var hours = parseInt(time_hours, 10);
            var mins = parseInt(time_mins, 10);
            return new Date(yyyy, mm - 1, dd, hours, mins, 0);
        };

        /**
         * Function for creating a new lecture and validation.
         * @memberof module:createLectureCtrl
         */
        $scope.submitLecture = function () {
            if ($scope.lectureId === undefined || $scope.lectureId === null) {
                $scope.editMode = false;
            }
            $scope.removeErrors();
            $scope.isDateValid($scope.startDate, "startDate");
            if ($scope.error_message <= 0) {
                $scope.start_date = $scope.translateToDateObject($scope.startDate, $scope.startHour, $scope.startMin, ".");
                if ($scope.endDate !== undefined, $scope.useDate) {
                    $scope.isDateValid($scope.endDate, "endDate");
                    $scope.end_date = $scope.translateToDateObject($scope.endDate, $scope.endHour, $scope.endMin, ".");
                } else {
                    $scope.end_date = "";
                }
            }

            /*This checks that "lecture code"-field is not empty.*/
            if ($scope.lectureCode === "") {
                $scope.errorize("lCode", "Lecture name must be entered!");
            }

            /*This checks that either "Use date" or "Duration" is chosen for ending time.*/
            if ($scope.dateCheck === false && $scope.dueCheck === false) {
                $scope.errorize("endInfo", "A date or duration must be chosen.");
            }
            /*Checks that hours in starting and ending time are between 0 and 23.
             Checks that minutes in starting and ending time are between 0 and 59*/
            $scope.isHour($scope.startHour, "startHour");
            $scope.isMinute($scope.startMin, "startMin");
            $scope.isNumber($scope.maxStudents, "maxStudents");

            if ($scope.start_date !== undefined) {
                var now_hours = date.getHours();
                var now_minutes = date.getMinutes();
                var now_date_object = $scope.translateToDateObject($scope.dateObjectToString(date, false), now_hours, now_minutes, "-");
                var lecture_starting_in_past = $scope.start_date - now_date_object < 0;
                var lecture_ending_in_past;

                /* Checks that are run if end date is used*/
                if ($scope.useDate && $scope.end_date !== undefined) {
                    $scope.isHour($scope.endHour, "endHour");
                    $scope.isMinute($scope.endMin, "endMin");
                    if ($scope.end_date - $scope.start_date < 120000) {
                        $scope.errorize("endDateDiv", "Lecture has to last at least two minutes.");
                    }
                    $scope.endDateForDB = $scope.dateObjectToString($scope.end_date, true);
                }

                /* Check that are run if duration is used. */
                if ($scope.useDuration) {
                    if ($scope.durationHour === "") {
                        $scope.durationHour = "00";
                    }
                    if ($scope.durationMin === "") {
                        $scope.durationMin = "00";
                    }
                    $scope.isPositiveNumber($scope.durationHour, "durationHour");
                    $scope.isPositiveNumber($scope.durationMin, "durationMin");
                    if ($scope.durationHour.length <= 0 && $scope.durationMin.length <= 0) {
                        $scope.errorize("durationDiv", "Please give a duration.");
                    }
                    $scope.end_date = new Date($scope.start_date.getTime());
                    $scope.end_date.setHours($scope.start_date.getHours() + parseInt($scope.durationHour));
                    $scope.end_date.setMinutes($scope.start_date.getMinutes() + parseInt($scope.durationMin));
                    if ($scope.end_date - $scope.start_date < 120000) {
                        $scope.errorize("durationDiv", "Lecture has to last at least two minutes.");
                    }
                    $scope.endDateForDB = $scope.dateObjectToString($scope.end_date, true);
                }
                var alert_message = "";
                lecture_ending_in_past = $scope.end_date - now_date_object <= 0;
                /* Confirmations if lecture starts and/or ends before the current date */
                if (lecture_starting_in_past && !$scope.editMode) {
                    alert_message += "Are you sure you want the lecture to start before now? ";
                }
                if (lecture_ending_in_past && !$scope.editMode) {
                    alert_message += "Are you sure that the lecture ends in the past or now and will not run?";
                }
                $window.console.log($scope.error_message.length);
                if (alert_message !== "" && $scope.error_message.length <= 0) {
                    if (!$window.confirm(alert_message)) {
                        if (lecture_starting_in_past) {
                            $scope.errorize("startInfo", "Please select another date and time.");
                        }
                        if (lecture_ending_in_past) {
                            $scope.errorize("endInfo", "Please select another date or duration.");
                        }
                    }
                }
            }
            /* If no errors save the lecture to the database */
            if ($scope.error_message <= 0) {
                if ($scope.earlyJoining) {
                    $scope.start_date = new Date($scope.start_date - 900000); // adds 15 minutes
                }
                $scope.startDateForDB = $scope.dateObjectToString($scope.start_date, true);
                $http({
                    url: '/createLecture',
                    method: 'POST',
                    params: {
                        'lecture_id': $scope.lectureId,
                        'doc_id': $scope.docId,
                        'lecture_code': $scope.lectureCode,
                        'password': $scope.password,
                        'start_date': $scope.start_date,
                        // 'start_date': $scope.startDateForDB,
                        // 'end_date': $scope.endDateForDB,
                        'end_date': $scope.end_date,
                        'max_students': $scope.maxStudents || ''
                    }
                })
                    .success(function (answer) {
                        if ($scope.editMode) {
                            $window.console.log("Lecture " + answer.lectureId + " updated.");
                        }
                        else {
                            $window.console.log("Lecture created: " + answer.lectureId);
                        }
                        $scope.$parent.lectureSettings.useWall = true;
                        $scope.$parent.useAnswers = true;
                        $scope.clearForm();
                        $scope.$emit("closeLectureForm", true);
                        $scope.$emit("lectureUpdated", $scope.lectureCode);
                    })
                    .error(function (answer) {
                        $scope.error_message += answer.error;
                        $window.console.log(answer);
                    });
            }
        };

        /**
         * Changes the border of the element to red.
         * @param div_val The ID of the input field so user can be notified of the error.
         * @param error_text Error text that will be printed if the error occurs.
         * @memberof module:createLectureCtrl
         */
        $scope.errorize = function (div_val, error_text) {
            angular.element("#" + div_val).css('border', "1px solid red");
            if (error_text.length > 0) {
                $scope.error_message += error_text + "<br />";
            }
        };

        /**
         * Calls defInputStyle for all the form elements.
         * @memberof module:createLectureCtrl
         */
        $scope.removeErrors = function () {
            $scope.error_message = "";

            var elementsToRemoveErrorsFrom = [
                "lCode",
                "startDate",
                "startHour",
                "startMin",
                "startInfo",
                "endInfo",
                "endDate",
                "endHour",
                "endMin",
                "endDateDiv",
                "durationDiv",
                "durationHour",
                "durationMin",
                "maxStudents"
            ];
            for (var i = 0; i < elementsToRemoveErrorsFrom.length; i++) {
                if (elementsToRemoveErrorsFrom[i] !== undefined) {
                    $scope.defInputStyle(elementsToRemoveErrorsFrom[i]);
                }
            }
        };

        /**
         *  Resets all the values of the form.
         *  @memberof module:createLectureCtrl
         */
        $scope.clearForm = function () {
            $scope.lectureCode = "";
            $scope.password = "";
            $scope.startDate = "";
            $scope.endDate = "";
            $scope.startHour = "";
            $scope.startMin = "";
            $scope.durationMin = "";
            $scope.durationHour = "";
            $scope.endHour = "";
            $scope.endMin = "";
            $scope.showLectureCreation = false;
            $scope.removeErrors();
            $scope.useDate = false;
            $scope.useDuration = true;
            $scope.dateChosen = false;
            $scope.durationChosen = false;
            $scope.dateCheck = false;
            $scope.lectureId = null;
        };

        /**
         * Function for adding preceding zeroes to a number to make it of desired length.
         * @param number Number to be padded.
         * @param size How long should the number be.
         * @returns {string} Returns the number in the padded length.
         * @memberof module:createLectureCtrl
         */
        $scope.leftPadder = function (number, size) {
            var paddedNumber = "" + number;
            var len = paddedNumber.length;
            while (len < size) {
                paddedNumber = "0" + paddedNumber;
                len++;
            }
            return paddedNumber;
        };

        /**
         * Function for cancelling the lecture creation.
         * @memberof module:createLectureCtrl
         */
        $scope.cancelCreation = function () {
            $scope.editMode = false;
            $scope.$emit("closeLectureForm");
            $scope.clearForm();
        };

        $scope.$watch('lectureCode', function () {
            $scope.lectureCodeEncoded = encodeURIComponent($scope.lectureCode);
        });

        $scope.$watch('hostName', function () {
            $scope.hostName = encodeURIComponent(location.host);
        });
    }
]);