import * as t from "io-ts";
import {Constructor, StringOrNumber} from "tim/util/utils";
import {IColumn, ITable} from "tim/plugin/timtable/timTable";
import {cellToString, ITimTableView} from "./data";

const styleToHtml: Record<string, string> = {
    backgroundColor: "background-color",
    border: "border",
    borderBottom: "border-bottom",
    borderLeft: "border-left",
    borderRight: "border-right",
    borderTop: "border-top",
    color: "color",
    colspan: "colspan",
    fontFamily: "font-family",
    fontSize: "font-size",
    fontWeight: "font-weight",
    height: "height",
    horizontalAlign: "horizontal-align",
    maxWidth: "max-width",
    minWidth: "min-width",
    rowspan: "rowspan",
    textAlign: "text-align",
    verticalAlign: "vertical-align",
    visibility: "visibility",
    width: "width",
};

const columnCellStyles: Set<string> = new Set<string>([
    "fontSize",
    "verticalAlign",
    "textAlign",
    "fontFamily",
    "color",
    "fontWeight",
]);

const cellStyles: Set<string> = new Set<string>([
    "verticalAlign",
    "fontSize",
    "border",
    "borderTop",
    "borderBottom",
    "borderLeft",
    "borderRight",
    "backgroundColor",
    "textAlign",
    "fontFamily",
    "color",
    "fontWeight",
    "width",
    "height",
    "colspan",
    "rowspan",
]);

const columnStyles: Set<string> = new Set<string>([
    "width",
    "backgroundColor",
    "border",
    "borderTop",
    "borderBottom",
    "borderLeft",
    "borderRight",
]);

const rowStyles: Set<string> = new Set<string>([
    "backgroundColor",
    "border",
    "borderTop",
    "borderBottom",
    "borderLeft",
    "borderRight",
    "verticalAlign",
    "textAlign",
    "color",
    "fontFamily",
    "fontSize",
    "fontWeight",
    "height",
]);

const tableStyles: Set<string> = new Set<string>([
    "backgroundColor",
    "border",
    "borderTop",
    "borderBottom",
    "borderLeft",
    "borderRight",
    "verticalAlign",
    "textAlign",
    "color",
    "fontFamily",
    "fontSize",
    "visibility",
    "width",
]);

const emptyStyle = {} as const;

export const WithStyleUtils = <T extends Constructor<ITimTableView>>(Base: T) =>
    class extends Base {
        stylingForTable(tab: ITable) {
            const styles: Record<string, string> = {};
            this.applyStyle(styles, tab, tableStyles);
            return styles;
        }

        stylingForCell(rowi: number, coli: number) {
            const cell = this.cellDataMatrix[rowi][coli];
            const sc = cell.styleCache;
            if (sc) {
                return sc;
            }
            const styles = this.stylingForCellOfColumn(coli);

            if (cellToString(cell.cell) == "") {
                styles.height = "2em";
                styles.width = "1.5em";
            }

            const def = this.data.table.defcells;
            if (def) {
                cell.class = this.applyStyle(styles, def, cellStyles);
            }

            const defrange = this.data.table.defcellsrange;
            if (defrange) {
                const rown = this.cellDataMatrix.length;
                const coln = this.cellDataMatrix[0].length;
                for (const dr of defrange) {
                    const r = dr.validrange ?? this.checkRange(dr.range);
                    dr.validrange = r;
                    if (this.checkIndex2(r, rown, coln, rowi, coli)) {
                        this.applyStyle(styles, dr.def, columnStyles);
                    }
                }
            }

            cell.class = this.applyStyle(styles, cell, cellStyles);

            if (this.data.maxWidth) {
                styles["max-width"] = this.data.maxWidth;
                styles.overflow = "hidden";
            }
            if (this.data.minWidth) {
                styles["min-width"] = this.data.minWidth;
            }
            if (this.data.singleLine) {
                styles["white-space"] = "nowrap";
            }
            cell.styleCache = styles;
            return styles;
        }

        stylingForRow(rowi: number) {
            if (!this.data.table) {
                return emptyStyle;
            }
            const cached = this.rowStyleCache?.get(rowi);
            if (cached) {
                return cached;
            }
            const styles: Record<string, string> = {};

            const def = this.data.table.defrows;
            if (def) {
                this.applyStyle(styles, def, rowStyles);
            }
            const defrange = this.data.table.defrowsrange;
            if (defrange) {
                // todo: do all this on init
                const n = this.cellDataMatrix.length;
                for (const dr of defrange) {
                    const r = dr.validrange ?? this.checkRange(dr.range);
                    dr.validrange = r;
                    if (this.checkIndex(r, n, rowi)) {
                        this.applyStyle(styles, dr.def, rowStyles);
                    }
                }
            }

            if (!this.data.table.rows || rowi >= this.data.table.rows.length) {
                return styles;
            }

            const row = this.data.table.rows[rowi];
            this.applyStyle(styles, row, rowStyles);
            this.rowStyleCache?.set(rowi, styles);
            return styles;
        }

        stylingForColumn(col: IColumn, index: number) {
            /*
            if (this.data.nrColumn) {
                index--;
                if (index < 0) { return; }
            }
            */

            const styles: Record<string, string> = {};

            const def = this.data.table.defcols;
            if (def) {
                this.applyStyle(styles, def, columnStyles);
            }

            const defrange = this.data.table.defcolsrange;
            if (defrange) {
                const n = this.cellDataMatrix[0].length;
                for (const dr of defrange) {
                    const r = dr.validrange ?? this.checkRange(dr.range);
                    dr.validrange = r;
                    if (this.checkIndex(r, n, index)) {
                        this.applyStyle(styles, dr.def, columnStyles);
                    }
                }
            }

            this.applyStyle(styles, col, columnStyles);
            return styles;
        }

        checkRange(
            dr: readonly number[] | number | string | undefined
        ): readonly number[] | undefined {
            const r = dr;
            if (!r) {
                return;
            }
            if (typeof r === "number") {
                return [r];
            }
            if (typeof r !== "string") {
                return r;
            }

            const json = "[" + r.replace("[", "").replace("]", "") + "]";
            try {
                const parsed = JSON.parse(json);
                if (t.array(t.number).is(parsed)) {
                    return parsed;
                } else {
                    return [];
                }
            } catch (e) {
                return [];
            }
        }

        checkIndex(
            r: readonly number[] | undefined,
            n: number,
            index: number
        ): boolean {
            if (!r) {
                return false;
            }
            if (r.length == 0) {
                return false;
            }
            const i1 = this.toIndex(r, 0, n, 0);
            if (index < i1) {
                return false;
            }
            const i2 = this.toIndex(r, 1, n, i1);
            return i2 >= index;
        }

        checkIndex2(
            r: readonly number[] | undefined,
            rown: number,
            coln: number,
            rowi: number,
            coli: number
        ): boolean {
            if (!r) {
                return false;
            }
            if (r.length == 0) {
                return false;
            }
            const ir1 = this.toIndex(r, 0, rown, 0);
            if (rowi < ir1) {
                return false;
            }
            const ic1 = this.toIndex(r, 1, coln, 0);
            if (coli < ic1) {
                return false;
            }
            const ir2 = this.toIndex(r, 2, rown, ir1);
            if (ir2 < rowi) {
                return false;
            }
            const ic2 = this.toIndex(r, 3, coln, ic1);
            return ic2 >= coli;
        }

        toIndex(r: readonly number[], i: number, n: number, def: number) {
            if (r.length <= i) {
                return def;
            }
            let idx = r[i];
            if (idx < 0) {
                idx = n + idx;
            }
            if (idx < 0) {
                idx = 0;
            }
            if (idx >= n) {
                idx = n - 1;
            }
            return idx;
        }

        stylingForCellOfColumn(coli: number) {
            const styles: Record<string, string> = {};
            const table = this.data.table;

            if (!table.columns) {
                return styles;
            }

            if (table.columns.length <= coli) {
                return styles;
            }

            const col = table.columns[coli];

            if (!col) {
                return styles;
            }

            this.applyStyle(styles, col, columnCellStyles);
            return styles;
        }

        /**
         * Generic function for setting style attributes.
         * Verifies that given style attributes are valid and applies them.
         * Non-valid style attributes are not applied.
         * @param styles The dictionary that will contain the final object styles
         * @param object The object that contains the user-given style attributes
         * @param validAttrs A set that contains the accepted style attributes
         * @return posible class
         */
        applyStyle(
            styles: Record<string, string | number>,
            object: Record<string, unknown> | undefined,
            validAttrs: Set<string>
        ): string {
            if (!object) {
                return "";
            }
            let cls: string = "";
            for (const [key, value] of Object.entries(object)) {
                // At least fontSize needs to be a number, so we accept numbers too.
                if (key === "class") {
                    cls = String(value);
                    continue;
                }
                if (!validAttrs.has(key) || !StringOrNumber.is(value)) {
                    continue;
                }

                const property = styleToHtml[key];
                if (!property) {
                    continue;
                }

                styles[property] = value;
            }
            return cls;
        }
    };
