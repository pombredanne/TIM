import {IAngularEvent, IController, IRootElementService, IScope} from "angular";
import * as allanswersctrl from "tim/answer/allAnswersController";
import {timApp} from "tim/app";
import uiGrid, {IFilterOptions, IGridColumnOf, IGridRowOf} from "ui-grid";
import {ViewCtrl} from "../document/viewctrl";
import {DialogController, registerDialogComponent, showDialog, showMessageDialog} from "../ui/dialog";
import {IUser} from "../user/IUser";
import {$timeout} from "../util/ngimport";
import {Binding, getURLParameter, markAsUsed, Require} from "../util/utils";
import {showAllAnswers} from "./allAnswersController";
import {showFeedbackAnswers} from "./feedbackAnswersController";

markAsUsed(allanswersctrl);

interface IFixedFilterOptions extends IFilterOptions {
    rawTerm?: boolean;
}

export interface IExportOptions {
    totalPointField: string;
    velpPointField: string;
    taskPointField: string;
    copy: boolean;
}

function filterFn(term: string, cellValue: any, row: IGridRowOf<any>, column: IGridColumnOf<any>) {
    try {
        return new RegExp(term, "i").test(cellValue);
    } catch {
        return false;
    }
}

export class UserListController implements IController {
    static $inject = ["$scope", "$element"];
    private gridOptions?: uiGrid.IGridOptions & {gridMenuCustomItems: any};
    private scope: IScope;
    private gridApi?: uiGrid.IGridApiOf<IUser>;
    private instantUpdate: boolean = false;
    private columns!: Array<uiGrid.IColumnDefOf<IUser>>; // $onInit
    private onUserChange!: Binding<(params: {$USER: IUser, $UPDATEALL: boolean}) => void, "&">;
    private viewctrl!: Require<ViewCtrl>;
    private element: IRootElementService;
    private preventedChange = false;

    constructor(scope: IScope, element: IRootElementService) {
        this.scope = scope;
        this.element = element;
    }

    $onInit() {
        this.scope.$watch(
            () => this.element[0].offsetHeight + this.element[0].offsetWidth,
            (sum) => {
                const grid = this.element.find(".grid");
                grid.css("width", (this.element[0].offsetWidth - 5) + "px");
                grid.css("height", (this.element[0].offsetHeight - 30) + "px");
            },
        );

        let anyAnnotations = false;
        let smallFieldWidth = 59;

        for (const u of this.viewctrl.users) {
            if (u.velped_task_count > 0) {
                anyAnnotations = true;
                smallFieldWidth = 40;
                break;
            }
        }

        this.columns = [
            {
                field: "real_name",
                name: "Full name",
                cellTooltip: true,
                headerTooltip: true,
            },
            {
                field: "name",
                name: "Username",
                cellTooltip: true,
                headerTooltip: true,
                maxWidth: 100,
            },
            {
                field: "task_count",
                name: "Tasks",
                cellTooltip: true,
                headerTooltip: true,
                maxWidth: smallFieldWidth,
            },
            {
                field: "task_points",
                name: "Task points",
                cellTooltip: true,
                headerTooltip: true,
                maxWidth: smallFieldWidth,
                visible: anyAnnotations,
            },
            {
                field: "velped_task_count",
                name: "Velped tasks",
                cellTooltip: true,
                headerTooltip: true,
                maxWidth: smallFieldWidth,
                visible: anyAnnotations,
            },
            {
                field: "velp_points",
                name: "Velp points",
                cellTooltip: true,
                headerTooltip: true,
                maxWidth: smallFieldWidth,
                visible: anyAnnotations,
            },
            {
                field: "total_points",
                name: "Points",
                cellTooltip: true,
                headerTooltip: true,
                maxWidth: smallFieldWidth,
            },
        ];
        for (const c of this.columns) {
            const f: IFixedFilterOptions = {
                condition: filterFn,
                rawTerm: true, // Required for RegExp to work.
            };
            c.filter = f;
        }
        this.instantUpdate = this.viewctrl.docSettings.form_mode || false;

        this.gridOptions = {
            exporterMenuPdf: false,
            multiSelect: false,
            enableFullRowSelection: true,
            enableRowHeaderSelection: false,
            noUnselect: true,
            enableFiltering: true,
            enableColumnMenus: false,
            enableGridMenu: true,
            data: this.viewctrl.users,
            enableSorting: true,
            columnDefs: this.columns,
            onRegisterApi: (gridApi) => {
                this.gridApi = gridApi;

                gridApi.selection.on.rowSelectionChanged(this.scope, (row) => {
                    this.fireUserChange(row, this.instantUpdate);
                });
                if (this.gridOptions && this.gridOptions.data) {
                    gridApi.grid.modifyRows(this.gridOptions.data as any[]);
                    gridApi.selection.selectRow(this.gridOptions.data[0]);
                    const userName = getURLParameter("user");
                    if (userName) {
                        const foundUser = this.findUserByName(userName);
                        if (foundUser) {
                            this.gridApi.selection.selectRow(foundUser);
                        } else {
                            void showMessageDialog(`User ${userName} not found from answerers.`);
                            gridApi.selection.selectRow(this.gridOptions.data[0]);
                        }
                    } else {
                        gridApi.selection.selectRow(this.gridOptions.data[0]);
                    }
                }
                gridApi.cellNav.on.navigate(this.scope, (newRowCol, oldRowCol) => {
                    // TODO: check if simple way to cancel this event here
                    //  or make unsavitimcomponents checks at keyboardpress/click events before on.navigate gets called
                    if (this.preventedChange) {
                        this.preventedChange = false;
                        return;
                    }

                    if (oldRowCol && oldRowCol.row === newRowCol.row) { return; }
                    const unsavedTimComponents = this.viewctrl.checkUnSavedTimComponents("userChange");
                    if (unsavedTimComponents && !window.confirm("You have unsaved changes. Change user anyway?")) {
                        this.preventedChange = true;
                        if (oldRowCol) {
                            gridApi.cellNav.scrollToFocus(oldRowCol.row.entity, oldRowCol.col.colDef);
                        } else {
                            if (this.gridOptions && this.gridOptions.data && this.gridOptions.columnDefs) {
                                gridApi.cellNav.scrollToFocus(this.gridOptions.data[0], this.gridOptions.columnDefs[0]);
                            }
                        }
                        return;
                    }
                    gridApi.selection.selectRow(newRowCol.row.entity);
                });
            },
            gridMenuCustomItems: [
                {
                    title: "Export to Korppi",
                    action: ($event: IAngularEvent) => {
                        $timeout(async () => {
                            const options = await showKorppiExportDialog();
                            this.exportKorppi(options);
                        });
                    },
                    order: 10,
                },
                {
                    title: "Enable instant update",
                    action: ($event: IAngularEvent) => {
                        this.instantUpdate = true;
                    },
                    shown: () => {
                        return !this.instantUpdate;
                    },
                    leaveOpen: true,
                    order: 20,
                },
                {
                    title: "Disable instant update",
                    action: ($event: IAngularEvent) => {
                        this.instantUpdate = false;
                    },
                    shown: () => {
                        return this.instantUpdate;
                    },
                    leaveOpen: true,
                    order: 30,
                },
                {
                    title: "Answers as plain text",
                    action: async ($event: IAngularEvent) => {
                        await showAllAnswers({
                            url: "/allDocumentAnswersPlain/" + this.viewctrl.item.id,
                            identifier: this.viewctrl.item.id.toString(),
                            allTasks: true,
                        });
                    },
                    order: 40,
                },
                {
                    title: "Create Feedback Report",
                    action: async ($event: IAngularEvent) => {
                        let iusers: IUser[];
                        iusers = [];
                        if (this.gridApi) {
                            const selectedUser = this.gridApi.selection.getSelectedRows()[0];
                            iusers.push(selectedUser);

                            const visibleRows = this.gridApi.core.getVisibleRows(this.gridApi.grid);

                            for (const row of visibleRows) { // Create string array of visible item.
                                if (row.entity !== selectedUser) {
                                    iusers.push(row.entity);
                                }
                            }
                            if (visibleRows.length <= 0) {
                                iusers = [];
                            }
                        }
                        await showFeedbackAnswers({
                            url: "/feedback/report/" + this.viewctrl.item.id,
                            users: iusers,
                            identifier: this.viewctrl.item.id.toString(),
                            allTasks: true,
                        });
                    },
                    order: 50,
                },
            ],
            rowTemplate: "<div ng-dblclick=\"grid.appScope.fireUserChange(row, true)\" ng-repeat=\"(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name\" class=\"ui-grid-cell\" ng-class=\"{ 'ui-grid-row-header-cell': col.isRowHeader }\" ui-grid-cell></div>",
        };
    }

    fireUserChange(row: uiGrid.IGridRowOf<IUser>, updateAll: boolean) {
        this.onUserChange({$USER: row.entity, $UPDATEALL: updateAll});
    }

    copyHelperElement: HTMLTextAreaElement | undefined;

    getClipboardHelper(): HTMLTextAreaElement {  // TODO: could be a TIM global function
        let e1 = this.copyHelperElement;  // prevent extra creating and deleting
        if (e1) {
            return e1;
        }
        e1 = document.createElement("textarea");
        e1.setAttribute("readonly", "");
        // e1.style.position = 'absolute';
        e1.style.position = "fixed"; // fixed seems better for FF and Edge so not to jump to end
        // e1.style.left = '-9999px';
        e1.style.top = "-9999px";
        document.body.appendChild(e1);
        // document.body.removeChild(el);
        this.copyHelperElement = e1;
        return e1;
    }

    copyToClipboard(s: string) {  // TODO: could be a TIM global function
        const e1 = this.getClipboardHelper();
        e1.value = s;
        const isIOS = navigator.userAgent.match(/ipad|ipod|iphone/i);
        if (isIOS) {
            // e1.contentEditable = true;
            e1.readOnly = true;
            const range = document.createRange();
            range.selectNodeContents(e1);
            const sel = window.getSelection();
            if (sel) {
                sel.removeAllRanges();
                sel.addRange(range);
            }
            e1.setSelectionRange(0, 999999);
        } else {
            e1.select();
        }
        document.execCommand("copy");
    }

    exportKorppi(options: IExportOptions) {
        if (!options.taskPointField && !options.velpPointField && !options.totalPointField) {
            return;
        }
        if (!this.gridApi) {
            throw new Error("gridApi was not initialized");
        }
        const data = this.gridApi.core.getVisibleRows(this.gridApi.grid);
        let dataKorppi = "";

        const fields = ["total_points", "task_points", "velp_points", ""];
        const fieldNames = new Map<string, string>();
        fieldNames.set(fields[0], options.totalPointField);
        fieldNames.set(fields[1], options.taskPointField);
        fieldNames.set(fields[2], options.velpPointField);
        let filename;
        for (const f of fields) {
            const fieldName = fieldNames.get(f);
            if (fieldName) {
                filename = (filename || fieldName + ".txt");
                if (dataKorppi !== "") {
                    dataKorppi += "\n";
                }
                for (const d of data) {
                    const entity = d.entity as any;
                    if (entity[f] != null) {
                        dataKorppi += entity.name + ";" + fieldName + ";" + entity[f] + "\n";
                    }
                }
            }
        }

        if (!filename) {
            filename = "korppi_" + this.viewctrl.docId + ".txt";
        }

        if ( options.copy ) {
            this.copyToClipboard(dataKorppi);
            return;
        }
        // from https://stackoverflow.com/a/33542499

        const blob = new Blob([dataKorppi], {type: "text/plain"});
        if (window.navigator.msSaveOrOpenBlob) {
            window.navigator.msSaveBlob(blob, filename);
        } else {
            const elem = window.document.createElement("a");
            elem.href = window.URL.createObjectURL(blob);
            elem.download = filename;
            document.body.appendChild(elem);
            elem.click();
            document.body.removeChild(elem);
        }
        /*
        const opened = window.open("text/plain", "replace");
        if ( !opened ) { return; }
        opened.document.write(dataKorppi);
        opened.close();
        */

    }

    private findUserByName(userName: string) {
        return this.viewctrl.users.find((u) => u.name === userName);
    }
}

timApp.component("timUserList", {
    bindings: {
        onUserChange: "&",
        users: "<", // unused?
    },
    controller: UserListController,
    require: {
        viewctrl: "^timView",
    },
    template: `<div
     class="userlist"
     ng-if="$ctrl.users"
     ui-grid="$ctrl.gridOptions"
     ui-grid-selection
     ui-grid-exporter
     ui-grid-auto-resize
     ui-grid-cellNav>
</div>
<div ng-if="!$ctrl.users">
    No answerers.
</div>`,
});

export class KorppiExportCtrl extends DialogController<{}, IExportOptions> {
    static component = "timKorppiExport";
    static $inject = ["$element", "$scope"] as const;
    private options: IExportOptions = {totalPointField: "", velpPointField: "", taskPointField: "", copy: false};

    protected getTitle() {
        return "Export to Korppi";
    }

    ok() {
        this.close(this.options);
    }

    copy() {
        this.options.copy = true;
        this.close(this.options);
    }
}

registerDialogComponent(KorppiExportCtrl, {templateUrl: "/static/templates/korppiExport.html"});

function showKorppiExportDialog() {
    return showDialog(KorppiExportCtrl, {}).result;
}
