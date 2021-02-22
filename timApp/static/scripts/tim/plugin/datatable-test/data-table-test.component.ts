import {Component, Injectable, Input, NgModule, OnInit} from "@angular/core";
import {NgxDatatableModule} from "@swimlane/ngx-datatable";
import {CommonModule} from "@angular/common";
import {isPrimitiveCell, TimTable} from "tim/plugin/timtable/timTable";
import {ICell, ITimTableView} from "tim/plugin/timtable/data";
import {WithStyleUtils} from "tim/plugin/timtable/styleUtils";
import {colnumToLetters} from "../timtable/timTable";

@Injectable()
class DataTableBase implements ITimTableView {
    cellDataMatrix!: ICell[][];
    @Input() data!: TimTable;
    rowStyleCache!: Map<number, Record<string, string>>;
}

const DataTable = WithStyleUtils(DataTableBase);

@Component({
    selector: "tim-data-table-test",
    template: `
        <div>
            <ngx-datatable [style]="tableStyle" [rows]="rows" [scrollbarV]="true" columnMode="standard" [rowHeight]="30" [footerHeight]="0"
                           [headerHeight]="30">
                <ngx-datatable-column *ngFor="let col of columns" [name]="col.name" [prop]="col.prop"
                                      [width]="300"
                                      [headerTemplate]="hdrCell" [cellTemplate]="mainCell"
                                      [canAutoResize]="true"></ngx-datatable-column>
            </ngx-datatable>
        </div>
        <ng-template #hdrCell let-column="column">
            <div class="draggable" [style]="headersStyle">{{column.name}}</div>
        </ng-template>
        <ng-template #mainCell let-value="value" let-rowIndex="rowIndex" let-rowHeight="rowHeight">
            <div>
                <span>{{value}}</span>
            </div>
        </ng-template>
    `,
    styleUrls: ["./data-table-test.component.scss"],
    inputs: ["data"],
})
export class DataTableTestComponent
    extends DataTable
    implements OnInit, ITimTableView {
    rows: Record<string, unknown>[] = [];
    columns: {name: string; prop: number}[] = [];
    headersStyle?: Record<string, string> = {};
    tableStyle: Record<string, string> = {};

    constructor() {
        super();
    }

    ngOnInit(): void {
        this.initFromTimTableData();
    }

    private initFromTimTableData() {
        if (!this.data) {
            return;
        }

        this.tableStyle = this.stylingForTable(this.data.table);

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
