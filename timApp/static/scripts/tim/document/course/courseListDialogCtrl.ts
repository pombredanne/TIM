/**
 * Dialog for displaying active courses grouped by their subjects.
 */

import {IRootElementService, IScope} from "angular";
import {ngStorage} from "ngstorage";
import {
    getCourseCode,
    ICourseSettings,
    IItem,
    ISubjectList,
    ITaggedItem,
    tagIsExpired,
    TagType,
} from "../../item/IItem";
import {DialogController, registerDialogComponent, showDialog} from "../../ui/dialog";
import {$http, $localStorage} from "../../util/ngimport";

export interface ICourseListParams {
    item: IItem;
    settings: ICourseSettings;
}

export interface IGroupedCourses {
    subject: string; // TODO: More than one subject.
    closed: boolean;
    docs: ITaggedItem[];
    subsubjects: IGroupedCourses[];
}

/**
 * Tag search dialog's controller.
 */
export class ShowCourseListDialogController extends DialogController<{ params: ICourseListParams }, {}, "timCourseListDialog"> {
    private static $inject = ["$element", "$scope"];
    private docList: ITaggedItem[] = [];
    private subjects: ISubjectList | undefined;
    private grouped: IGroupedCourses[];
    private closedSubjects: boolean[] = [];
    private storage: ngStorage.StorageService & {subjectsStorage: null | boolean[]};
    private toggleCollapseAll: boolean = false;
    private filterText: string = "";

    constructor(protected element: IRootElementService, protected scope: IScope) {
        super(element, scope);
        this.storage = $localStorage.$default({
            subjectsStorage: null,
        });
        this.grouped = [];
        this.toggleCollapseAll = !this.allClosed(this.grouped);
    }

    /**
     * Show tag list when dialog loads and focus on tag-field.
     */
    async $onInit() {
        super.$onInit();
        await this.getDocumentsByTag("", false, true);
        this.subjects = this.resolve.params.settings.course_subjects;
        if (this.storage.subjectsStorage) {
            this.closedSubjects = this.storage.subjectsStorage;
        }
        this.groupBySubject();
        this.loadCollapseStates();
        this.toggleCollapseAll = !this.allClosed(this.grouped);
    }

    $onDestroy() {
        this.saveCollapseStates();
    }

    /**
     * Loads subjects collapse states.
     */
    private loadCollapseStates() {
        if (this.grouped && this.closedSubjects && this.closedSubjects.length === this.grouped.length) {
            for (const {subject, i} of this.grouped.map((subject, i) => ({ subject, i }))) {
                subject.closed = this.closedSubjects[i];
            }
        }
    }

    /**
     * Saves subject collapse states (whether the subject list is closed or not) into local storage.
     */
    private saveCollapseStates() {
        this.closedSubjects = [];
        if (this.grouped) {
            for (const {subject, i} of this.grouped.map((subject, i) => ({ subject, i }))) {
                this.closedSubjects.push(subject.closed);
            }
        }
        this.storage.subjectsStorage = this.closedSubjects;
    }

    /**
     * Dialog title.
     */
    public getTitle() {
        return "Available courses";
    }

    /**
     * Filter documents by tag.
     * @param tagName Tag word to search with.
     * @param exactMatch Search only documents with the whole tag.
     * @param listDocTags Get also tags in each document.
     * If false will also search for partial matches.
     */
    private async getDocumentsByTag(tagName: string, exactMatch: boolean, listDocTags: boolean) {
        const response = await $http<ITaggedItem[]>({
            method: "GET",
            params: {
                exact_search: exactMatch,
                list_doc_tags: listDocTags,
                name: tagName,
            },
            url: "/tags/getDocs",
        });
        this.docList = response.data;
    }

    /**
     * Checks collapse states of all subjects.
     * @param {IGroupedCourses[]} courses List of grouped courses.
     * @returns {boolean} True if all course categories are closed, false if one or more are open.
     */
    private allClosed(courses: IGroupedCourses[]) {
        for (const course of courses) {
            if (!course.closed) {
                return false;
            }
        }
        return true;
    }

    /**
     * Groups courses by their subject tags. Leaves out expired courses, subjects
     * with no non-expired courses and filtered courses, if filter is used.
     */
    private groupBySubject() {
        let close = true;
        if (!this.subjects) {
            return;
        }
        for (const s of this.subjects) {
            const documents = [];
            if (typeof s === "string") {
                for (const d of this.docList) {
                    let isSameSubject = false;
                    let isNonExpiredCourse = false;
                    let passesFilter = false;  // Won't be added unless this is true.
                    if (this.filterText.length === 0 ||
                        d.title.toLowerCase().indexOf(this.filterText.toLowerCase()) > -1) {
                        passesFilter = true;
                    }
                    for (const tag of d.tags) {
                        if (tag.type === TagType.Subject && tag.name === s) {
                            isSameSubject = true;
                        }
                        if (tag.type === TagType.CourseCode && !tagIsExpired(tag)) {
                            if (tag.name.toLowerCase().indexOf(this.filterText.toLowerCase()) > -1) {
                                passesFilter = true;
                            }
                            isNonExpiredCourse = true;
                        }
                    }
                    if (isSameSubject && isNonExpiredCourse && passesFilter) {
                        documents.push(d);
                    }
                }
                // If a subject has no non-expired course documents in it, don't display it.
                if (documents.length > 0) {
                    this.grouped.push({subject: s, closed: close, docs: documents, subsubjects: []});
                    close = true;
                }
            } else {
                // TODO: Subsubjects.
            }
        }
    }

    /**
     * Gets course code of an unexpired course.
     * @param {ITaggedItem} d Document with tags.
     * @returns {string} Coursecode or undefined, if non-existent or expired.
     */
    private courseCode(d: ITaggedItem) {
        return getCourseCode(d.tags, true);
    }

    /**
     * Collapse or open all subjects.
     */
    private toggleAll() {
        for (const item of this.grouped) {
            item.closed = this.toggleCollapseAll;
        }
        this.toggleCollapseAll = !this.toggleCollapseAll;
    }

    /**
     * Update course list according to filter word.
     */
    private refresh() {
        this.grouped = [];
        this.groupBySubject();
        this.toggleCollapseAll = false;
        this.toggleAll();
    }

    /**
     * Filter when Enter is pressed.
     * @param event Keyboard event.
     */
    private async keyPressed(event: KeyboardEvent) {
        if (event.which === 13) {
            this.refresh();
        }
    }
}

registerDialogComponent("timCourseListDialog",
    ShowCourseListDialogController,
    {
        template:
            `<tim-dialog>
    <dialog-header>
    </dialog-header>
    <dialog-body>
    <h5>Listing available courses <a><i ng-if="$ctrl.toggleCollapseAll" ng-click="$ctrl.toggleAll()"
    title="Collapse all subjects" class="glyphicon glyphicon-minus-sign"></i>
    <i ng-if="!$ctrl.toggleCollapseAll" ng-click="$ctrl.toggleAll()" title="Open all subjects"
    class="glyphicon glyphicon-plus-sign"></i></a></h5>
    <div class="col-xs-8">
        <p>
            <span>
                <span ng-if="$ctrl.allClosed($ctrl.grouped)">
                    Press the plus signs to view available courses on different subjects
                </span>
            </span>
        </p>
    </div>
    <div class="input-group float-right col-xs-4">
        <input class="float-right form-control" ng-if="true" ng-model="$ctrl.filterText" placeholder="Input filter word"
        title="Filter by course code and title" ng-keypress="$ctrl.keyPressed($event)">
        <span class="input-group-addon btn" ng-click="$ctrl.refresh()" title="Filter courses">
        <i class="glyphicon glyphicon-search"></i></span>
    </div>
    <br>
    <div>
        <ul class="list-unstyled" ng-if="$ctrl.grouped.length > 0" id="courses" aria-multiselectable="true">
            <li ng-repeat="subject in $ctrl.grouped" ng-if="subject.docs.length > 0">
                <span class="cursor-pointer" ng-click="subject.closed = !subject.closed"
                data-toggle="collapse" data-parent="#courses" href="#{{subject.subject}}" aria-expanded="false"
                aria-controls="{{subject.subject}}">
                    <a><i class="glyphicon" ng-class="subject.closed ? 'glyphicon-plus' : 'glyphicon-minus'"></i></a>
                    {{subject.subject}} ({{subject.docs.length}} <ng-pluralize count="subject.docs.length"
                    when="{'1': 'course', 'other': 'courses'}"></ng-pluralize>)
                </span>
                <ul class="list-unstyled well well-sm" uib-collapse="subject.closed">
                    <li ng-repeat="course in subject.docs | orderBy:$ctrl.courseCode"
                    ng-if="$ctrl.courseCode(course)">
                        <a href="/view/{{course.path}}" title="Open {{course.title}}">
                        <span class="btn-xs btn-primary">{{$ctrl.courseCode(course)}}</span>
                         {{course.title}}
                        </a>
                    </li>
                </ul>
            </li>
        </ul>
    <span ng-if="$ctrl.grouped.length == 0">No documents found!</span>
    </div>
    </dialog-body>
    <dialog-footer>
        <button class="timButton" ng-click="$ctrl.dismiss()">Close</button>
    </dialog-footer>
</tim-dialog>
`,
    });

export async function showCourseListDialog(d: ICourseListParams) {
    return await showDialog<ShowCourseListDialogController>("timCourseListDialog", {params: () => d}).result;
}
