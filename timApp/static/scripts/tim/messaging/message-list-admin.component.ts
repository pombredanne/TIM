import {HttpClient} from "@angular/common/http";
import {Component, NgModule, OnInit} from "@angular/core";
import {CommonModule} from "@angular/common";
import {to2} from "tim/util/utils";
import {FormsModule} from "@angular/forms";
import {
    archivePolicyNames,
    ArchiveType,
    Distribution,
    ListOptions,
    MemberInfo,
    ReplyToListChanges,
} from "tim/messaging/listOptionTypes";
import {documentglobals} from "tim/util/globals";
import {TimUtilityModule} from "tim/ui/tim-utility.module";
import {TableFormModule} from "tim/plugin/tableForm";
import moment from "moment";
import {Users} from "../user/userService";

@Component({
    selector: "tim-message-list-admin",
    template: `
        <form class="form-horizontal">
            <h1>Message list management</h1>
            <div class="form-group">
                <label for="list-name" class="list-name control-label col-sm-3">List name: </label>
                <div class="col-sm-9">
                    <div class="input-group">
                        <input type="text" class="form-control" name="list-name" id="list-name" disabled
                               [(ngModel)]="listname"/>
                        <div class="input-group-addon">@</div>
                        <select id="domain-select" class="form-control" name="domain-select" [(ngModel)]="domain">
                            <option [disabled]="domains.length < 2" *ngFor="let domain of domains">{{domain}}</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="form-group" *ngIf="domain">
                <label for="list-description" class="short-description control-label col-sm-3">List address: </label>
                <div class="col-sm-9">
                    <input type="text" class="form-control" name="list-email-address" id="list-email-address"
                           [ngModel]="listAddress()" disabled/>
                </div>
            </div>
            <div class="form-group">
                <label for="list-description" class="short-description control-label col-sm-3">Short
                    description: </label>
                <div class="col-sm-9">
                    <input type="text" class="form-control" name="list-description" id="list-description"
                           [(ngModel)]="listDescription"/>
                </div>
            </div>
            <div class="form-group">
                <label for="list-info" class="long-description control-label col-sm-3">Long description: </label>
                <div class="col-sm-9">
                <textarea name="list-info" class="list-info form-control"
                          [(ngModel)]="listInfo">A more detailed information thingy for this list.</textarea>
                </div>
            </div>
            <div>
            </div>
            <div>
                <p class="list-archive-policy-header">Archive policy:</p>
                <!-- Variable archiveoptions is reversed, so indexing for display has to accommodate. -->
                <p>{{archiveOptions[archiveOptions.length - (archive + 1)].policyName}}</p>
                <!-- Hide radio buttons here, until the changing of archive policy levels is implemented -->
                <!--
                <ul id="archive-policy-list">
                    <li *ngFor="let option of archiveOptions">
                        <label for="archive-{{option.archiveType}}">
                        <input
                                name="items-radio"
                                type="radio"
                                id="archive-{{option.archiveType}}"
                                [value]="option.archiveType"
                                [(ngModel)]="archive"
                        />
                        {{option.policyName}}</label>
                    </li>
                </ul>
                -->
            </div>
            <div class="section">
                <h3>Options</h3>
                <div>
                    <label for="list-subject-prefix">
                        <input type="text" name="list-subject-prefix" [(ngModel)]="listSubjectPrefix">
                        Subject prefix.</label>
                </div>
            </div>
            <div>
                <label for="notify-owner-on-list-change">
                    <input type="checkbox" name="notify-owner-on-list-change" id="notify-owner-on-list-change"
                           [(ngModel)]="notifyOwnerOnListChange"/>
                    Notify owners on list changes (e.g. user subscribes).</label>
            </div>
            <div>
                <label for="tim-users-can-join">
                    <input type="checkbox" name="tim-users-can-join" [(ngModel)]="timUsersCanJoin">
                    TIM users can freely join this list.</label>
            </div>
            <div>
                <label for="can-user-unsubscribe">
                    <input type="checkbox" name="can-user-unsubscribe" [(ngModel)]="canUnsubscribe">
                    Members can unsubscribe from the list on their own.</label>
            </div>
            <div>
                <label for="non-members-can-send">
                    <input type="checkbox" name="non-members-can-send" [(ngModel)]="nonMemberMessagePass">
                    Non members can send messages to list.</label>
            </div>
            <div>
                <label for="only-text">
                    <input type="checkbox" name="only-text" [(ngModel)]="onlyText">
                    No HTML messages allowed on the list.</label>
            </div>
            <div>
                <label for="allow-attachments">
                    <input type="checkbox" name="allow-attachments" [(ngModel)]="allowAttachments">
                    Allow attachments on the list.</label>
            </div>
            <div>
                <button class="timButton" (click)="saveOptions()">Save changes</button>
            </div>
            <div id="members-section" class="section">
                <h3>Members</h3>
                <div id="add-members-section">
                    <label for="add-multiple-members">Add members</label> <br/>
                    <textarea id="add-multiple-members" name="add-multiple-members"
                              [(ngModel)]="membersTextField"></textarea>
                    <div>
                        <div>
                            <input type="checkbox" name="new-member-send-right" [(ngModel)]="newMemberSendRight">
                            <label for="new-member-send-right">New member's send right.</label>
                        </div>
                        <div>
                            <input type="checkbox" name="new-member-delivery-right"
                                   [(ngModel)]="newMemberDeliveryRight">
                            <label for="new-member-delivery-right">New member's delivery right.</label>
                        </div>
                    </div>
                    <button (click)="addNewListMember()" class="timButton">Add new members</button>
                    <div id="member-add-feedback">
                        <tim-alert *ngIf="memberAddSucceededResponse"
                                   severity="success">{{memberAddSucceededResponse}}</tim-alert>
                        <tim-alert *ngIf="memberAddFailedResponse"
                                   severity="danger">{{memberAddFailedResponse}}</tim-alert>
                    </div>
                </div>
                <div class="section">
                    <table>
                        <caption>List members</caption>
                        <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Send right</th>
                            <th>Delivery right</th>
                            <th>Membership ended</th>
                            <th>Removed</th>
                        </tr>
                        </thead>
                        <tbody>
                        <tr *ngFor="let member of membersList">
                            <td>{{member.name}}</td>
                            <td>{{member.email}}</td>
                            <td>
                                <input type="checkbox" [(ngModel)]="member.sendRight"
                                       name="member-send-right-{{member.email}}">
                            </td>
                            <td>
                                <input type="checkbox" [(ngModel)]="member.deliveryRight"
                                       name="member-delivery-right-{{member.email}}">
                            </td>
                            <td>{{member.removed}}</td>
                            <td><input type="checkbox" (click)="membershipChange(member)" [ngModel]="!!member.removed"
                                       name="removed-{{member.email}}"/></td>
                        </tr>
                        </tbody>
                    </table>
                    <button class="timButton" (click)="saveMembers()">Save</button>
                </div>
            </div>
            <div id="email-send">
                <tim-message-send [(recipientList)]="recipients" [docId]="getDocId()"></tim-message-send>
                <button class="timButton" (click)="openEmail()" *ngIf="!recipients">Send email to list</button>
            </div>
            <div class="section">
                <h2>List deletion</h2>
                <button class="timButton" (click)="deleteList()">Delete List</button>
            </div>
            <div>
                <h3>Links</h3>
                <div *ngIf="archiveURL">
                    <a [href]="archiveURL">List's archive</a>
                </div>
                <div *ngIf="emailAdminURL">
                    <a [href]="emailAdminURL">Advanced email list settings</a>
                </div>
            </div>
        </form>
    `,
    styleUrls: ["message-list-admin.component.scss"],
})
export class MessageListAdminComponent implements OnInit {
    listname: string = "";

    // List has a private members only archive by default.
    archive: ArchiveType = ArchiveType.GROUPONLY;

    domain?: string;
    domains: string[] = [];

    membersTextField?: string;
    membersList: MemberInfo[] = [];

    urlPrefix: string = "/messagelist";

    // Not in use at the moment.
    ownerEmail: string = "";

    archiveOptions = archivePolicyNames;

    notifyOwnerOnListChange: boolean = false;
    timUsersCanJoin?: boolean = false;

    listInfo?: string;
    listDescription?: string;

    emailAdminURL?: string;
    archiveURL?: string;

    canUnsubscribe?: boolean;
    defaultSendRight?: boolean;
    defaultDeliveryRight?: boolean;
    listSubjectPrefix?: string;
    nonMemberMessagePass?: boolean;
    onlyText?: boolean;
    allowAttachments?: boolean;
    // distibution?: Channel[];
    distribution?: Distribution;
    listReplyToChange?: ReplyToListChanges;

    newMemberSendRight: boolean = true;
    newMemberDeliveryRight: boolean = true;

    // Response strings used in giving feedback to the user on adding new members to the message list.
    memberAddSucceededResponse: string = "";
    memberAddFailedResponse: string = "";

    recipients = "";

    /**
     * Modifies the member's removed attribute if the member's state is changed.
     * @param member Who's membership on the list is changed.
     */
    membershipChange(member: MemberInfo) {
        if (member.removed) {
            member.removed = undefined;
        } else {
            // Set time stamp when the member was removed.
            member.removed = moment();
        }
    }

    /**
     * The current documents document ID.
     */
    getDocId() {
        return documentglobals().curr_item.id;
    }

    /**
     * Build this list's email address, if there is a domain configured.
     */
    listAddress() {
        if (this.domain) {
            return `${this.listname}@${this.domain}`;
        }
        return "";
    }

    /**
     * Initialization procedures.
     */
    async ngOnInit() {
        if (Users.isLoggedIn()) {
            // Get domains.
            await this.getDomains();

            // Load message list options.
            const docId = this.getDocId();
            const result1 = await this.loadValues(docId);

            if (result1.ok) {
                this.setValues(result1.result);
            } else {
                console.error(result1.result.error.error);
                // TODO: Check what went wrong.
            }

            // Load list members.
            const result2 = await this.getListMembers();

            if (result2.ok) {
                console.log(result2.result);
                this.membersList = result2.result;
            } else {
                console.error(result2.result.error.error);
            }
        }
    }

    /**
     * Opens the email sending view by adding the list's address to the string of recipients.
     *
     * The email sending view will be closed by emptying the list of recipients by the component(?)
     */
    openEmail() {
        this.recipients = this.listAddress();
    }

    /**
     * Get domains ccondigured for email list use.
     */
    private async getDomains() {
        const result = await to2(
            this.http.get<string[]>(`${this.urlPrefix}/domains`).toPromise()
        );
        if (result.ok) {
            this.domains = result.result;
            if (!this.domains.length) {
                this.domain = this.domains[0];
            }
        } else {
            console.error(result.result.error.error);
        }
    }

    constructor(private http: HttpClient) {}

    /**
     * Compile email addresses separated by line breaks into a list
     * @private
     */
    private parseMembers(): string[] {
        if (!this.membersTextField) {
            return [];
        }
        return this.membersTextField.split("\n").filter((e) => e);
    }

    /**
     * Add new members to message list.
     */
    async addNewListMember() {
        const memberCandidates = this.parseMembers();
        if (memberCandidates.length == 0) {
            return;
        }
        const result = await to2(
            this.http
                .post(`${this.urlPrefix}/addmember`, {
                    memberCandidates: memberCandidates,
                    msgList: this.listname,
                    sendRight: this.newMemberSendRight,
                    deliveryRight: this.newMemberDeliveryRight,
                })
                .toPromise()
        );
        if (result.ok) {
            this.membersTextField = undefined; // Empty the text field.
            this.memberAddSucceededResponse = "New members added.";
        } else {
            this.memberAddFailedResponse = `Adding new members failed: ${result.result.error.error}`;
        }
    }

    /**
     * Get all list members.
     */
    async getListMembers() {
        return to2(
            this.http
                .get<MemberInfo[]>(
                    `${this.urlPrefix}/getmembers/${this.listname}`
                )
                .toPromise()
        );
    }

    /**
     * Helper for list deletion.
     */
    async deleteList() {
        // TODO: Confirm with user if they are really sure they want to delete the entire message list. Technically it
        //  could be reversible, but such an hassle that not letting it happen by a single button press should be
        //  allowed.
        const result = await to2(
            this.http
                .delete(`/messagelist/deletelist`, {
                    params: {
                        listname: this.listname,
                        domain: this.domain ? this.domain : "",
                    },
                })
                .toPromise()
        );
        if (result.ok) {
            // TODO: Inform the user deletion was succesfull.
            console.log(result.result);
        } else {
            // TODO: Inform the user deletion was not succesfull.
            console.error(result.result);
        }
    }

    /**
     * Get values for message list's options.
     * @param docID List is defined by it's management document, so we get list's options and members with it.
     */
    async loadValues(docID: number) {
        return to2(
            this.http
                .get<ListOptions>(`${this.urlPrefix}/getlist/${docID}`)
                .toPromise()
        );
    }

    /**
     * Setting list values after loading.
     * @param listOptions
     */
    setValues(listOptions: ListOptions) {
        this.listname = listOptions.name;
        this.archive = listOptions.archive;

        this.domain = listOptions.domain;

        // No use at the moment.
        // this.ownerEmail = "";

        this.notifyOwnerOnListChange =
            listOptions.notify_owners_on_list_change ?? false;

        this.listInfo = listOptions.list_info;
        this.listDescription = listOptions.list_description;

        this.emailAdminURL = listOptions.email_admin_url;

        // If some type of archiving exists for the list, provide a link to it.
        if (this.archive !== ArchiveType.NONE) {
            this.archiveURL = `/view/archives/${this.listname}`;
        }

        this.timUsersCanJoin = listOptions.tim_users_can_join;

        this.listSubjectPrefix = listOptions.list_subject_prefix;
        this.canUnsubscribe = listOptions.members_can_unsubscribe;
        this.defaultSendRight = listOptions.default_send_right;
        this.defaultDeliveryRight = listOptions.default_delivery_right;
        this.nonMemberMessagePass = listOptions.non_member_message_pass;
        this.onlyText = listOptions.only_text;
        this.allowAttachments = listOptions.allow_attachments;
        this.distribution = listOptions.distribution;
        this.allowAttachments = listOptions.allow_attachments;
        this.listReplyToChange = listOptions.default_reply_type;
    }

    /**
     * Save the list options.
     */
    async saveOptions() {
        const result = await this.saveOptionsCall({
            name: this.listname,
            domain: this.domain,
            list_info: this.listInfo,
            list_description: this.listDescription,
            only_text: this.onlyText,
            default_reply_type: this.listReplyToChange, // TODO: Option to ask the user.
            notify_owners_on_list_change: this.notifyOwnerOnListChange,
            archive: this.archive,
            tim_users_can_join: this.timUsersCanJoin,
            list_subject_prefix: this.listSubjectPrefix,
            members_can_unsubscribe: this.canUnsubscribe,
            default_delivery_right: this.defaultDeliveryRight,
            default_send_right: this.defaultSendRight,
            non_member_message_pass: this.nonMemberMessagePass,
            distribution: this.distribution,
            allow_attachments: this.allowAttachments,
        });
        if (result.ok) {
            // console.log("save succee");
        } else {
            console.error("save fail");
        }
    }

    /**
     * Helper for list saving to keep types in check.
     * @param options All the list options the user saves.
     */
    private saveOptionsCall(options: ListOptions) {
        return to2(this.http.post(`/messagelist/save`, {options}).toPromise());
    }

    /**
     * Save the lists members' state.
     */
    async saveMembers() {
        const resultSaveMembers = await this.saveMembersCall(this.membersList);

        if (resultSaveMembers.ok) {
            // console.log("Saving members succeeded.");
        } else {
            console.error("Saving members failed.");
        }
    }

    /**
     * Makes the actual REST call to save the state of list members'.
     * @param memberList A list of message list members with their information.
     */
    saveMembersCall(memberList: MemberInfo[]) {
        return to2(
            this.http
                .post(`${this.urlPrefix}/savemembers`, {
                    members: memberList,
                    listname: this.listname,
                })
                .toPromise()
        );
    }

    /**
     * Modify the recipient list for tim-message-send component. Adds the message list's email list as the recipient.
     */
    recipientList() {
        if (this.domain) {
            return `${this.listname}@${this.domain}`;
        } else {
            return "";
        }
    }
}

@NgModule({
    declarations: [MessageListAdminComponent],
    exports: [MessageListAdminComponent],
    imports: [CommonModule, FormsModule, TimUtilityModule, TableFormModule],
})
export class NewMsgListModule {}
