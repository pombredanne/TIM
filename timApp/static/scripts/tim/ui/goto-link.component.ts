import {Component, Input, OnInit} from "@angular/core";
import moment, {Moment} from "moment";
import {formatString, to2} from "tim/util/utils";
import {IRight} from "tim/item/rightsEditor";
import humanizeDuration from "humanize-duration";
import {Users} from "tim/user/userService";
import {HttpClient} from "@angular/common/http";
import {vctrlInstance} from "tim/document/viewctrlinstance";

interface IViewAccessStatus {
    can_access: boolean;
    right?: IRight;
}

enum GotoLinkState {
    Ready,
    Countdown,
    Goto,
    Unauthorized,
    Expired,
    HasUnsavedChanges,
}

const VIEW_PATH = "/view/";

@Component({
    selector: "tim-goto-link",
    template: `
        <a [class.disabled]="linkDisabled"
           [attr.aria-disabled]="linkDisabled"
           [class.timButton]="isButton"
           [attr.role]="isButton ? 'button': null"
           (click)="handleClick()">
            <ng-content></ng-content>
        </a>
        <div class="load-text" *ngIf="hasStatus">
            <ng-container *ngIf="isExpired">
                <span class="error">
                    <ng-container *ngIf="pastDueText else defaultPastDueText">{{formatString(pastDueText, pastDueTime)}}</ng-container>
                    <ng-template #defaultPastDueText i18n>Your access expired {{pastDueTime}} ago.</ng-template>
                </span>
            </ng-container>
            <ng-container *ngIf="isUnauthorized">
                <span class="error">
                    <ng-container *ngIf="unauthorizedText else defaultUnauthorizedText">{{unauthorizedText}}</ng-container>
                    <ng-template #defaultUnauthorizedText i18n>You don't have permission to view that document.</ng-template>
                </span>
            </ng-container>
            <ng-container *ngIf="hasUnsavedChanges">
                <span class="error">
                    <ng-container *ngIf="unsavedChangesText else defaultUnsavedChangesText">{{unsavedChangesText}}</ng-container>
                    <ng-template #defaultUnsavedChangesText i18n>You have unsaved changes. Save them or click the link again.</ng-template>
                </span>
            </ng-container>
            <ng-container *ngIf="isCountdown">
                <tim-countdown [template]="countdownText" [endTime]="openTime" (onFinish)="startGoto()"></tim-countdown>
                <ng-template i18n="@@gotoOpensIn">Opens in {{"{"}}0{{"}"}}.</ng-template>
            </ng-container>
            <ng-container *ngIf="isGoing">
                <tim-loading></tim-loading>
                <span>
                    <ng-container *ngIf="waitText else defaultWaitText">{{waitText}}</ng-container>
                    <ng-template #defaultWaitText i18n>Loading, please wait.</ng-template>
                </span>
            </ng-container>
        </div>
    `,
    styleUrls: ["./goto-link.component.scss"],
})
export class GotoLinkComponent implements OnInit {
    @Input() href = "";
    @Input() waitText?: string;
    @Input() countdownText: string = $localize `:@@gotoOpensIn:Opens in ${"{"}:INTERPOLATION:0${"}"}:INTERPOLATION_1:.`;
    @Input() unauthorizedText?: string;
    @Input() pastDueText?: string;
    @Input() timeLang?: string;
    @Input() resetTime = 15;
    @Input() maxWait = 0;
    @Input() isButton = false;
    @Input() target = "_self";
    @Input() openAt?: string;
    @Input() closeAt?: string;
    @Input() checkUnsaved: boolean = false;
    @Input() unsavedChangesText?: string;
    @Input() autoOpen: boolean = false;
    openTime?: string;
    pastDue = 0;
    linkDisabled = false;
    linkState = GotoLinkState.Ready;
    resetTimeout?: number;

    formatString = formatString;

    constructor(private http: HttpClient) {
    }

    ngOnInit() {
        if (this.autoOpen) {
            void this.handleClick();
        }
    }

    get hasStatus() {
        return this.linkState != GotoLinkState.Ready;
    }

    get isCountdown() {
        return this.linkState == GotoLinkState.Countdown;
    }

    get isGoing() {
        return this.linkState == GotoLinkState.Goto;
    }

    get isUnauthorized() {
        return this.linkState == GotoLinkState.Unauthorized;
    }

    get isExpired() {
        return this.linkState == GotoLinkState.Expired;
    }

    get hasUnsavedChanges() {
        return this.linkState == GotoLinkState.HasUnsavedChanges;
    }

    get pastDueTime() {
        return humanizeDuration(this.pastDue * 1000, {language: this.timeLang ?? Users.getCurrentLanguage()});
    }

    async resolveAccess() {
        const url = new URL(this.href, window.location.href);
        const path = url.pathname;

        // If href points to a valid TIM document, check permissions
        if (url.hostname == window.location.hostname && path.startsWith(VIEW_PATH)) {
            const docPath = path.substring(VIEW_PATH.length);
            const accessInfo = await to2(this.http.get<IViewAccessStatus>(`/docViewInfo/${docPath}`).toPromise());
            if (accessInfo.ok) {
                return {unauthorized: !accessInfo.result.can_access, access: accessInfo.result.right};
            }
        }
        return {unauthorized: false, access: undefined};
    }

    parseTime(timeString?: string, wildcardValue?: Moment | null) {
        if (!timeString) {
            return wildcardValue;
        }
        const result = moment(timeString);
        return result.isValid() ? result : wildcardValue;
    }

    async handleClick() {
        // Allow user to click during countdown or past expiration, but do nothing reasonable.
        if (this.isCountdown) { return; }

        this.stopReset();

        this.linkDisabled = true;

        const {unauthorized, access} = await this.resolveAccess();

        if (unauthorized && !access) {
            this.linkState = GotoLinkState.Unauthorized;
            this.startReset(this.resetTime);
            return;
        }

        const openTime = this.parseTime(this.openAt, access?.accessible_from ?? access?.duration_from);
        const closeTime = this.parseTime(this.closeAt, access?.accessible_to ?? access?.duration_to);

        let curTime = moment();
        if (closeTime || openTime) {
            const serverTime = await to2(this.http.get<{time: Moment}>("/time").toPromise());
            // Fail silently here and hope the user clicks again so it can retry
            if (!serverTime.ok) {
                this.linkDisabled = false;
                return;
            }
            curTime = serverTime.result.time;
        }

        if (closeTime?.isValid() && closeTime.isBefore(curTime)) {
            this.pastDue = closeTime.diff(curTime, "seconds");
            this.linkState = GotoLinkState.Expired;
            this.startReset(this.resetTime);
            return;
        }

        if (!this.hasUnsavedChanges && this.checkUnsaved && vctrlInstance?.checkUnSavedTimComponents()) {
            this.linkDisabled = false;
            this.linkState = GotoLinkState.HasUnsavedChanges;
            this.startReset(this.resetTime);
            return;
        }

        if (openTime?.isValid()) {
            this.openTime = openTime?.toISOString();
        }

        if (openTime?.isValid() && openTime.diff(curTime, "seconds", true) <= 0) {
            this.startGoto();
        } else {
            this.startCountdown();
        }
    }

    startCountdown() {
        // Allow clicking, but do nothing reasonable...
        this.linkDisabled = false;
        this.linkState = GotoLinkState.Countdown;
    }

    startReset(resetTime: number) {
         this.resetTimeout = window.setTimeout(() => {
           this.stopReset();
           this.linkState = GotoLinkState.Ready;
           this.linkDisabled = false;
        }, resetTime * 1000);
    }

    stopReset() {
        if (this.resetTimeout) {
            window.clearTimeout(this.resetTimeout);
            this.resetTimeout = undefined;
        }
    }

    startGoto() {
        if (this.isGoing) { return; }
        this.linkDisabled = true;
        this.linkState = GotoLinkState.Goto;
        const waitTime = Math.random() * Math.max(this.maxWait, 0);
        const realResetTime = Math.max(this.resetTime, waitTime);

        window.setTimeout(() => {
            // Special case: on empty href just reload the page to mimic the behaviour of <a>
            if (this.href == "") {
                // Note: the force-reload is deprecated: https://github.com/Microsoft/TypeScript/issues/28898
                // TODO: Do we need force reloading? There is no consensus on whether this is supported by all browsers
                //  anymore.
                window.location.reload(true);
            } else {
                window.open(this.href, this.target);
            }
        }, waitTime * 1000);

        this.startReset(realResetTime);
    }
}
