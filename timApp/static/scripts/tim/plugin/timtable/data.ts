import * as t from "io-ts";
import {TimTable} from "tim/plugin/timtable/timTable";

export interface DataEntity {
    type: "Relative" | "Abstract";
    cells: ICellDataEntity;
}

export interface ICellIndex {
    x: number;
    y: number;
}

export interface ISelectedCells {
    cells: ICellIndex[]; // List of original cell indecies inside selected area
    srows: boolean[]; // table for screen indecies selected
    scol1: number; // screen index for first selected column
    scol2: number; // screen index for last selected column
    srow1: number; // screen index for first selected row
    srow2: number; // screen index for last selected row
}

export type ICellDataEntity = Record<string, CellEntity>;

const CellTypeR = t.union([t.string, t.number, t.boolean, t.null]);
export type CellType = t.TypeOf<typeof CellTypeR>;
export type CellEntity = ICell | CellType;

export interface IRow {
    // extends IRowStyles
    row?: CellEntity[];

    [key: string]: unknown;
}

export type IColumn = Record<string, unknown>;

export interface ICellCoord {
    row: number;
    col: number;
}

export interface ICell {
    // extends ICellStyles
    cell: CellType;
    class?: string;
    editorOpen?: boolean;
    colspan?: number;
    rowspan?: number;
    underSpanOf?: ICellCoord;
    renderIndexX?: number;
    renderIndexY?: number; // TODO: Is this useless?
    styleCache?: Record<string, string>; // cache of computed styles for this cell
    [key: string]: unknown;
}

export interface ITimTableView {
    data: TimTable;
    cellDataMatrix: ICell[][];
    rowStyleCache?: Map<number, Record<string, string>>;
}

export function cellToString(cell: CellType) {
    if (cell == null) {
        return "";
    }
    return cell.toString();
}
