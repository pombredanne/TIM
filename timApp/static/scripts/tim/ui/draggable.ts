import {IController, IRootElementService, IScope} from "angular";
import {IModalInstanceService} from "angular-ui-bootstrap";
import {timApp} from "tim/app";
import {timLogTime} from "tim/util/timTiming";
import {$compile, $document} from "../util/ngimport";
import {
    Binding,
    getOutOffsetFully,
    getOutOffsetVisible,
    getPageXYnull,
    getStorage,
    IBounds,
    ISize,
    isMobileDevice,
    setStorage
} from "../util/utils";

function getPixels(s: string) {
    const s2 = s.replace(/px$/, "");
    return Number(s2) || 0;
}

const draggableTemplate = `
<div class="draghandle" ng-mousedown="d.dragClick()" ng-show="d.canDrag()">
    <p ng-show="d.caption" ng-bind="d.caption"></p>
    <i ng-show="d.closeFn"
       title="Close dialog"
       ng-click="d.closeFn()"
       class="glyphicon glyphicon-remove pull-right"></i>
    <i ng-show="d.click"
       title="Minimize dialog"
       ng-click="d.toggleMinimize()"
       class="glyphicon glyphicon-minus pull-right"></i>
</div>
<button class="timButton pull-right" ng-show="d.detachable" ng-click="d.toggleDetach()">
    <i class="glyphicon glyphicon-arrow-{{ d.canDrag() ? 'left' : 'right' }}"></i>
</button>
<div ng-show="d.canResize() && !d.autoWidth"
     class="resizehandle-r resizehandle"></div>
<div ng-show="d.canResize() && !d.autoHeight"
     class="resizehandle-d resizehandle"></div>
<div ng-show="d.canResize() && !d.autoWidth && !d.autoHeight"
     class="resizehandle-rd resizehandle"></div>
    `;

timApp.directive("timDraggableFixed", [() => {
    return {
        bindToController: {
            absolute: "<?",
            caption: "@?",
            click: "<?",
            detachable: "<?",
            forceMaximized: "<?",
            resize: "<?",
            save: "@?",
        },
        controller: DraggableController,
        controllerAs: "d", // default $ctrl does not work, possibly because of some ng-init
        require: {
            parentDraggable: "?^^timDraggableFixed", // for checking whether we are inside some other draggable
        },
        restrict: "A",
        scope: {},
        // Using template + transclude here does not work for some reason with uib-modal, so we compile the
        // template manually in $postLink.
    };
}]);

interface Pos {
    X: number;
    Y: number;
}

interface IResizeStates {
    up: boolean;
    down: boolean;
    left: boolean;
    right: boolean;
}

export class DraggableController implements IController {
    private static $inject = ["$scope", "$element"];

    private posKey?: string;
    private areaMinimized: boolean = false;
    private areaHeight: number = 0;
    private areaWidth: number = 0;
    private setLeft: boolean = true;
    private setRight: boolean = false;
    private setBottom: boolean = false;
    private setTop: boolean = true;
    private prev: IBounds = {left: 0, right: 0, bottom: 0, top: 0};
    private prevSize: ISize = {width: 0, height: 0};
    private resizeStates: IResizeStates = {up: false, down: false, right: false, left: false};
    private lastPos: Pos = {X: 0, Y: 0};
    private pos?: Pos;
    private delta?: Pos;
    private lastPageXYPos = {X: 0, Y: 0};
    private handle?: JQuery;
    private closeFn?: () => void;
    private caption?: Binding<string, "<">;
    private click?: Binding<boolean, "<">;
    private detachable?: Binding<boolean, "<">;
    private resize?: Binding<boolean, "<">;
    private save?: Binding<string, "<">;
    private dragClick?: () => void;
    private autoHeight?: boolean;
    private absolute?: Binding<boolean, "<">;
    private parentDraggable?: DraggableController;
    private forceMaximized?: Binding<boolean, "<">;
    private modal?: IModalInstanceService;

    constructor(private scope: IScope, private element: IRootElementService) {
    }

    isModal() {
        return this.element.parent(".modal").length === 1;
    }

    $onInit() {
        // hide element temporarily to avoid flashing the dialog in wrong position briefly
        this.setVisibility("hidden");
        if (this.save) {
            const pageId = window.location.pathname.split("/")[1];
            this.posKey = this.save.replace("%%PAGEID%%", pageId);
        }
    }

    private setVisibility(v: "visible" | "hidden") {
        this.element.css("visibility", v);
    }

    setCaption(caption: string) {
        this.caption = caption;
    }

    async makeHeightAutomatic() {
        // workaround for Chrome issue where the browser jumps to the start of page when opening a dialog that
        // calls this
        await this.getModal();

        this.element.css("height", "auto");
        this.autoHeight = true;
    }

    private toggleDetach() {
        if (this.canDrag()) {
            this.element.css("position", "static");
            for (const prop of ["width", "height"]) {
                this.element.css(prop, "");
            }
        } else {
            this.element.css("position", "absolute");
            this.restoreSizeAndPosition();
        }
        setStorage(this.posKey + "detach", this.canDrag());
    }

    private async makeModalPositionAbsolute() {
        const modal = await this.getModal();
        if (!modal) {
            return;
        }
        modal.css("position", "absolute");
    }

    private async getModal() {
        if (!this.modal) {
            return;
        }

        // We don't want "this.modal.opened" here because then the saved position gets set incorrectly
        // (20px too much left). On the other hand, when using "rendered", we have to manually hide the modal while
        // loading its old position to avoid it being flashed briefly in wrong position.
        // This is done in $onInit and setInitialLayout.
        await this.modal.rendered;
        return this.element.parents(".modal");
    }

    public isMinimized() {
        return this.areaMinimized;
    }

    private async modalHasAbsolutePosition() {
        const m = await this.getModal();
        if (!m) {
            return false;
        }
        return m.css("position") === "absolute" && this.parentDraggable == null;
    }

    private elementHasAbsoluteOrRelativePosition() {
        const s = this.element.css("position");
        return s === "absolute" || s === "relative";
    }

    setDragClickFn(fn: () => void) {
        this.dragClick = fn;
    }

    setCloseFn(fn: (() => void) | undefined) {
        this.closeFn = fn;
    }

    async $postLink() {
        this.element.prepend($compile(draggableTemplate)(this.scope));
        this.createResizeHandlers();
        this.handle = this.element.children(".draghandle");

        this.handle.on("mousedown pointerdown touchstart", (e: JQueryEventObject) => {
            this.resizeStates = {
                up: false,
                down: false,
                left: false,
                right: false,
            };
            $document.off("mouseup pointerup touchend", this.release);
            $document.off("mousemove pointermove touchmove", this.move);
            this.lastPos = this.getPageXY(e);
            // Rules for what we should set in CSS
            // to keep the element dimensions (X).
            // Prefer left over right.
            this.getSetDirs();
            // prevTop = this.element.position().top;
            // prevLeft = this.element.position().left;

            $document.on("mouseup pointerup touchend", this.release);
            $document.on("mousemove pointermove touchmove", this.move);
        });

        // DialogController will call setInitialLayout in case draggable is inside modal
        if (!this.isModal()) {
            await this.setInitialLayout();
        }
    }

    public async setInitialLayout() {
        if (this.absolute) {
            await this.makeModalPositionAbsolute();
        }
        if (isMobileDevice()) {
            const modal = await this.getModal();
            if (modal) {
                modal.css("overflow", "visible");
            }
        }
        if (this.posKey) {
            this.getSetDirs();
            await this.restoreSizeAndPosition();
            if (getStorage(this.posKey + "min") && !this.forceMaximized) {
                this.toggleMinimize();
            }
            if (getStorage(this.posKey + "detach")) {
                this.toggleDetach();
            }
        }
        // restore visibility (see $onInit)
        this.setVisibility("visible");
    }

    private async restoreSizeAndPosition() {
        if (!this.posKey) {
            return;
        }
        const oldSize: any = getStorage(this.posKey +
            "Size");
        if (oldSize && this.elementHasAbsoluteOrRelativePosition()) {
            if (oldSize.width) {
                this.element.css("width",
                    oldSize.width);
            }
            if (oldSize.height && !this.autoHeight) {
                this.element.css("height",
                    oldSize.height);
            }
        }
        const oldPos: {left: string, right: string, top: string, bottom: string} | null = getStorage(this.posKey);
        // it doesn't make sense to restore Y position if the dialog has absolute position (instead of fixed)
        if (await this.modalHasAbsolutePosition()) {
            const off = this.element.offset() || {left: 20};
            this.element.offset({top: window.pageYOffset, left: off.left});
        }
        if (oldPos) {
            if (oldPos.left && this.setLeft) {
                this.element.css("left", oldPos.left);
            }
            if (oldPos.right && this.setRight) {
                this.element.css("right", oldPos.right);
            }
            if (!await this.modalHasAbsolutePosition()) {
                if (oldPos.top && this.setTop) {
                    this.element.css("top", oldPos.top);
                }
                if (oldPos.bottom && this.setBottom) {
                    this.element.css("bottom", oldPos.bottom);
                }
            }
            timLogTime("oldpos:" + oldPos.left + ", " + oldPos.top, "drag");
        }
        if (oldPos || oldSize) {
            this.ensureVisibleInViewport();
        }
    }

    getWidth(): number {
        const w = this.element.width();
        if (w == null) {
            // should never happen because element is not empty set
            throw new Error("this.element.width() returned null");
        }
        return w;
    }

    getHeight(): number {
        const w = this.element.height();
        if (w == null) {
            // should never happen because element is not empty set
            throw new Error("this.element.height() returned null");
        }
        return w;
    }

    toggleMinimize() {
        this.areaMinimized = !this.areaMinimized;
        const base = this.element.find(".draggable-content");
        if (this.areaMinimized) {
            this.areaHeight = this.getHeight();
            this.areaWidth = this.getWidth();
            this.element.height(15);
            this.element.width(200);
            this.element.css("left", this.getCss("left") + (this.areaWidth - this.getWidth()));

            base.css("display", "none");
            this.element.css("min-height", "0");
            setStorage(this.posKey + "min", true);
        } else {
            base.css("display", "");
            this.element.css("min-height", "");
            this.element.css("left", this.getCss("left") - (this.areaWidth - this.getWidth()));
            if (this.autoHeight) {
                this.element.height("auto");
            } else {
                this.element.height(this.areaHeight);
            }
            this.element.width(this.areaWidth);
            setStorage(this.posKey + "min", false);
        }
    }

    private getSetDirs() {
        const leftSet = this.element.css("left") != "auto";
        const rightSet = this.element.css("right") != "auto";
        this.setLeft = (!leftSet && !rightSet) || leftSet;
        this.setRight = rightSet;
        // setLeft = true; // because for some reason in iPad it was right???

        // Rules for what we should set in CSS
        // to keep the element dimensions (Y).
        // Prefer top over bottom.

        const topSet = this.element.css("top") != "auto";
        const botSet = this.element.css("bottom") != "auto";
        this.setTop = (!topSet && !botSet) || topSet;
        this.setBottom = botSet;
        this.prevSize = {
            height: this.getHeight(),
            width: this.getWidth(),
        };

        this.prev = {
            top: getPixels(this.element.css("top")),
            left: getPixels(this.element.css("left")),
            bottom: getPixels(this.element.css("bottom")),
            right: getPixels(this.element.css("right")),
        };
        timLogTime("set:" + [this.setLeft, this.setTop, this.setBottom, this.setRight].join(", "), "drag");
    }

    private resizeElement(e: JQueryEventObject, up: boolean, right: boolean, down: boolean, left: boolean) {
        this.resizeStates = {up, down, left, right};
        $document.off("mouseup pointerup touchend", this.release);
        $document.off("mousemove pointermove touchmove", this.moveResize);
        this.lastPos = this.getPageXY(e);

        this.getSetDirs();

        $document.on("mouseup pointerup touchend", this.release);
        $document.on("mousemove pointermove touchmove", this.moveResize);
    }

    private createResizeHandlers() {
        const handleRight = this.element.children(".resizehandle-r");
        handleRight.on("mousedown pointerdown touchstart", (e: JQueryEventObject) => {
            this.resizeElement(e, false, true, false, false);
        });
        const handleDown = this.element.children(".resizehandle-d");
        handleDown.on("mousedown pointerdown touchstart", (e: JQueryEventObject) => {
            this.resizeElement(e, false, false, true, false);
        });
        const handleRightDown = this.element.children(".resizehandle-rd");
        handleRightDown.on("mousedown pointerdown touchstart", (e: JQueryEventObject) => {
            this.resizeElement(e, false, true, true, false);
        });
    }

    private canDrag() {
        return this.element.css("position") !== "static";
    }

    private canResize() {
        return !this.areaMinimized && this.resize && this.canDrag();
    }

    private getPageXY(e: JQueryEventObject) {
        const pos = getPageXYnull(e);
        if (pos) {
            this.lastPageXYPos = pos;
        }
        return this.lastPageXYPos;
    }

    private getCss(key: "left" | "right" | "bottom" | "top") {
        return getPixels(this.element.css(key));
    }

    // The methods release, move and moveResize are required to be instance
    // functions because they are used as callbacks for $document.on/off.
    release = (e: JQueryEventObject) => {
        $document.off("mouseup pointerup touchend", this.release);
        $document.off("mousemove pointermove touchmove", this.move);
        $document.off("mousemove pointermove touchmove", this.moveResize);
        this.pos = this.getPageXY(e);
        this.ensureVisibleInViewport();
        if (this.posKey) {
            const css = this.element.css(["top", "bottom", "left",
                "right"]);
            setStorage(this.posKey, css);

            timLogTime("pos:" + css.left + "," + css.top, "drag");
        }
    }

    private ensureFullyInViewport() {
        const bound = getOutOffsetFully(this.element[0]);
        this.setCssFromBound(bound);
    }

    private ensureVisibleInViewport() {
        const bound = getOutOffsetVisible(this.element[0]);
        this.setCssFromBound(bound);
    }

    private setCssFromBound(bound: IBounds) {
        if (this.setTop) {
            this.element.css("top", this.getCss("top") - bound.top + bound.bottom);
        }
        if (this.setBottom) {
            this.element.css("bottom", this.getCss("bottom") - bound.bottom + bound.top);
        }
        if (this.setLeft) {
            this.element.css("left", this.getCss("left") - bound.left + bound.right);
        }
        if (this.setRight) {
            this.element.css("right", this.getCss("right") - bound.right + bound.left);
        }
    }

    move = (e: JQueryEventObject) => {
        this.pos = this.getPageXY(e);
        this.delta = {
            X: this.pos.X -

                this.lastPos.X, Y: this.pos.Y - this.lastPos.Y,
        };

        if (this.setTop) {
            this.element.css("top", this.prev.top + this.delta.Y);
        }
        if (this.setLeft) {
            this.element.css("left", this.prev.left + this.delta.X);
        }
        if (this.setBottom) {
            this.element.css("bottom",
                this.prev.bottom - this.delta.Y);
        }
        if (this.setRight) {
            this.element.css("right"
                , this.prev.right - this.delta.X);
        }

        e.preventDefault();
        e.stopPropagation();
    }

    moveResize = (e: JQueryEventObject) => {
        this.pos = this.getPageXY(e);
        this.delta = {
            X: this.pos.X - this.lastPos.X, Y: this.pos.Y -
                this.lastPos.Y,
        };

        if (this.resizeStates.up) {
            this.element.css("height",
                this.prevSize.height - this.delta.Y);
            if (this.setTop) {
                this.element.css("top", this.prev.top + this.delta.Y);
            }
        }
        if (this.resizeStates.left) {
            this.element.css(
                "width", this.prevSize.width - this.delta.X);
            if (this.setLeft) {
                this.element.css("left", this.prev.left + this.delta.X);
            }
        }
        if (this.resizeStates.down) {
            this.element.css("height", this.prevSize.height + this.delta.Y);
            if (this.setBottom) {
                this.element.css("bottom", this.prev.bottom - this.delta.Y);
            }
        }
        if (this.resizeStates.right) {
            this.element.css("width", this.prevSize.width + this.delta.X);

            if (this.setRight && this.delta.X >= 0) {
                this.element.css(
                    "right", this.prev.right - this.delta.X);
            }
        }

        e.preventDefault();
        e.stopPropagation();

        const size = this.element.css(["width", "height"]);
        if (this.posKey) {
            setStorage(this.posKey + "Size", size);
        }
    }

    $destroy() {
        this.element.remove();
    }

    setModal(modalInstance: IModalInstanceService) {
        this.modal = modalInstance;
    }
}
