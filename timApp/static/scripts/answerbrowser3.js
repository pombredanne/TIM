var timLogTime;
timLogTime("answerbrowser3 load","answ");

var angular;
var timApp = angular.module('timApp');
var LAZYWORD = "lazylazylazy";
var LAZYSTART="<!--lazy ";
var LAZYEND =" lazy-->";
var RLAZYSTART = new RegExp(LAZYSTART, 'g');
var RLAZYEND = new RegExp(LAZYEND, 'g');


function makeNotLazy(html) {
    "use strict";
    var s = html.replace(RLAZYSTART,"");
    var i = s.lastIndexOf(LAZYEND);
    if ( i >= 0 ) s = s.substring(0,i);
    s = s.replace(RLAZYEND,""); 
    s = s.replace(/-LAZY->/g,"-->");
    s = s.replace(/<!-LAZY-/g,"<!--");
    return s;
}

timApp.directive("answerbrowserlazy", ['Upload', '$http', '$sce', '$compile', '$window',
    function (Upload, $http, $sce, $compile, $window) {
        "use strict";
        timLogTime("answerbrowserlazy directive function","answ");
        return {
            restrict: 'E',
            scope: {
                taskId: '@'
            },

            controller: function ($scope) {
                timLogTime("answerbrowserlazy ctrl function", "answ", 1);
                $scope.compiled = false;

                /**
                 * Returns whether the given task id is valid.
                 * A valid task id is of the form '1.taskname'.
                 * @param taskId {string} The task id to validate.
                 * @returns {boolean} True if the task id is valid, false otherwise.
                 */
                $scope.isValidTaskId = function (taskId) {
                    return taskId.slice(-1) !== ".";
                };

                $scope.loadAnswerBrowser = function () {
                    var plugin = $scope.$element.parents('.par').find('.parContent');
                    if ( $scope.compiled ) return;
                    $scope.compiled = true;
                    if (!$scope.$parent.noBrowser && $scope.isValidTaskId($scope.taskId)) {
                        var newHtml = '<answerbrowser task-id="' + $scope.taskId + '"></answerbrowser>';
                        var newElement = $compile(newHtml);
                        var parent = $scope.$element.parents(".par")[0];
                        parent.replaceChild(newElement($scope.$parent)[0], $scope.$element[0]);
                    }
                    // Next the inside of the plugin to non lazy
                    var origHtml = plugin[0].innerHTML;
                    if ( origHtml.indexOf(LAZYSTART) < 0 ) {
                        plugin = null;
                    }
                    if ( plugin ) {
                        var newPluginHtml = makeNotLazy(origHtml);
                        var newPluginElement = $compile(newPluginHtml);
                        plugin.html(newPluginElement($scope));
                        $scope.$parent.processAllMathDelayed(plugin);
                    }
                };
            },
            
            link: function ($scope, $element, $attrs) {
                timLogTime("answerbrowserlazy link function","answ",1);
                $scope.$element = $element;
                $element.parent().on('mouseenter touchstart', $scope.loadAnswerBrowser);
            }
        };
    }]);


timApp.directive("answerbrowser", ['Upload', '$http', '$sce', '$compile', '$window', '$filter', '$uibModal', 'Users',
    function (Upload, $http, $sce, $compile, $window, $filter, $uibModal, Users) {
        "use strict";
        timLogTime("answerbrowser directive function","answ");
        return {
            templateUrl: "/static/templates/answerBrowser.html",
            restrict: 'E',
            scope: {
                taskId: '@'
            },
            controller: function ($scope) {
            },
            link: function ($scope, $element, $attrs) {
                $scope.element = $element.parents('.par');
                $scope.parContent = $scope.element.find('.parContent');
                //$scope.$parent = $scope.$parent; // muutos koska scope on syntynyt tuon toisen lapseksi
                timLogTime("answerbrowser link","answ");



                $scope.$watch("taskId", function (newValue, oldValue) {
                    if (newValue === oldValue) {
                        return;
                    }
                    if ($scope.$parent.teacherMode) {
                        $scope.getAvailableUsers();
                    }
                    $scope.getAvailableAnswers();
                });

                $scope.savePoints = function () {
                    $http.put('/savePoints/' + $scope.user.id + '/' + $scope.selectedAnswer.id,
                        {points: $scope.points}).then(function (response) {
                        $scope.selectedAnswer.points = $scope.points;
                    }, function (response) {
                        $window.alert('Error settings points: ' + response.data.error);
                    });
                };

                $scope.updatePoints = function () {
                    $scope.points = $scope.selectedAnswer.points;
                    if ($scope.points !== null) {
                        $scope.giveCustomPoints = $scope.selectedAnswer.last_points_modifier !== null;
                    } else {
                        $scope.giveCustomPoints = false;
                    }
                };

                $scope.loading = 0;
                $scope.setFocus = function() {
                    $scope.element.focus();
                };

                $scope.changeAnswer = function () {
                    if ($scope.selectedAnswer === null) {
                        return;
                    }
                    $scope.updatePoints();
                    var $par = $scope.element;
                    var par_id = $scope.$parent.getParId($par);
                    $scope.loading++;
                    $http.get('/getState', {
                        params: {
                            doc_id: $scope.$parent.docId,
                            par_id: par_id,
                            user_id: $scope.user.id,
                            answer_id: $scope.selectedAnswer.id,
                            review: $scope.review
                        }
                    }).success(function (data, status, headers, config) {
                        var newhtml = makeNotLazy(data.html);
                        var plugin = $par.find('.parContent');
                        plugin.html($compile(newhtml)($scope));
                        plugin.css('opacity', '1.0');
                        $scope.$parent.processAllMathDelayed(plugin);
                        if ($scope.review) {
                            $scope.element.find('.review').html(data.reviewHtml);
                        }
                        var lata = $scope.$parent.loadAnnotationsToAnswer;
                        if ( lata ) lata($scope.selectedAnswer.id, par_id, $scope.review, $scope.setFocus);

                    }).error(function (data, status, headers, config) {
                        $scope.error = 'Error getting state: ' + data.error;
                    }).finally(function () {
                        $scope.loading--;
                    });


                };

                // Loads annotations to answer
                setTimeout($scope.changeAnswer, 500); //TODO: Don't use timeout

                $scope.next = function () {
                    var newIndex = $scope.findSelectedAnswerIndex() - 1;
                    if (newIndex < 0) {
                        newIndex = $scope.filteredAnswers.length - 1;
                    }
                    $scope.selectedAnswer = $scope.filteredAnswers[newIndex];
                    $scope.changeAnswer();
                };

                $scope.previous = function () {
                    var newIndex = $scope.findSelectedAnswerIndex() + 1;
                    if (newIndex >= $scope.filteredAnswers.length) {
                        newIndex = 0; 
                    }
                    $scope.selectedAnswer = $scope.filteredAnswers[newIndex];
                    $scope.changeAnswer();
                };


                if ( $scope.$parent.teacherMode ) {
                    $scope.findSelectedUserIndex = function() {
                        if ($scope.users === null) {
                            return -1;
                        }
                        for (var i = 0; i < $scope.users.length; i++) {
                            if ($scope.users[i].id === $scope.user.id) {
                                return i;
                            }
                        }
                        return -1;
                    };

                    $scope.checkKeyPress = function(e) {
                        if ( e.which === 38 && e.ctrlKey ) {
                            e.preventDefault();
                            $scope.changeStudent(-1);
                        }
                        if ( e.which === 40 && e.ctrlKey ) {
                            e.preventDefault();
                            $scope.changeStudent(1);
                        }
                    };
                    $scope.element.attr("tabindex", 1);
                    $scope.element.css("outline", "none");
                    $scope.element[0].addEventListener("keydown", $scope.checkKeyPress);

                    $scope.changeStudent = function (dir) {
                        if ( $scope.users.length <= 0 ) return;
                        var newIndex = $scope.findSelectedUserIndex() + dir;
                        if (newIndex >= $scope.users.length) {
                            newIndex = 0;
                        }
                        if (newIndex < 0 ) {
                            newIndex = $scope.users.length-1;
                        }
                        if (newIndex < 0) return;
                        $scope.user = $scope.users[newIndex];
                        $scope.getAvailableAnswers();
                        $scope.element.focus();
                    };
                }


                $scope.setNewest = function () {
                    if ($scope.filteredAnswers.length > 0) {
                        $scope.selectedAnswer = $scope.filteredAnswers[0];
                        $scope.changeAnswer();
                    }
                };

                $scope.setAnswerById = function(id) {
                    for (var i=0; i<$scope.filteredAnswers.length; i++){
                        if ($scope.filteredAnswers[i].id === id){
                            $scope.selectedAnswer = $scope.filteredAnswers[i];
                            $scope.changeAnswer();
                            break;
                        }
                    }
                };

                $scope.indexOfSelected = function () {
                    if ( !$scope.filteredAnswers || !$scope.selectedAnswer ) return -1;
                    var arrayLength = $scope.filteredAnswers.length;
                    for (var i = 0; i < arrayLength; i++) {
                        if ($scope.filteredAnswers[i].id === $scope.selectedAnswer.id) {
                            return i;
                        }
                    }
                    return -1;
                };

                $scope.getBrowserData = function () {
                    if ($scope.answers.length > 0 && $scope.selectedAnswer)
                        return {
                            answer_id: $scope.selectedAnswer.id,
                            saveTeacher: $scope.saveTeacher,
                            teacher: $scope.$parent.teacherMode,
                            points: $scope.points,
                            giveCustomPoints: $scope.giveCustomPoints,
                            userId: $scope.user.id,
                            saveAnswer: !$scope.$parent.noBrowser
                        };
                    else
                        return {
                            saveTeacher: false,
                            teacher: $scope.$parent.teacherMode,
                            saveAnswer: !$scope.$parent.noBrowser
                        };
                };

                $scope.getAvailableUsers = function () {
                    $scope.loading++;
                    $http.get('/getTaskUsers/' + $scope.taskId, {params: {group: $scope.$parent.group}})
                        .success(function (data, status, headers, config) {
                            $scope.users = data;
                        }).error(function (data, status, headers, config) {
                            $scope.error = 'Error getting users: ' + data.error;
                        }).finally(function () {
                            $scope.loading--;
                        });
                };

                $scope.getAvailableAnswers = function (updateHtml) {
                    updateHtml = (typeof updateHtml === "undefined") ? true : updateHtml;
                    if ( !$scope.$parent.rights || !$scope.$parent.rights.browse_own_answers) {
                        return;
                    }
                    if ($scope.user === null) {
                        return;
                    }
                    $scope.loading++;
                    $http.get('/answers/' + $scope.taskId + '/' + $scope.user.id)
                        .success(function (data, status, headers, config) {
                            if (data.length > 0 && ($scope.hasUserChanged() || data.length !== ($scope.answers || []).length)) {
                                $scope.answers = data;
                                $scope.selectedAnswer = $scope.answers[0];
                                $scope.updatePoints();
                                if (updateHtml) {
                                    $scope.changeAnswer();
                                }
                            } else {
                                $scope.answers = data;
                                if ($scope.answers.length === 0 && $scope.$parent.teacherMode) {
                                    $scope.dimPlugin();
                                }
                                $scope.updateFiltered();
                                var i = $scope.findSelectedAnswerIndex();
                                if (i >= 0) {
                                    $scope.selectedAnswer = $scope.filteredAnswers[i];
                                    $scope.updatePoints();
                                }
                            }
                            $scope.fetchedUser = $scope.user;
                        }).error(function (data, status, headers, config) {
                            $scope.error = 'Error getting answers: ' + data.error;
                        }).finally(function () {
                            $scope.loading--;
                        });
                };

                $scope.$on('answerSaved', function (event, args) {
                    if (args.taskId === $scope.taskId) {
                        $scope.getAvailableAnswers(false);
                        // HACK: for some reason the math mode is lost because of the above call, so we restore it here
                        $scope.$parent.processAllMathDelayed($scope.element.find('.parContent'));
                    }
                });

                $scope.hasUserChanged = function () {
                    return ($scope.user || {}).id !== ($scope.fetchedUser || {}).id;
                };

                $scope.$on('userChanged', function (event, args) {
                    $scope.user = args.user;
                    $scope.firstLoad = false;
                    $scope.shouldUpdateHtml = true;
                    if (args.updateAll) {
                        $scope.loadIfChanged();
                    }
                    else if ($scope.hasUserChanged()) {
                        $scope.dimPlugin();
                    } else {
                        $scope.parContent.css('opacity', '1.0');
                    }
                });

                $scope.dimPlugin = function () {
                    $scope.parContent.css('opacity', '0.3');
                };

                $scope.allowCustomPoints = function () {
                    if ($scope.taskInfo === null) {
                        return false;
                    }
                    return $scope.taskInfo.userMin !== null && $scope.taskInfo.userMax !== null;
                };

                $scope.loadIfChanged = function () {
                    if ($scope.hasUserChanged()) {
                        $scope.getAvailableAnswers($scope.shouldUpdateHtml);
                        $scope.loadInfo();
                        $scope.firstLoad = false;
                        $scope.shouldUpdateHtml = false;
                    }
                };

                $scope.showTeacher = function () {
                    return $scope.$parent.teacherMode && $scope.$parent.rights.teacher;
                };

                $scope.getTriesLeft = function () {
                    if ($scope.taskInfo === null) {
                        return null;
                    }
                    return Math.max($scope.taskInfo.answerLimit - $scope.answers.length, 0);
                };

                $scope.loadInfo = function () {
                    if ($scope.taskInfo !== null) {
                        return;
                    }
                    $scope.loading++;
                    $http.get('/taskinfo/' + $scope.taskId)
                        .success(function (data, status, headers, config) {
                            $scope.taskInfo = data;
                        }).error(function (data, status, headers, config) {
                            $scope.error = 'Error getting taskinfo: ' + data.error;
                        }).finally(function () {
                            $scope.loading--;
                        });
                };

                
                $scope.checkUsers = function () {
                    if ($scope.loading > 0) {
                        return;
                    }
                    $scope.loadIfChanged();
                    if ($scope.$parent.teacherMode && $scope.users === null) {
                        $scope.users = [];
                        if ($scope.$parent.users.length > 0) {
                            $scope.getAvailableUsers();
                        }
                    }
                };

                $scope.getAllAnswers = function () {
                    $uibModal.open({
                        animation: false,
                        ariaLabelledBy: 'modal-title',
                        ariaDescribedBy: 'modal-body',
                        templateUrl: '/static/templates/allAnswersOptions.html',
                        controller: 'AllAnswersCtrl',
                        controllerAs: '$ctrl',
                        size: 'md',
                        resolve: {
                            options: function () {
                                return {
                                    url: '/allAnswersPlain/' + $scope.taskId
                                };
                            }
                        }
                    });
                };

                $scope.findSelectedAnswerIndex = function () {
                    if ($scope.filteredAnswers === null) {
                        return -1;
                    }
                    for (var i = 0; i < $scope.filteredAnswers.length; i++) {
                        if ($scope.filteredAnswers[i].id === $scope.selectedAnswer.id) {
                            return i;
                        }
                    }
                    return -1;
                };

                if ( $scope.$parent.selectedUser ) {
                    $scope.user = $scope.$parent.selectedUser;
                }
                else if ($scope.$parent && $scope.$parent.users && $scope.$parent.users.length > 0) { 
                    $scope.user = $scope.$parent.users[0];
                } else {
                    $scope.user = Users.getCurrent();
                }

                $scope.fetchedUser = null;
                $scope.firstLoad = true;
                $scope.shouldUpdateHtml = $scope.$parent.users.length > 0 && $scope.user !== $scope.$parent.users[0];
                if ($scope.shouldUpdateHtml) {
                    $scope.dimPlugin();
                }
                $scope.saveTeacher = false;
                $scope.users = null;
                $scope.answers = [];
                $scope.filteredAnswers = [];
                $scope.onlyValid = true;
                $scope.selectedAnswer = null;
                $scope.taskInfo = null;
                $scope.anyInvalid = false;
                $scope.giveCustomPoints = false;
                $scope.review = false;

                $scope.updateFiltered = function (newValues, oldValues, scope) {
                    $scope.anyInvalid = false;
                    $scope.filteredAnswers = $filter('filter')($scope.answers, function (value, index, array) {
                        if (value.valid) {
                            return true;
                        }
                        $scope.anyInvalid = true;
                        return !$scope.onlyValid;
                    });
                    if ($scope.findSelectedAnswerIndex() < 0) {
                        $scope.setNewest();
                    }
                };

                $scope.$watch('review', $scope.changeAnswer);
                $scope.$watchGroup(['onlyValid', 'answers'], $scope.updateFiltered);

                // call checkUsers automatically for now; suitable only for lazy mode!
                $scope.checkUsers();
                $element.parent().on('mouseenter touchstart', function () {
                    $scope.checkUsers();
                });
            }
        };
    }]);
