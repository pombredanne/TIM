/**
 * Defines the client-side implementation of JavaScript runner plugin.
 */
import angular from "angular";
import * as t from "io-ts";
import {PluginBase, pluginBindings} from "tim/plugin/util";
import {timApp} from "../app";
import {GenericPluginMarkup, Info, nullable, withDefault} from "./attributes";

const importDataApp = angular.module("importDataApp", ["ngSanitize"]);
export const moduleDefs = [importDataApp];

// this.attrs
const TimMenuMarkup = t.intersection([
    t.partial({
        // menu: nullable(t.array(t.string)),
        menu: nullable(t.string),
    }),
    GenericPluginMarkup,
    t.type({
        hoverOpen: withDefault(t.boolean, true),
        topMenu: withDefault(t.boolean, false),
        separator: withDefault(t.string, "&nbsp;"), // Non-breaking space
        openingSymbol: withDefault(t.string, "&#9662;"), // Caret
    }),
]);
const TimMenuAll = t.intersection([
    t.partial({
        // menu: t.array(t.string),
        menu: t.string,
    }),
    t.type({
        info: Info,
        markup: TimMenuMarkup,
        preview: t.boolean,
    }),
]);

/*
interface IMenuItem {
    items: IMenuItem[] | undefined;
    open: false; // Whether the list of items is shown.
    text: string;
}*/

interface IMenuItem {
    items: IMenuItem[] | undefined;
    text: string;
    level: number;
    open: boolean;
}

class TimMenuController extends PluginBase<t.TypeOf<typeof TimMenuMarkup>, t.TypeOf<typeof TimMenuAll>, typeof TimMenuAll> {
    private menu: any; // IMenuItem[] = [];
    private openingSymbol: string = "";
    private hoverOpen: boolean = true;
    private separator: string = "";
    private topMenu: boolean = false;
    private topBarY = 117;
    private menuId: string = String.fromCharCode(65 + Math.floor(Math.random() * 26)) + Date.now();

    getDefaultMarkup() {
        return {};
    }

    buttonText() {
        return super.buttonText() || "TimMenu";
    }

    $onInit() {
        super.$onInit();
        this.formMenu();
        this.hoverOpen = this.attrs.hoverOpen;
        this.separator = this.attrs.separator;
        this.topMenu = this.attrs.topMenu;
        this.openingSymbol = this.attrs.openingSymbol;
        if (this.topMenu) {
            window.onscroll = () => this.toggleSticky();
        }
    }

    /**
     * Turn string-list into leveled menuitem-list.
     */
    formMenu() {
        if (!this.attrs.menu) {
            return;
        }
        // TODO: Get rid of eval.
        const evaluedMenu = eval(this.attrs.menu);
        this.menu = evaluedMenu;
    }

    protected getAttributeType() {
        return TimMenuAll;
    }

    isPlainText() {
        return (window.location.pathname.startsWith("/view/"));
    }

    /**
     * Close other menus and toggle clicked menu open or closed.
     * @param item
     * @param parent
     */
    toggleSubmenu(item: any, parent: IMenuItem) {
        const wasOpen = item.open;
        if (parent.items) {
            for (const i of parent.items) {
                i.open = false;
            }
        }
        if (!wasOpen) {
            item.open = !item.open;
        }
    }

    /**
     * Makes the element follow when scrolling for one screen height after top bar.
     */
    toggleSticky() {
        // console.log($(window).scrollTop() + " " + $(window).height());
        if ($(window).scrollTop() >= this.topBarY && $(window).scrollTop() < ($(window).height() + this.topBarY)) {
            // return "tim-menu top-menu";
            document.getElementById(this.menuId).classList.add("top-menu");
        } else {
            // return "tim-menu";
            document.getElementById(this.menuId).classList.remove("top-menu");
        }
    }
}

timApp.component("timmenuRunner", {
    bindings: pluginBindings,
    controller: TimMenuController,
    require: {
        vctrl: "^timView",
    },
    template: `
<tim-markup-error ng-if="::$ctrl.markupError" data="::$ctrl.markupError"></tim-markup-error>
<div id="{{$ctrl.menuId}}" ng-class="tim-menu">
    <span ng-repeat="m in $ctrl.menu">
        <div ng-if="m.items.length > 0" class="btn-group" uib-dropdown is-open="status.isopen" id="simple-dropdown" style="cursor: pointer;">
          <span uib-dropdown-toggle ng-disabled="disabled" ng-bind-html="m.text+$ctrl.openingSymbol"></span>
          <ul class="dropdown-menu" uib-dropdown-menu aria-labelledby="simple-dropdown">
            <li class="tim-menu-item" ng-repeat="item in m.items" role="menuitem">
                <span class="tim-menu-item" ng-if="item.items.length > 0">
                    <span ng-bind-html="item.text+$ctrl.openingSymbol" ng-click="$ctrl.toggleSubmenu(item, m)"></span>
                    <ul class="tim-menu-submenu" ng-if="item.open">
                        <li class="tim-menu-item" ng-repeat="submenuitem in item.items" ng-bind-html="submenuitem.text"></li>
                    </ul>
                </span ng-if="item.items.length > 0">
                <span class="tim-menu-item" ng-if="item.items.length < 1" ng-bind-html="item.text"></span>
            </li>
          </ul>
        </div>
        <div ng-if="m.items.length < 1" class="btn-group" style="cursor: pointer;" ng-bind-html="m.text"></div>
        <span ng-if="!$last" ng-bind-html="$ctrl.separator"></span>
    </span>
</div>
`,
});
