import {IController, IScope} from "angular";
import {Type} from "io-ts/lib";
import {FormModeOption, ISetAnswerResult} from "tim/document/viewctrl";
import {isLeft} from "fp-ts/lib/Either";
import {IAnswer} from "tim/answer/IAnswer";
import {IUser} from "tim/user/IUser";
import {createParContext} from "tim/document/structure/create";
import {Binding} from "../util/utils";
import {IGenericPluginMarkup, IGenericPluginTopLevelFields} from "./attributes";
import {getErrors} from "./errors";
import {TaskId} from "./taskid";

export function getDefaults<
    MarkupType extends IGenericPluginMarkup,
    A extends IGenericPluginTopLevelFields<MarkupType>,
    T extends Type<A, unknown>
>(runtimeType: T, defaultMarkup: MarkupType) {
    const defaults: IGenericPluginTopLevelFields<MarkupType> = {
        info: null,
        markup: defaultMarkup,
        preview: true,
        state: null,
    };
    const d = runtimeType.decode(defaults);
    if (isLeft(d)) {
        throw new Error(
            "Could not get default markup:\n" +
                getErrors(d)
                    .map((x) => `- ${x.name}: ${x.type}`)
                    .join("\n")
        );
    }
    return d.right;
}

export class PluginMeta {
    constructor(
        private readonly element: JQLite,
        private readonly preview = false,
        private readonly plugintype?: string,
        private readonly taskid?: string
    ) {}

    protected getParentAttr(name: string) {
        return this.element.parent().attr(name);
    }

    taskIdCache?: TaskId | null;

    public getTaskId() {
        if (this.taskIdCache !== undefined) {
            return this.taskIdCache ?? undefined;
        }
        const tidStr = this.taskid ?? this.getParentAttr("id");
        if (tidStr) {
            const r = TaskId.tryParse(tidStr);
            if (r.ok) {
                this.taskIdCache = r.result;
                return r.result;
            } else {
                this.taskIdCache = null;
                // If a plugin doesn't have task id, the servers sends "<docid>..<blockid>" in HTML.
                // Don't warn about those because they are common.
                // The server should be fixed to not put any taskid attribute in these cases.
                if (!r.result.startsWith("Task id has empty name:")) {
                    console.warn(r.result);
                }
            }
        }
    }

    protected getPlugin() {
        let p = this.plugintype ?? this.getParentAttr("data-plugin");
        if (!p) {
            const message = "Could not find plugin type from HTML";
            alert(message);
            throw new Error(message);
        }
        const i = p.indexOf("/");
        if (i >= 0) {
            p = p.substring(i + 1);
        }
        return p;
    }

    public getTaskIdUrl() {
        return `/${this.getPlugin()}/${this.getTaskId()!.docTask().toString()}`;
    }

    public getAnswerUrl() {
        return `${this.getTaskIdUrl()}/answer`;
    }

    public getIframeHtmlUrl(user: IUser, answer: IAnswer | undefined) {
        const start = `/iframehtml/${this.getPlugin()}/${this.getTaskId()!
            .docTask()
            .toString()}/${user.id}`;
        if (answer) {
            return `${start}/${answer.id}`;
        }
        return start;
    }

    public isPreview() {
        return this.preview;
    }
}

interface PluginInit<
    MarkupType extends IGenericPluginMarkup,
    A extends IGenericPluginTopLevelFields<MarkupType>,
    T extends Type<A, unknown>
> {
    attrsall: Readonly<A>;

    getAttributeType(): T;

    markupError?: PluginMarkupErrors;
    readonly json: Binding<string, "@">;
}

export function baseOnInit<
    MarkupType extends IGenericPluginMarkup,
    A extends IGenericPluginTopLevelFields<MarkupType>,
    T extends Type<A, unknown>
>(self: PluginInit<MarkupType, A, T>) {
    const parsed = JSON.parse(atob(self.json)) as unknown;
    const validated = self.getAttributeType().decode(parsed);
    // These can be uncommented for debugging:
    // console.log(parsed);
    // console.log(this);
    // console.log(validated);
    if (isLeft(validated)) {
        self.markupError = getErrors(validated);
        return undefined;
    } else {
        self.attrsall = validated.right;
        return self.attrsall;
    }
}

export type PluginMarkupErrors = Array<{name: string; type: string}>;

/**
 * Functionality that is common to both Angular and old AngularJS plugins.
 */
export abstract class PluginBaseCommon {
    abstract element: JQuery;
    protected abstract pluginMeta: PluginMeta;

    protected getRootElement() {
        return this.element[0];
    }

    isPreview() {
        return this.pluginMeta.isPreview();
    }

    getAreas(): string[] {
        const returnList: string[] = [];
        const parents = this.element.parents(".area");
        if (parents[0]) {
            const areaList = parents[0].classList;
            areaList.forEach((value) => {
                const m = value.match(/^area_(\S+)$/);
                if (m) {
                    returnList.push(m[1]);
                }
            });
        }
        return returnList;
    }

    belongsToArea(area: string): boolean {
        return this.getAreas().includes(area);
    }

    /**
     * Returns task name of the plugin.
     */
    getName() {
        return this.pluginMeta.getTaskId()?.name;
    }

    getTaskId() {
        return this.pluginMeta.getTaskId();
    }

    /**
     * Returns the plugin's parent paragraph.
     * If the plugin is not attached to a paragraph or the paragraph is not attached to a document, returns null.
     */
    public getPar() {
        const parElement = this.element.parents(".par")[0];
        if (!parElement.parentElement) {
            return undefined;
        }
        return createParContext(parElement);
    }

    /**
     * @returns {FormModeOption} FormModeOption.IsForm if plugin wants to register as formAnswerBrowser
     * This means invisible answerBrowser and direct answer input when changing users in ViewCtrl
     * If Undecided, let ViewCtrl decide if plugin is to be used as form.
     * IsForm and Undecided options should only be used by simple plugins where getState is not necessary when changing answers
     */
    public formBehavior(): FormModeOption {
        return FormModeOption.NoForm;
    }

    /**
     * Sets plugin's answer content via external call
     * @param content answer to be parsed
     * @returns ISetAnswerResult: {ok: boolean, message: (string | undefined)}
     * ok: true if content was succesfully parsed
     * message: for replying with possible errors
     */
    setAnswer(content: Record<string, unknown>): ISetAnswerResult {
        return {ok: false, message: "Plugin doesn't support setAnswer"};
    }

    resetField(): undefined {
        return undefined;
    }

    resetChanges(): void {}
}

/**
 * Base class for plugins.
 *
 * All properties or fields having a one-time binding in template should eventually return a non-undefined value.
 * That's why there are "|| null"s in several places.
 */
export abstract class PluginBase<
        MarkupType extends IGenericPluginMarkup,
        A extends IGenericPluginTopLevelFields<MarkupType>,
        T extends Type<A>
    >
    extends PluginBaseCommon
    implements IController
{
    static $inject = ["$scope", "$element"];

    buttonText() {
        return this.attrs.button ?? this.attrs.buttonText ?? null;
    }

    get attrs(): Readonly<MarkupType> {
        return this.attrsall.markup;
    }

    get disableUnchanged() {
        return this.attrs.disableUnchanged;
    }

    get footer() {
        return this.attrs.footer ?? null;
    }

    get header() {
        return this.attrs.header ?? null;
    }

    get stem() {
        return this.attrs.stem ?? null;
    }

    /**
     * Returns if this plugin is readonly for the current user.
     */
    get readonly(): boolean {
        return (
            this.attrsall.access === "readonly" ||
            (this.attrs.readonly ?? false)
        );
    }

    get undoButton() {
        return this.attrs.undo?.button;
    }

    get undoTitle() {
        return this.attrs.undo?.title;
    }

    get undoConfirmation() {
        return this.attrs.undo?.confirmation;
    }

    // Parsed form of json binding or default value if json was not valid.
    attrsall: Readonly<A>;
    // Binding that has all the data as a JSON string.
    readonly json!: Binding<string, "@">;

    // Optional bindings that are used when the plugin is compiled without being attached to document.
    // In that case, the plugin element does not have the parent where to fetch the type and task id, so they
    // are provided when compiling.
    plugintype?: Binding<string, "@?">;
    taskid?: Binding<string, "@?">;

    markupError?: PluginMarkupErrors;
    pluginMeta: PluginMeta;

    constructor(protected scope: IScope, public element: JQLite) {
        super();
        this.attrsall = getDefaults(
            this.getAttributeType(),
            this.getDefaultMarkup()
        );
        this.pluginMeta = new PluginMeta(element, this.attrsall.preview);
    }

    abstract getDefaultMarkup(): Partial<MarkupType>;

    $postLink() {}

    $onInit() {
        const result = baseOnInit(this);
        if (result) {
            this.pluginMeta = new PluginMeta(
                this.element,
                result.preview,
                this.plugintype,
                this.taskid
            );
        }
    }

    abstract getAttributeType(): T;
}

/**
 * Shuffles a string array.
 * @param strings Array of strings to be shuffled.
 */
export function shuffleStrings(strings: string[]): string[] {
    const result = strings.slice();
    const n = strings.length;
    for (let i = n - 1; i >= 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        const tmp = result[i];
        result[i] = result[j];
        result[j] = tmp;
    }
    return result;
}

/**
 * Converts plugin's "form" (boolean/undefined) attribute to FormModeOption
 * @param attr attribute to inspect
 * @param defBehavior default option to return if form attribute was not given
 */
export function getFormBehavior(
    attr: boolean | undefined,
    defBehavior: FormModeOption
): FormModeOption {
    if (attr == undefined) {
        return defBehavior;
    }
    return attr ? FormModeOption.IsForm : FormModeOption.NoForm;
}

export const pluginBindings = {
    json: "@",
    plugintype: "@?",
    taskid: "@?",
};

export function inIframe() {
    try {
        return window.self !== window.top;
    } catch (e) {
        return true;
    }
}
