import {IController, IScope} from "angular";
import {timApp} from "../app";
import {$http, $window} from "../ngimport";

type PreviewList = Array<{from: string, to: string}>;

class CopyFolderCtrl implements IController {
    private static $inject = ["$scope"];
    private copyingFolder: "notcopying" | "copying" | "finished";
    private item: any;
    private copyPreviewList: PreviewList;
    private scope: IScope;
    private copyFolderPath: string;
    private copyFolderExclude: string;
    private newFolder: any;

    constructor(scope: IScope) {
        this.scope = scope;
    }

    $onInit() {
        this.copyFolderPath = this.item.path;
        this.copyingFolder = "notcopying";
        this.copyFolderExclude = "";
    }

    async copyFolderPreview(path: string, exclude: string) {
        this.copyingFolder = "notcopying";
        try {
            const result = await $http.post<PreviewList>(`/copy/${this.item.id}/preview`, {
                destination: path,
                exclude: exclude,
            });
            this.copyPreviewList = result.data;
        } catch (e) {
            $window.alert(e.data.error);
        }
        this.scope.$apply();
    }

    async copyFolder(path: string, exclude: string) {
        this.copyingFolder = "copying";
        try {
            const result = await $http.post(`/copy/${this.item.id}`, {destination: path, exclude: exclude});
            this.copyingFolder = "finished";
            this.copyPreviewList = null;
            this.newFolder = result.data;
            this.scope.$apply();
        } catch (e) {
            this.copyingFolder = "notcopying";
            this.scope.$apply();
            $window.alert(e.data.error);
        }
    }

    copyParamChanged() {
        this.copyPreviewList = null;
    }
}

timApp.component("timCopyFolder", {
    bindings: {
        item: "<",
    },
    controller: CopyFolderCtrl,
    template: `
<form name="copyForm">
    <p>You can copy all documents and folders in this folder to another folder.</p>
    <div class="form-group" tim-error-state data-for="copyForm.copyPath">
        <label for="destination" class="control-label">Destination:</label>
        <input name="copyPath" class="form-control" tim-location id="destination" type="text" autocomplete="off"
               ng-model="$ctrl.copyFolderPath" ng-change="$ctrl.copyParamChanged()">
        <tim-error-message for="copyForm.copyPath"></tim-error-message>
    </div>
    <p>You can optionally exclude some documents/folders from being copied.</p>
    <div class="form-group" tim-error-state data-for="copyForm.exclude">
        <label for="exclude" class="control-label">Exclude documents/folders that match:</label>
        <input name="exclude" class="form-control" id="exclude" type="text" autocomplete="off"
               ng-model="$ctrl.copyFolderExclude" ng-change="$ctrl.copyParamChanged()">
        <tim-error-message for="copyForm.exclude"></tim-error-message>
    </div>
    <button ng-click="$ctrl.copyFolderPreview($ctrl.copyFolderPath, $ctrl.copyFolderExclude)" class="timButton"
            ng-disabled="$ctrl.copyFolderPath === $ctrl.item.path ||
            copyForm.copyPath.$invalid"
            ng-show="$ctrl.copyingFolder === 'notcopying'">Copy preview...
    </button>
    <ul ng-show="$ctrl.copyPreviewList.length > 0">
        <li ng-repeat="p in $ctrl.copyPreviewList"><span ng-bind="p.from"></span> <i
                class="glyphicon glyphicon-arrow-right"></i> <span ng-bind="p.to"></span></li>
    </ul>
    <p ng-show="$ctrl.copyPreviewList.length === 0">Nothing would be copied.</p>
    <button ng-click="$ctrl.copyFolder($ctrl.copyFolderPath, $ctrl.copyFolderExclude)" class="timButton"
            ng-show="$ctrl.copyFolderPath !== item.path &&
                     $ctrl.copyPreviewList.length > 0 &&
                     $ctrl.copyingFolder === 'notcopying'">Copy
    </button>
    <span ng-show="$ctrl.copyingFolder === 'copying'">Copying...</span>
    <span ng-show="$ctrl.copyingFolder === 'finished'">
    Folder {{ $ctrl.item.name }} copied to
    <a href="/manage/{{ $ctrl.newFolder.path }}" ng-bind="$ctrl.newFolder.path"></a>.
    </span>
</form>
    `,
});
