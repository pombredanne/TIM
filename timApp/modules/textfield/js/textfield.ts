/**
 * Defines the client-side implementation of textfield/label plugin.
 */
import angular, {INgModelOptions} from "angular";
import * as t from "io-ts";
import {ITimComponent, ViewCtrl} from "tim/document/viewctrl";
import {GenericPluginMarkup, Info, nullable, PluginBase, pluginBindings, withDefault} from "tim/plugin/util";
import {$http} from "tim/util/ngimport";
import {to, valueOr} from "tim/util/utils";

const textfieldApp = angular.module("textfieldApp", ["ngSanitize"]);
export const moduleDefs = [textfieldApp];

const TextfieldMarkup = t.intersection([
    t.partial({
        followid: nullable(t.string),
        inputplaceholder: nullable(t.string),
        inputstem: nullable(t.string),
        initword: nullable(t.string),
        buttonText: nullable(t.string),
        validinput: nullable(t.string),
        errormessage: nullable(t.string),
        labelStyle: nullable(t.string),
        autosave: t.boolean,
    }),
    GenericPluginMarkup,
    t.type({
        autoupdate: withDefault(t.number, 500),
        cols: withDefault(t.number, 1),
    }),
]);
const TextfieldAll = t.intersection([
    t.partial({
    }),
    t.type({
        info: Info,
        markup: TextfieldMarkup,
        preview: t.boolean,
        state: nullable(t.type({c: t.union([t.string, t.number, t.null])})),
    }),
]);

class TextfieldController extends PluginBase<t.TypeOf<typeof TextfieldMarkup>, t.TypeOf<typeof TextfieldAll>, typeof TextfieldAll> implements ITimComponent {
    private result?: string;
    private isRunning = false;
    private userword = "";
    private modelOpts!: INgModelOptions; // initialized in $onInit, so need to assure TypeScript with "!"
    private vctrl!: ViewCtrl;
    private initialValue = "";
    private errormessage = "";
    private hideSavedText = true;
    private redAlert = false;
    private saveResponse: {saved: boolean, message: (string | undefined)} = {saved: false, message: undefined};

    getDefaultMarkup() {
        return {};
    }

    /**
     * Returns (user) defined text for the button.
     */
    buttonText() {
        return super.buttonText() || null;
    }

    $onInit() {
        super.$onInit();
        this.userword = (valueOr(this.attrsall.state && this.attrsall.state.c, this.attrs.initword || "")).toString();
        this.modelOpts = {debounce: this.autoupdate};
        if (!this.attrs.labelStyle) {
            this.vctrl.addTimComponent(this);
        }
        this.initialValue = this.userword;
    }

    /**
     * Returns the name given to the plugin.
     */
    getName(): string | undefined {
        if (this.attrs.followid) {
            return this.attrs.followid;
        }
        const taskId = this.pluginMeta.getTaskId();
        if (taskId) {
            return taskId.split(".")[1];
        }
    }

    /**
     * Returns (user) content in string form.
     */
    getContent(): string {
        return this.userword;
    }

    /**
     * Save method for other plugins, needed by e.g. multisave plugin.
     */
    async save() {
        return this.saveText();
    }

    resetField(): undefined {
        this.initCode();
        return undefined;
    }

    /**
     * Method for autoupdating.
     */
    get autoupdate(): number {
        return this.attrs.autoupdate;
    }

    /**
     * Returns (user) set inputstem (textfeed before userinput box).
     */
    get inputstem() {
        return this.attrs.inputstem || "";
    }

    /**
     * Returns (user) set col size (size of the field).
     */
    get cols() {
        return this.attrs.cols;
    }

    /**
     * Initialize content.
     */
    initCode() {
        this.userword = this.attrs.initword || "";
        this.initialValue = this.userword;
        this.result = undefined;
    }

    /**
     * Redirects save request to actual save method.
     * Used as e.g. timButton ng-click event.
     */
    async saveText() {
        if (this.isUnSaved()) {
            return this.doSaveText(false);
        } else {
            // return {saved: false, message:undefined};
            this.saveResponse.saved = false;
            this.saveResponse.message = undefined;
            return this.saveResponse;
        }
    }

    // noinspection JSUnusedGlobalSymbols
    /**
     * Returns validinput attribute, if one is defined.
     * Used by pattern checker in angular.
     * Unused method warning is suppressed, as the method is only called in template.
     */
    getPattern() {
        if (this.attrs.validinput) {
            return this.attrs.validinput;
        }
    }

    // noinspection JSUnusedGlobalSymbols
    /**
     * Returns focus on next HTML field.
     * Used by keydown (Enter) in angular.
     * Unused method warning is suppressed, as the method is only called in template.
     */
    changeFocus() {
        const inputfields = document.querySelectorAll("textfield-runner input, numericfield-runner input");
        for (let i = 0; i < inputfields.length; ++i) {
            const selectedfield = inputfields[i] as HTMLInputElement;
            if (selectedfield === document.activeElement && inputfields[i + 1]) {
                const nextfield = inputfields[i + 1] as HTMLInputElement;
                return nextfield.focus();
            }
        }
    }

    // noinspection JSUnusedGlobalSymbols
    /**
     * Returns true value, if label is set to plaintext.
     * Used to define labelstyle in angular, either input or span.
     * Unused method warning is suppressed, as the method is only called in template.
     */
    isPlainText() {
        return (this.attrs.labelStyle == "plaintext");
    }

    /**
     * Method to check grading input type for textfield.
     * Used as e.g. grading checker for hyv | hyl | 1 | 2 | 3 | 4 | 5.
     * @param re validinput defined by given attribute.
     */
    validityCheck(re: string) {
        if (this.userword === "") {
            return new RegExp("").test(this.userword);
        }
        const regExpChecker = new RegExp(re);
        return regExpChecker.test(this.userword);
    }

    // noinspection JSUnusedGlobalSymbols
    /**
     * Checking if input has been changed since the last Save or initialization.
     * Displays a red thick marker at the right side of the inputfield to notify users
     * about unsaved changes.
     * Unused method warning is suppressed, as the method is only called in template.
     */
    isUnSaved() {
        if (this.initialValue != this.userword) {
            this.hideSavedText = true;
        }
        return (this.initialValue != this.userword);
    }

    // noinspection JSUnusedGlobalSymbols
    /**
     * Autosaver used by ng-blur in textfieldApp component.
     * Needed to seperate from other save methods because of the if-structure.
     * Unused method warning is suppressed, as the method is only called in template.
     */
    autoSave() {
        if (this.attrs.autosave) {
            this.doSaveText(false);
        }
    }

    /**
     * Actual save method, called by different save alternatives implemented above.
     * @param true/false parameter boolean checker for the need to save
     */
    async doSaveText(nosave: boolean) {
        this.errormessage = "";
        if (this.attrs.validinput) {
            if (!this.validityCheck(this.attrs.validinput)) {
                this.errormessage = this.attrs.errormessage || "Input does not pass the RegEx: " + this.attrs.validinput;
                this.redAlert = true;
                this.saveResponse.message = this.errormessage;
                return this.saveResponse;
            }
        }
        this.isRunning = true;
        this.result = undefined;
        const params = {
            input: {
                nosave: false,
                c: this.userword.trim(),
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
            // TODO: Make angular to show tooltip even without user having to move cursor out and back into the input
            // (Use premade bootstrap method / add listener for enter?)
            this.errormessage = data.web.error || "";
            this.result = data.web.result;
            this.initialValue = this.userword;
            this.hideSavedText = false;
            this.redAlert = false;
            this.saveResponse.saved = true;
            this.saveResponse.message = this.errormessage;
        } else {
            this.errormessage = r.result.data.error || "Syntax error, infinite loop or some other error?";
        }
        return this.saveResponse;
    }

    protected getAttributeType() {
        return TextfieldAll;
    }
}

/**
 * Introducing textfieldRunner as HTML component.
 */
textfieldApp.component("textfieldRunner", {
    bindings: pluginBindings,
    controller: TextfieldController,
    require: {
        vctrl: "^timView",
    },
    template: `
<div class="textfieldNoSaveDiv">
    <tim-markup-error ng-if="::$ctrl.markupError" data="::$ctrl.markupError"></tim-markup-error>
    <h4 ng-if="::$ctrl.header" ng-bind-html="::$ctrl.header"></h4>
    <p class="stem" ng-if="::$ctrl.stem">{{::$ctrl.stem}}</p>
    <form name="$ctrl.f" class="form-inline">
    <label>{{::$ctrl.inputstem}}<span>
        <input type="string"
               ng-if="::!$ctrl.isPlainText()"
               class="form-control"
               ng-model="$ctrl.userword"
               ng-model-options="{ debounce: {'blur': 0} } "
               ng-blur="::$ctrl.autoSave()"
               ng-keydown="$event.keyCode === 13 && $ctrl.saveText() && $ctrl.changeFocus()"
               ng-model-options="::$ctrl.modelOpts"
               ng-trim="false"
               ng-pattern="$ctrl.getPattern()"
               ng-readonly="::$ctrl.readonly"
               uib-tooltip="{{ $ctrl.errormessage }}"
               tooltip-is-open="$ctrl.f.$invalid && $ctrl.f.$dirty"
               tooltip-trigger="mouseenter"
               placeholder="{{::$ctrl.inputplaceholder}}"
               size="{{::$ctrl.cols}}"
               ng-class="{warnFrame: ($ctrl.isUnSaved() && !$ctrl.redAlert), alertFrame: $ctrl.redAlert }">
               </span></label>
         <span ng-if="::$ctrl.isPlainText()" style="float:left;">{{$ctrl.userword}}</span>
    </form>
    <button class="timButton"
            ng-if="$ctrl.buttonText()"
            ng-disabled="$ctrl.isRunning || $ctrl.readonly"
            ng-click="$ctrl.saveText()">
        {{::$ctrl.buttonText()}}
    </button>
    <p class="savedtext" ng-if="!$ctrl.hideSavedText && $ctrl.buttonText()">Saved!</p>
    <p ng-if="::$ctrl.footer" ng-bind="::$ctrl.footer" class="plgfooter"></p>
</div>
`,
});
