import {Component, Input, NgModule, OnInit} from "@angular/core";
import {NgxDatatableModule} from "@swimlane/ngx-datatable";
import {CommonModule} from "@angular/common";
import {isPrimitiveCell, TimTable} from "tim/plugin/timTable";
import {colnumToLetters} from "../timTable";

type TableData = TimTable;

@Component({
    selector: "tim-data-table-test",
    template: `
        <div>
            <ngx-datatable [rows]="rows" [scrollbarV]="true" columnMode="force" [rowHeight]="50" [headerHeight]="50">
                <ngx-datatable-column *ngFor="let col of columns" [name]="col.name" [prop]="col.prop"
                                      [headerTemplate]="hdrCell"></ngx-datatable-column>
            </ngx-datatable>

            <ng-template #hdrCell let-column="column">
                <div [style]="headersStyle">{{column.name}}</div>
            </ng-template>
        </div>
    `,
    styleUrls: ["./data-table-test.component.scss"],
})
export class DataTableTestComponent implements OnInit {
    /**
     * Table data that's compatible with TimTable format
     */
    @Input() data?: TableData;

    rows: Record<string, unknown>[] = [];

    columns: {name: string; prop: number}[] = [];

    headersStyle?: Record<string, string> = {};

    constructor() {}

    ngOnInit(): void {
        this.initFromTimTableData();
    }

    private initFromTimTableData() {
        if (!this.data) {
            return;
        }

        if (!this.data.headers) {
            return;
        }

        this.headersStyle = this.data.headersStyle ?? this.headersStyle;
        for (const [i, header] of this.data.headers.entries()) {
            this.columns.push({
                name: header,
                prop: i,
            });
        }

        const colMax = this.data.table.countCol ?? 0;
        const rowMax = this.data.table.countRow ?? 0;

        const newRows: Record<string, unknown>[] = [];
        for (let row = 0; row < rowMax; row++) {
            const rowObj: Record<string, unknown> = {};
            for (let col = 0; col < colMax; col++) {
                const coord = `${colnumToLetters(col)}${row + 1}`;
                const cell = this.data?.userdata?.cells[coord];
                if (cell) {
                    rowObj[col] = isPrimitiveCell(cell) ? cell : cell.cell;
                }
            }
            newRows.push(rowObj);
        }
        this.rows = newRows;
    }
}

@NgModule({
    declarations: [DataTableTestComponent],
    imports: [NgxDatatableModule, CommonModule],
    exports: [DataTableTestComponent],
})
export class DataTableTestModule {
    constructor() {}
}
