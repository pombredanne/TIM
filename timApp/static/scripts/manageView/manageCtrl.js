var PermApp = angular.module('permApp', ['ngSanitize', 'angularFileUpload']);

PermApp.directive('focusMe', function ($timeout) {
    return {
        link: function (scope, element, attrs) {
            scope.$watch(attrs.focusMe, function (value) {
                if (value === true) {
                    // $timeout(function() {
                    element[0].focus();
                    element[0].select();
                    scope[attrs.focusMe] = false;
                    // });
                }
            });
        }
    };
});

PermApp.controller("PermCtrl", [
    '$scope',
    '$http',
    '$upload',
    function (sc, $http, $upload) {
        sc.editors = editors;
        sc.viewers = viewers;
        sc.doc = doc;
        sc.newName = doc.name;
        doc.fulltext = doc.fulltext.trim();
        sc.fulltext = doc.fulltext;

        sc.removeConfirm = function (group, type) {
            if (confirm("Are you sure you want to remove this usergroup?")) {
                sc.removePermission(group, type);
            }
        };

        sc.getPermissions = function () {
            $http.get('/getPermissions/' + sc.doc.id).success(function (data, status, headers, config) {
                sc.editors = data.editors;
                sc.viewers = data.viewers;
            }).error(function (data, status, headers, config) {
                alert("Could not fetch permissions.");
            });
        };

        sc.removePermission = function (group, type) {
            $http.put('/removePermission/' + sc.doc.id + '/' + group.UserGroup_id + '/' + type).success(
                function (data, status, headers, config) {
                    sc.getPermissions();
                }).error(function (data, status, headers, config) {
                    alert(data.error);
                });
        };

        sc.addPermission = function (groupname, type) {
            $http.put('/addPermission/' + sc.doc.id + '/' + groupname + '/' + type).success(
                function (data, status, headers, config) {
                    sc.getPermissions();
                }).error(function (data, status, headers, config) {
                    alert(data.error);
                });
            sc.showAddEditor = false;
            sc.showAddViewer = false;
        };

        sc.renameDocument = function (newName) {
            $http.put('/rename/' + sc.doc.id, {
                'new_name': newName
            }).success(function (data, status, headers, config) {
                sc.doc.name = newName;
            }).error(function (data, status, headers, config) {
                alert(data.error);
            });
        };

        sc.deleteDocument = function (doc) {
            if (confirm('Are you sure you want to delete this document?')) {
                $http.delete('/documents/' + doc)
                    .success(function (data, status, headers, config) {
                        location.replace('/');
                    }).error(function (data, status, headers, config) {
                        alert(data.error);
                    });
            }
        };

        sc.onFileSelect = function (url, $files) {
            // $files: an array of files selected, each file has name, size,
            // and type.
            sc.progress = 'Uploading... ';
            sc.uploadInProgress = true;
            for (var i = 0; i < $files.length; i++) {
                var file = $files[i];
                sc.upload = $upload.upload({
                    url: url,
                    method: 'POST',
                    file: file
                }).progress(function (evt) {
                    sc.progress = 'Uploading... ' + parseInt(100.0 * evt.loaded / evt.total) + '%';
                }).success(function (data, status, headers, config) {
                    sc.doc.versions = data;
                    $http.get('/download/' + sc.doc.id).success(function (data) {
                        sc.doc.fulltext = data;
                        sc.fulltext = data;
                        sc.progress = 'Uploading... Done!';
                    })
                }).error(function (data, status, headers, config) {
                    sc.progress = 'Error occurred: ' + data.error;
                }).then(function () {
                    sc.uploadInProgress = false;
                });
            }
        };

        sc.updateDocument = function (doc, $files) {
            sc.onFileSelect('/update/' + doc.id + '/' + doc.versions[0].hash, $files);
        };

        sc.saveDocument = function (doc) {
            sc.saving = true;
            $http.post('/update/' + doc.id + '/' + doc.versions[0].hash, {'fulltext': sc.fulltext}).success(
                function (data, status, headers, config) {
                    sc.doc.fulltext = sc.fulltext;
                    sc.doc.versions = data;
                }).error(function (data, status, headers, config) {
                    alert(data.error);
                }).then(function () {
                    sc.saving = false;
                });
        };

    }]);