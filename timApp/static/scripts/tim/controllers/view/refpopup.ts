import $ from "jquery";
import * as refPopup from "tim/directives/refPopup";
import {markAsUsed} from "tim/utils";
import {$compile} from "../../ngimport";
import {onMouseOut, onMouseOver} from "./eventhandlers";

markAsUsed(refPopup);

export function defineRefPopup(sc) {
    "use strict";

    onMouseOver(".parlink", function($this, e) {
        sc.over_reflink = true;

        const $par = $this.parents(".par").find(".parContent");
        const coords = {left: e.pageX - $par.offset().left + 10, top: e.pageY - $par.offset().top + 10};
        let params;

        try {
            params = {
                docid: $this[0].attributes["data-docid"].value,
                parid: $this[0].attributes["data-parid"].value,
            };
        } catch (TypeError) {
            // The element was modified
            return;
        }

        sc.showRefPopup(e, $this, coords, params);
    });

    onMouseOver(".ref-popup", function($this, e) {
        sc.over_popup = true;
    });

    onMouseOut(".ref-popup", function($this, e) {
        sc.over_popup = false;
        sc.hideRefPopup();
    });

    onMouseOut(".parlink", function($this, e) {
        sc.over_reflink = false;
        sc.hideRefPopup();
    });

    sc.showRefPopup = function(e, $ref, coords, attrs) {
        const $popup = $("<ref-popup>");
        $popup.offset(coords);

        for (const attr in attrs) {
            if (attrs.hasOwnProperty(attr)) {
                $popup.attr(attr, attrs[attr]);
            }
        }

        $ref.parent().prepend($popup); // need to prepend to DOM before compiling
        $compile($popup[0])(sc);
        return $popup;
    };

    sc.hideRefPopup = function() {
        if (sc.over_reflink || sc.over_popup) {
            return;
        }

        $(".refPopup").remove();
    };
}
