import moment, {Moment} from "moment";
import {ngStorage} from "ngstorage";
import {DialogController, registerDialogComponent, showDialog} from "../ui/dialog";
import {IUser} from "../user/IUser";
import {$http, $httpParamSerializer, $localStorage} from "../util/ngimport";
import {to} from "../util/utils";

interface IFBOptions<T> {
    period: "whenever" | "sincelast" | "day" | "week" | "month" | "other";
    valid: string;
    name: string;
    periodFrom: T;
    periodTo: T;
    scope: string;
    answers: string;
    format: string;
    users: string;
    decimal: string;
}

export interface IFeedbackAnswersParams {
    identifier: string;
    users: IUser[];
    url: string;
    allTasks: boolean;
}

export class FeedbackAnswersCtrl extends DialogController<{params: IFeedbackAnswersParams}, {}> {
    static component = "timFeedbackAnswers";
    static $inject = ["$element", "$scope"] as const;
    private options!: IFBOptions<Moment>; // $onInit
    private $storage!: ngStorage.StorageService & {feedbackAnswersOptions: IFBOptions<number | null>}; // $onInit
    private showSort: boolean = false;
    private datePickerOptionsFrom!: EonasdanBootstrapDatetimepicker.SetOptions; // $onInit
    private datePickerOptionsTo!: EonasdanBootstrapDatetimepicker.SetOptions; // $onInit
    private lastFetch: unknown;

    protected getTitle() {
        return "Export to csv";
    }

    async $onInit() {
        super.$onInit();
        const options = this.resolve.params;
        moment.locale("en", {
            week: {dow: 1, doy: 4}, // This sets Monday as the first day of the week.
        });
        this.showSort = options.allTasks;
        const defs = {
            period: "whenever",
            valid: "1",
            name: "both",
            periodFrom: null,
            periodTo: null,
            scope: "task",
            answers: "all",
            format: "semicolon",
            users: "",
            decimal: "point",
        } as const;
        this.$storage = $localStorage.$default({
            feedbackAnswersOptions: defs,
        });

        const dateFormat = "D.M.YYYY HH:mm:ss";

        this.options = {
            ...this.$storage.allAnswersOptions,
            periodFrom: moment(this.options.periodFrom || Date.now()),
            periodTo: moment(this.options.periodFrom || Date.now()),
        };
        this.datePickerOptionsFrom = {
            format: dateFormat,
            defaultDate: moment(this.options.periodFrom),
            showTodayButton: true,
        };
        this.datePickerOptionsTo = {
            format: dateFormat,
            defaultDate: moment(this.options.periodTo),
            showTodayButton: true,
        };

        this.lastFetch = null;
        const r =
            await to($http.get<{last_answer_fetch: {[index: string]: string}}>("/settings/get/last_answer_fetch"));
        if (r.ok && r.result.data.last_answer_fetch) {
            this.lastFetch = r.result.data.last_answer_fetch[options.identifier];
            if (!this.lastFetch) {
                this.lastFetch = "no fetches yet";
            }
        }
        this.options.users = "";
        for (const user of options.users) {
            this.options.users += user.name + ",";
        }
    }

    ok() {
        const toSerialize: IFBOptions<Date | null> = {
            ...this.options,
            periodFrom: this.options.periodFrom.toDate(),
            periodTo: this.options.periodTo.toDate(),
        };
        window.open(this.resolve.params.url + "?" + $httpParamSerializer(toSerialize), "_blank");
        this.close({});
    }
    cancel() {
        this.dismiss();
    }
}

registerDialogComponent(FeedbackAnswersCtrl,
    {templateUrl: "/static/templates/allFeedbackAnswersOptions.html"});

export function showFeedbackAnswers(p: IFeedbackAnswersParams) {
    return showDialog(FeedbackAnswersCtrl, {params: () => p}).result;
}
