import {
    Component,
    ElementRef,
    EventEmitter,
    Host,
    Input,
    Output,
} from "@angular/core";
import {ParCompiler} from "tim/editor/parCompiler";
import {ViewCtrl} from "tim/document/viewctrl";
import {NgForm} from "@angular/forms";
import {$http} from "../util/ngimport";
import {clone, to} from "../util/utils";
import {VelpSelectionDialog} from "./velp-selection-dialog.component";
import {
    ILabel,
    ILabelUI,
    INewLabel,
    INewVelp,
    IVelpGroup,
    IVelpGroupUI,
    IVelpUI,
} from "./velptypes";

/**
 * Created by Seppo Tarvainen on 25.11.2016.
 *
 * @author Seppo Tarvainen
 * @licence MIT
 */

export const colorPalette = [
    "blueviolet",
    "darkcyan",
    "orange",
    "darkgray",
    "cornflowerblue",
    "coral",
    "goldenrod",
    "blue",
];

// TODO: add keyboard shortcuts to velps
// TODO: add min and max values for points
// TODO: user should be able to delete velp without any annotations

interface IVelpOptionSetting {
    type: string;
    title: string;
    values: number[];
    names: string[];
}

/**
 * Controller for velp Window
 */
@Component({
    selector: "tim-velp-window",
    template: `
        <div class="velp" [ngStyle]="{top: 1+index*2 + 'em'}"  (click)="notAnnotationRights(velp.points) || useVelp()">
    <div class="velp-data emphasise default" [ngClass]="{neutral: velp.points && velp.points == 0,
                    positive: velp.points && velp.points > 0,
                    negative: velp.points && velp.points < 0,
                    new: new,
                    inactive: notAnnotationRights(velp.points),
                    edit: velp.edit}"
        [ngStyle]="{ backgroundColor: getCustomColor()}"
    ><!--

        Show this when velp is NOT being edited

       --><div *ngIf="!velp.edit" class="content velpContent">
            <div>
                <span class="header math">{{ velp.content }}</span>

                <span (click)="toggleVelpToEdit(); $event.stopPropagation();"
                      *ngIf="hasEditAccess"
                      class="pull-right glyphicon glyphicon-pencil clickable-icon"></span>
                <span *ngIf="notAnnotationRights(velp.points)"
                      class="annmark glyphicon glyphicon-exclamation-sign clickable-icon pull-right"
                      [title]="settings.teacherRightsError">
                </span>
                <span class="margin-5-right header pull-right">{{ velp.points }}</span>
                <p class="velpInfoText truncate math">{{ velp.default_comment }}</p>

                <div class="tags">
                    <ng-container *ngIf="advancedOn">
                        <span *ngFor="let label of velp.labels" title="label.content" 
                              class="pull-right glyphicon glyphicon-tag"
                              [style.color]="getColor(label)"></span>
                    </ng-container>
                </div>

            </div>
            <div class="bottom-part"></div>
        </div><!--

        Show this when velp IS being edited

     --><div *ngIf="velp.edit" class="content">
                            <tim-close-button (click)="toggleVelpToEdit(); $event.stopPropagation();" 
                                              class="clickable-icon">
                            </tim-close-button>

        <form #saveVelpForm="ngForm" (submit)="saveVelp(saveVelpForm)">
            <p class="header"><input #velpName="ngModel" name="velpName" type="text" [(ngModel)]="velp.content"
                       required placeholder="Velp content" title="Annotation visible text">
            </p>
            <p *ngIf="(velpName.invalid && !velpName.pristine)"
               class="error velpInfoText">
                {{ settings.velpContentError }}
            </p>


            <p *ngIf="allowChangePoints()" class="header"><input id="addVelpPoints" type="number" style="width: 100%;"
                                                    title="Default points from this velp"
                                                    name="velpPoints"
                                                    [(ngModel)]="velp.points"
                                                    step="0.01"
                                                    placeholder="Points" value="0"></p>
            <p [hidden]="allowChangePoints()" class="velpInfoText">{{ settings.teacherRightsError }}</p>

            <p><textarea placeholder="Add default comment" name="velpDefaultComment" [(ngModel)]="velp.default_comment" title="Default comment for annotation" ></textarea></p>

            <fieldset *ngIf="advancedOn">
                <legend>Labels
                    <span class="pull-right glyphicon glyphicon-tag"
                          *ngFor="let l of velp.labels"
                          [ngStyle]="{ color: getColor(l) }">
                    </span>
                </legend>

                <span *ngFor="let l of labels">

                    <!-- Show this when label IS NOT being edited -->
                    <span *ngIf="!l.edit">
                        <label>
                            <input type="checkbox"
                                      (click)="updateVelpLabels(l)"
                                      [checked]="isLabelInVelp(l)">
                            {{ l.content }}
                        </label>

                        <span class="pull-right glyphicon glyphicon-pencil clickable-icon"
                              (click)="toggleLabelToEdit(l)">
                        </span>
                        <br>
                    </span>

                    <!-- Show this when label IS being edited -->
                    <span *ngIf="l.edit">
                        <input type="text"
                               placeholder="Add label"
                               name="labelToEditContent"
                               (ngModelChange)="setLabelValid(labelToEdit)"
                               [(ngModel)]="labelToEdit.content">

                        <span class="pull-right glyphicon glyphicon-pencil clickable-icon"
                              (click)="toggleLabelToEdit(l)">
                        </span>
                        <input class="timButton" type="button"
                               value="Save" (click)="editLabel()"
                               [disabled]="!isVelpValid()">
                        <input class="timButton" type="button"
                               value="Cancel" (click)="toggleLabelToEdit(l)">
                        <br>
                        <span *ngIf="!labelToEdit.valid">
                            <span class="error velpInfoText">{{ settings.labelContentError }}</span>
                            <br>
                        </span>
                    </span>
                </span>

                <!-- Add new label -->
                <input class="addLabelField" placeholder="Add label"
                       name="newLabelContent"
                       (ngModelChange)="setLabelValid(newLabel)"
                       [(ngModel)]="newLabel.content">
                <input class="addLabelBtn" type="button" value="Add"
                       (click)="addLabel()">
                <span *ngIf="!newLabel.valid" class="error velpInfoText">{{ settings.labelContentError }}</span>
            </fieldset>

            <!-- Velp groups -->
            <fieldset *ngIf="advancedOn">
                <legend>Velp groups</legend>
                <span *ngFor="let g of velpGroups">

                    <label  title="{{ !g.show ? 'This group is not shown in the selected area. Change setting in manage tab.' : ''}}"
                            [ngClass]="{disabled: !g.edit_access, gray: !g.show}"><input type="checkbox"
                                                                        (click)="updateVelpGroups(g)"
                                                                        [checked]="isGroupInVelp(g)"
                                                                        [disabled]="!g.edit_access">
                        {{ g.name }}
                    </label>
                    <br>
                </span>
            </fieldset>
            <p class="error velpInfoText" *ngIf="!isSomeVelpGroupSelected()">
                {{ settings.velpGroupError }}
            </p>
            <p class="warning velpInfoText" *ngIf="!isSomeVelpGroupShown()">
                {{ settings.velpGroupWarning }}
            </p>

            <p>
                <label>
                    <span title="Visible to"
                          class="glyphicon glyphicon-eye-open visible-icon">

                    </span>
                    <select name="velpVisibleTo" [(ngModel)]="velp.visible_to" title="Visible to">
                        <option *ngFor="let v of visibleOptions.values" [value]="v">{{visibleOptions.names[v-1]}}</option>
                    </select>
                    <span class="glyphicon glyphicon-question-sign clickable-icon"
                          popover="Who can see the velp as a default?
                                      'Just me' means that the annotation is visible only to yourself.
                                      'Document owner' refers to the person or group who has been named as the document owner.
                                      'Teachers' refers to the users that have teacher access to this document.
                                      'Everyone' means that the annotation is visible to everyone who can view the assessed content."
                          placement="top">
                    </span>
                </label>
                <span style="float: right">
                    <input type="color" name="velpColor" [(ngModel)]="velp.color" title="change Velp default color" class="colorchange-button">
                    <input *ngIf="isVelpCustomColor()" class="smallButton" type="button" (click)="clearVelpColor()" title="Reset color to original value" value="R">
                </span>
            </p>
            <p>
                <label>
                    <span>Style</span>
                    <select name="velpStyle" [(ngModel)]="velp.style" title="Style">
                        <option *ngFor="let v of styleOptions.values" [value]="v">{{ styleOptions.names[v-1] }}</option>
                    </select>
                </label>
            </p>
            <!-- submit executes 'saveVelp'-function -->
            <p>
            <input type="submit" class="timButton" [value]="saveButtonText()" [disabled]="!isVelpValid()"/>
            <input type="button" class="timButton" value="Cancel" (click)="toggleVelpToEdit(); $event.stopPropagation();">
            </p>
        </form>
        </div>
    </div>
</div>
`,
})
export class VelpWindowComponent {
    velpLocal!: IVelpUI | INewVelp;
    newLabel: INewLabel;
    labelToEdit: INewLabel;
    visibleOptions: IVelpOptionSetting;
    styleOptions: IVelpOptionSetting;
    settings: {
        teacherRightsError: string;
        labelContentError: string;
        velpGroupError: string;
        velpGroupWarning: string;
        velpContentError: string;
    };
    private submitted: boolean;
    hasEditAccess: boolean;
    @Output() velpSelect = new EventEmitter();
    @Input() velp!: IVelpUI | INewVelp;
    @Input() new!: boolean;
    @Input() velpGroups!: IVelpGroupUI[];
    @Input() labels!: ILabelUI[];
    @Input() docId!: number;
    @Input() teacherRight!: boolean;
    @Input() advancedOn!: boolean;
    @Input() index!: number;
    private vctrl!: ViewCtrl;
    private element: JQuery;

    ngOnInit() {
        this.velpLocal = clone(this.velp);

        if (this.velp.visible_to == null) {
            this.velp.visible_to = 4; // Everyone by default
        }
        if (this.velp.style == null) {
            this.velp.style = 1;
        }

        // declare edit rights
        if (this.new) {
            this.hasEditAccess = true;
            this.velpSelection.registerNewVelp(this);
        } else {
            this.hasEditAccess = this.velpGroups.some(
                (g) => (g.edit_access && this.isGroupInVelp(g)) || false
            );
        }
    }

    ngAfterViewInit() {
        void ParCompiler.processAllMath(this.element.find(".velpContent"));
    }

    constructor(
        @Host() private velpSelection: VelpSelectionDialog,
        private elementRef: ElementRef
    ) {
        this.element = $(elementRef.nativeElement);
        this.newLabel = {content: "", selected: true, valid: true, id: null};
        this.labelToEdit = {
            content: "",
            selected: false,
            edit: false,
            valid: true,
            id: null,
        };
        this.visibleOptions = {
            type: "select",
            title: "Visible to",
            values: [1, 2, 3, 4],
            names: ["Just me", "Document owner", "Teachers", "Everyone"],
        };
        this.styleOptions = {
            type: "select",
            title: "Style",
            values: [1, 2, 3],
            names: ["Default", "Text", "Text (always visible)"],
        };
        this.settings = {
            teacherRightsError:
                "You need to have teacher rights to change points in this document.",
            labelContentError: "Label content too short",
            velpGroupError: "Select at least one velp group.",
            velpGroupWarning:
                "All selected velp groups are hidden in the current area.",
            velpContentError: "Velp content too short",
        };
        this.submitted = false;
        this.hasEditAccess = false;
        // scope.$watch(
        //     () => this.velp.edit,
        //     (newValue, oldValue) => {
        //         if (!newValue && oldValue) {
        //             scope.$evalAsync(() => {
        //                 ParCompiler.processAllMath(
        //                     this.element.find(".velpContent")
        //                 );
        //             });
        //         }
        //     }
        // );
    }

    saveButtonText() {
        if (this.new) {
            return "Add velp";
        }
        return "Save";
    }

    /**
     * Toggles velp for editing. If another velp is currently open,
     * this method closes it.
     */
    toggleVelpToEdit() {
        const lastEdited = this.velpSelection.getVelpUnderEdit();

        if (lastEdited.edit && lastEdited.id !== this.velp.id) {
            // if (this.new === "true") this.$parent.resetNewVelp();
            this.velpSelection.resetEditVelp();
        }

        this.velp.edit = !this.velp.edit;
        if (!this.velp.edit) {
            this.cancelEdit();
        } else {
            if (this.new) {
                this.velpLocal = clone(this.velp);
                // TODO: focus velp content textarea
            }
            this.velpSelection.setVelpToEdit(this.velp, () =>
                this.cancelEdit()
            );
        }
        return this.velp.edit;
    }

    /**
     * Saves velp to database
     * @param form
     */
    saveVelp(form: NgForm) {
        if (!form.form.valid) {
            return;
        }
        form.form.markAsPristine();
        // this.submitted = true;

        if (this.new) {
            // add new velp
            this.addVelp();
        } else {
            // edit velp
            this.editVelp();
        }
    }

    /**
     * Cancel edit and restore velp back to its original version
     * TODO: new velp reset does not work
     */
    cancelEdit() {
        this.velp = clone(this.velpLocal);
        this.velp.edit = false;
    }

    useVelp() {
        if (!this.velp.edit && !this.notAnnotationRights(this.velp.points)) {
            this.velpSelect.emit();
        }
    }

    /**
     * Detect user right to annotation to document.
     * @param points - Points given in velp or annotation
     * @returns {boolean} - Right to make annotations
     */
    notAnnotationRights(points: number | null) {
        if (this.teacherRight) {
            return false;
        } else {
            if (points == null || this.vctrl.docSettings.peer_review) {
                return false;
            } else {
                return true;
            }
        }
    }

    isVelpValid() {
        if (this.velp.content == null) {
            return false;
        }
        // check if still original
        if (JSON.stringify(this.velpLocal) === JSON.stringify(this.velp)) {
            return false;
        }
        return this.isSomeVelpGroupSelected() && this.velp.content.length > 0;
    }

    setLabelValid(label: INewLabel) {
        label.valid = label.content.length > 0;
    }

    /**
     * Returns whether the velp contains the label or not.
     * @param label - Label to check
     * @returns {boolean} Whether the velp contains the label or not.
     */
    isLabelInVelp(label: ILabel): boolean {
        if (label.id == null) {
            return false;
        }
        return this.velp.labels.includes(label.id);
    }

    /**
     * Checks whether the velp contains the velp group.
     * @param group - Velp group to check
     * @returns {boolean} Whether the velp contains the velp group or not
     */
    isGroupInVelp(group: IVelpGroup) {
        if (this.velp.velp_groups == null || group.id == null) {
            return false;
        }
        return this.velp.velp_groups.includes(group.id);
    }

    /**
     * Updates the labels of the velp.
     * @param label - Label to be added or removed from the velp
     */
    updateVelpLabels(label: ILabel) {
        if (label.id == null) {
            return;
        }
        const index = this.velp.labels.indexOf(label.id);
        if (index < 0) {
            this.velp.labels.push(label.id);
        } else if (index >= 0) {
            this.velp.labels.splice(index, 1);
        }
    }

    /**
     * Updates velp groups of this velp.
     * @param group - Group to be added or removed from the velp
     */
    updateVelpGroups(group: IVelpGroup) {
        if (group.id == null) {
            return;
        }
        const index = this.velp.velp_groups.indexOf(group.id);
        if (index < 0) {
            this.velp.velp_groups.push(group.id);
        } else if (index >= 0) {
            this.velp.velp_groups.splice(index, 1);
        }
    }

    /**
     * Checks if the velp has any velp groups selected.
     * @returns {boolean} Whether velp has any groups selected or not
     */
    isSomeVelpGroupSelected() {
        if (this.velp.velp_groups == null) {
            return false;
        }
        return this.velp.velp_groups.length > 0;
    }

    isSomeVelpGroupShown() {
        if (
            this.velp.velp_groups == null ||
            this.velp.velp_groups.length === 0
        ) {
            return true;
        }

        for (const vg of this.velp.velp_groups) {
            for (const g of this.velpGroups) {
                if (g.id === vg && g.show) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Adds new label to this velp.
     */
    async addLabel() {
        if (this.newLabel.content.length < 1) {
            this.newLabel.valid = false;
            return;
        }

        const data = {
            content: this.newLabel.content,
            language_id: "FI", // TODO: Change to user language
        };

        const json = await to(
            $http.post<{id: number}>("/add_velp_label", data)
        );
        if (!json.ok) {
            return;
        }
        const labelToAdd = {
            ...data,
            selected: false,
            id: json.result.data.id,
        };
        this.resetNewLabel();
        this.labels.push(labelToAdd);
        // this.labelAdded = false;
        this.velp.labels.push(labelToAdd.id);
    }

    /**
     * Selects the label for editing.
     * @param label - Label to edit
     */
    toggleLabelToEdit(label: INewLabel) {
        if (this.labelToEdit.edit && label.id === this.labelToEdit.id) {
            this.cancelLabelEdit(label);
            return;
        }

        if (this.labelToEdit.edit) {
            this.labelToEdit.edit = false;
            for (const l of this.labels) {
                l.edit = false;
            }
        }

        label.edit = true;
        this.copyLabelToEditLabel(label);
        this.setLabelValid(this.labelToEdit);
    }

    cancelLabelEdit(label: INewLabel) {
        label.edit = false;
        this.labelToEdit = {
            content: "",
            selected: false,
            edit: false,
            valid: true,
            id: null,
        };
    }

    clearVelpColor() {
        this.velp.color = "";
    }

    isVelpCustomColor() {
        if (this.velp.color) {
            return this.velp.color.length === 7; // hex colors are 7 characters long
        }
        return false;
    }

    copyLabelToEditLabel(label: INewLabel) {
        this.labelToEdit = clone(label);
    }

    /**
     * Edits the label according to the this.labelToedit variable.
     * All required data exists in the this.labelToedit variable,
     * including the ID of the label.
     * TODO: This can be simplified
     */
    editLabel() {
        if (this.labelToEdit.content.length < 1) {
            return;
        }

        let updatedLabel = null;
        for (const l of this.labels) {
            if (l.id === this.labelToEdit.id) {
                this.labelToEdit.edit = false;
                l.content = this.labelToEdit.content;
                l.edit = false;
                updatedLabel = l;
                break;
            }
        }

        $http.post("/update_velp_label", updatedLabel);
    }

    /**
     * Reset new label information to the initial (empty) state.
     */
    resetNewLabel() {
        this.newLabel = {content: "", selected: true, valid: true, id: null};
    }

    /**
     * Return true if user has teacher rights.
     * @returns {boolean}
     */
    allowChangePoints() {
        return this.teacherRight;
    }

    async editVelp() {
        const defaultVelpGroup = this.velpSelection.getDefaultVelpGroup();

        if (
            this.isGroupInVelp(defaultVelpGroup) &&
            defaultVelpGroup.id === -1
        ) {
            await this.handleDefaultVelpGroupIssue();
            await this.updateVelpInDatabase();
        } else if (this.velp.velp_groups.length > 0) {
            await this.updateVelpInDatabase();
        }
    }

    async updateVelpInDatabase() {
        await to(
            $http.post(
                "/{0}/update_velp".replace("{0}", this.docId.toString()),
                this.velp
            )
        );
        this.velpLocal = clone(this.velp);
        this.toggleVelpToEdit();
    }

    /**
     * Adds a new velp on form submit event.
     */
    async addVelp() {
        const defaultVelpGroup = this.velpSelection.getDefaultVelpGroup();
        if (
            this.isGroupInVelp(defaultVelpGroup) &&
            defaultVelpGroup.id === -1
        ) {
            await this.handleDefaultVelpGroupIssue();
            await this.addNewVelpToDatabase();
        } else if (this.velp.velp_groups.length > 0) {
            await this.addNewVelpToDatabase();
        }
        this.velpSelection.updateVelpList();
    }

    /**
     * Adds a new velp to the database. Requires values in `this.newVelp` variable.
     */
    async addNewVelpToDatabase() {
        // this.velp.edit = false;
        const data = {
            labels: this.velp.labels,
            used: 0,
            points: this.velp.points,
            content: this.velp.content,
            default_comment: this.velp.default_comment,
            language_id: "FI",
            valid_until: null,
            color: this.velp.color,
            visible_to: this.velp.visible_to ?? 4, // Everyone by default
            velp_groups: clone(this.velp.velp_groups),
            style: this.velp.style,
        };
        const json = await to($http.post<number>("/add_velp", data));
        if (!json.ok) {
            return;
        }
        const velpToAdd: IVelpUI = {
            id: json.result.data,
            ...data,
        };
        velpToAdd.id = json.result.data;
        if (this.velpSelection.rctrl.velps != null && velpToAdd.id != null) {
            this.velpSelection.rctrl.velps.push(velpToAdd);
        }

        this.velpLocal.velp_groups = velpToAdd.velp_groups;
        this.velpLocal.labels = velpToAdd.labels;

        this.toggleVelpToEdit();
        this.velpSelection.updateVelpList();

        // this.velp =  clone(this.velpLocal);
        // this.velpLocal = clone(this.velp);
        /*
         velpToAdd.id = parseInt(json.data);

         this.resetNewVelp();
         this.velpToEdit = {content: "", points: "", labels: [], edit: false, id: -1};

         this.velps.push(velpToAdd);
         this.submitted.velp = false;
         //this.resetLabels();
         */
    }

    /**
     *
     */
    async handleDefaultVelpGroupIssue() {
        const oldDefaultGroup = this.velpSelection.getDefaultVelpGroup();

        const newDefaultGroup =
            await this.velpSelection.generateDefaultVelpGroup();
        if (newDefaultGroup == null) {
            return;
        }
        if (oldDefaultGroup.id == null || newDefaultGroup.id == null) {
            return;
        }
        const oldGroupIndex = this.velp.velp_groups.indexOf(oldDefaultGroup.id);
        if (oldGroupIndex >= 0) {
            this.velp.velp_groups.splice(oldGroupIndex, 1);
        }

        this.velp.velp_groups.push(newDefaultGroup.id);
        this.velpSelection.setDefaultVelpGroup(newDefaultGroup);
    }

    /**
     * Get color for the object from colorPalette variable.
     * @param index - Index of the color in the colorPalette variable (modulo by length of color palette)
     * @returns {string} String representation of the color
     */
    getColor(index: number) {
        return colorPalette[index % colorPalette.length];
    }

    getCustomColor() {
        return this.velp.color;
    }
}
