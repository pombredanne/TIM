/**
 * Defines the client-side implementation of an example plugin (a numericfield checker).
 */
import angular, {INgModelOptions} from "angular";
import * as t from "io-ts";
import {ITimComponent, ViewCtrl} from "tim/document/viewctrl"
import {GenericPluginMarkup, nullable, PluginBase, withDefault} from "tim/plugin/util";
import {$http} from "tim/util/ngimport";
import {to} from "tim/util/utils";
import {valueDefu} from "tim/util/utils"; //reset-metodille
import {fieldNumber} from "../../../static/scripts/jspm_packages/npm/fp-ts@1.11.1/lib/Field";
import {number} from "../../../static/scripts/jspm_packages/npm/io-ts@1.4.1/lib";
import * as ts from "../../../static/scripts/jspm_packages/npm/typescript@3.0.1/lib/tsserverlibrary";
import emptyArray = ts.server.emptyArray;

const numericfieldApp = angular.module("numericfieldApp", ["ngSanitize"]);
export const moduleDefs = [numericfieldApp];

const NumericfieldMarkup = t.intersection([
    t.partial({
        initnumber: t.number,
        inputplaceholder: nullable(t.number),
        inputstem: t.number,
        followid: t.string,
        onefield: t.string,
        manyfields: t.array(t.string)
    }),
    GenericPluginMarkup,
    t.type({
        // all withDefaults should come here; NOT in t.partial
        autoupdate: withDefault(t.number, 500),
        cols: withDefault(t.number, 20),
    }),
]);
const NumericfieldAll = t.intersection([
    t.partial({
        numericvalue: t.number,
    }),
    t.type({markup: NumericfieldMarkup}),
]);

class NumericfieldController extends PluginBase<t.TypeOf<typeof NumericfieldMarkup>, t.TypeOf<typeof NumericfieldAll>, typeof NumericfieldAll> implements ITimComponent {
    private result?: string;
    private error?: string;
    private isRunning = false;
    private numericvalue?: number;
    private modelOpts!: INgModelOptions; // initialized in $onInit, so need to assure TypeScript with "!"
    private vctrl!: ViewCtrl;

    getDefaultMarkup() {
        return {};
    }

    buttonText() {
        return super.buttonText() || "Save";
    }

    $onInit() {
        super.$onInit();
        this.numericvalue = this.attrsall.numericvalue || this.attrs.initnumber || undefined;
        this.modelOpts = {debounce: this.autoupdate};
        if (this.attrs.followid) {
            this.vctrl.addTimComponent(this, this.attrs.followid || this.pluginMeta.getTaskId() || "");
        }
    }

    getContent(): string {
        return; // not used with numericfield plugin, but promised to implement in ITimComponent
    }

    getNumericContent(): number {
        return this.numericvalue;
    }

    save(): string {
        return this.numericvalue.toString(); // not used with textfield plugin, but promised to implement in ITimComponent
    }

    get autoupdate(): number {
        return this.attrs.autoupdate;
    }

    get inputstem() {
        return this.attrs.inputstem || null;
    }

    get cols() {
        return this.attrs.cols;
    }

    initCode() {
        this.numericvalue = undefined;
        this.error = undefined;
        this.result = undefined;
    }

    saveText() {
        this.doSaveText(false);
    }

    async doSaveText(nosave: boolean) {
        this.error = "... saving ...";
        this.isRunning = true;
        this.result = undefined;
        const params = {
            input: {
                nosave: false,
                numericvalue: this.numericvalue,
            },
        };

        if (nosave) {
            params.input.nosave = true;
        }
        const url = this.pluginMeta.getAnswerUrl();
        const r = await to($http.put<{web: {result: string, error?: string}}>(url, params));
        this.isRunning = false;
        if (r.ok) {
            const data = r.result.data;
            this.error = data.web.error;
            this.result = data.web.result;
        } else {
            this.error = "Infinite loop or some other error?";
        }
    }

    protected getAttributeType() {
        return NumericfieldAll;
    }
}

numericfieldApp.component("numericfieldRunner", {
    bindings: {
        json: "@",
    },
    controller: NumericfieldController,
    template: `
<div class="numericfieldNoSaveDiv">
    <h4 ng-if="::$ctrl.header" ng-bind-html="::$ctrl.header"></h4>
    <p ng-if="::$ctrl.stem">{{::$ctrl.stem}}</p>
    <div class="form-inline"><label>{{::$ctrl.inputstem}} <span>   
        <input type="number"
               class="form-control"
               ng-model="$ctrl.numericvalue"
               ng-model-options="::$ctrl.modelOpts"
               ng-trim="false"
               placeholder="{{::$ctrl.inputplaceholder}}"
               size="{{::$ctrl.cols}}"></span></label>
    </div>
    <pre ng-if="$ctrl.result">{{$ctrl.result}}</pre>
    <p ng-if="::$ctrl.footer" ng-bind="::$ctrl.footer" class="plgfooter"></p>
</div> `,
});

numericfieldApp.component("numericfieldRunner2", {
    bindings: {
        json: "@",
    },
    controller: NumericfieldController,
    template: `
<div class="numericfieldSaveDiv">
    <h4 ng-if="::$ctrl.header" ng-bind-html="::$ctrl.header"></h4>
    <p ng-if="::$ctrl.stem">{{::$ctrl.stem}}</p>
    <div class="form-inline"><label>{{::$ctrl.inputstem}} <span>   
        <input type="number"
               class="form-control"
               ng-model="$ctrl.numericvalue"
               ng-model-options="::$ctrl.modelOpts"
               ng-trim="false"
               placeholder="{{::$ctrl.inputplaceholder}}"
               size="{{::$ctrl.cols}}"></span></label>
    </div>
    <button class="timButton"
            ng-if="::$ctrl.buttonText()"
            ng-disabled="$ctrl.isRunning || !$ctrl.numericvalue"
            ng-click="$ctrl.saveText()">
        {{::$ctrl.buttonText()}}
    </button>
    <pre ng-if="$ctrl.result">{{$ctrl.result}}</pre>
    <p ng-if="::$ctrl.footer" ng-bind="::$ctrl.footer" class="plgfooter"></p>
</div> `,
});
