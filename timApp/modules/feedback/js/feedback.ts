/**
 * Defines the client-side implementation of a feedback-plugin.
 */
import angular, {INgModelOptions} from "angular";
import * as t from "io-ts";
import {ITimComponent, ViewCtrl} from "tim/document/viewctrl";
import {GenericPluginMarkup, nullable, PluginBase, withDefault} from "tim/plugin/util";
import {$http} from "tim/util/ngimport";
import {to} from "tim/util/utils";

const feedbackApp = angular.module("feedbackApp", ["ngSanitize"]);
export const moduleDefs = [feedbackApp];

const MatchElement = t.type({
    index: t.Integer,
    answer: t.string,
})

const Choice = t.type({
    match: t.union ([t.array(t.string),t.array(MatchElement)]),
    levels:t.array(t.string)
});


const QuestionItem = t.type({
    pluginNames: t.array(t.string),
    dropdownWords: t.array(t.array(t.string)),
    dragWords: t.array(t.string),
    correctAnswer: t.array(t.string),
    correctAnswerFeedback: t.string,
    choices: t.array(Choice),
});



const FeedbackMarkup = t.intersection([
    t.partial({
        inputstem: t.string,
        followid: t.string,
        field: t.string,
        feedbackLevel: t.number,
        toNextTaskRule: t.string,
        questionItems: t.array(QuestionItem),

        instructionID: t.string,
        sampleItemID: t.string,
        nextTask: t.string,
        pluginID: t.string,
        words: t.string,
        correctAnswer: t.string,
        correctAnswerFeedback: t.string,
        userword: t.string
    }),
    GenericPluginMarkup,
    t.type({
        // all withDefaults should come here; NOT in t.partial
        autoupdate: withDefault(t.number, 500),
        cols: withDefault(t.number, 20),
        //questionItems: t.array(QuestionItem),
    }),
]);
const FeedbackAll = t.intersection([
    t.partial({
        userword: t.string,
    }),
    t.type({markup: FeedbackMarkup}),
]);
/*
class Choice{
    private choice?: string;
    private feedback?: string[];


}

class QuestionItem extends Choice{
    private pluginID?: string;  //tarkasta
    private words?: string[];
    private correctAnswer?: string;
    private correctAnswerFeedback?: string;
    private choise?: Choice;    // miksi herjaa jos choice





}


class Feedback extends QuestionItem{
    private nextTaskRule?: string;
    private nextTask?: string;
    private instructionID?: string;
    private feedbackLevel?: number;
    //private feedbackLevelRise?: boolean;
    private QuestionItems?: QuestionItem[];
    //private answerList?: string[];
    private answer?: string;
    private questionPluginID?: string;  // tarkasta
    private currentFeedbackLevel?: number;
    private listOfValidQuestionItems?: string[];

}



*/

class FeedbackController extends PluginBase<t.TypeOf<typeof FeedbackMarkup>, t.TypeOf<typeof FeedbackAll>, typeof FeedbackAll> implements ITimComponent {
    private result?: string;
    private error?: string;
    private vctrl!: ViewCtrl;
    private userword = "";



    private answer = ["is", "today"];
    private questionPluginID?: string;  // tarkasta
    private currentFeedbackLevel = 0;
    private listOfValidQuestionItems?: string[];



    /*
    private feedback = {
            feedbackLevel: 5,
            feedbackLevelRise: false,
            toNextTaskRule:"",
            questionItems: [{
                pluginNames: ["x", "y"],
                dropdownWords: [["is", "do", "are"], ["yesterday", "today"]],
                dragwords:["what", "does", "the", "fox", "say?"],
                correctAnswer: ["is", "today"],
                correctAnswerFeedback: "vastasit [answer] vastaus on oikein",
                choices:[{
                    match:[
                        {
                            index: 0,
                            answer: "do",
                        },
                        {
                            index: 2,
                            answer: "do",
                        }
                    ],
                    fblevels: [
                        "vastasit [answer]. vastaus on hiukan väärin",
                        "vastasit [answer]. vastaus on hiukan väärin, mieti vielä"
                    ]
                }]
            }]
        };


    setFeedback(){

        let fb={
            feedbackLevel: 5,
            feedbackLevelRise: false,
            toNextTaskRule:"",
            questionItems: [{
                pluginNames: ["x", "y"],
                dropdownWords: [["is", "do", "are"], ["yesterday", "today"]],
                dragwords:["what", "does", "the", "fox", "say?"],
                correctAnswer: ["is", "today"],
                correctAnswerFeedback: "vastasit [answer] vastaus on oikein",
                choices:[{
                    match:[
                        {
                            index: 0,
                            answer: "do",
                        },
                        {
                            index: 2,
                            answer: "do",
                        }
                    ],
                    fblevels: [
                        "vastasit [answer]. vastaus on hiukan väärin",
                        "vastasit [answer]. vastaus on hiukan väärin, mieti vielä"
                    ]
                }]
            }]
        }
        this.feedback = fb;
    }



    handleAnswer(answer: string[], pluginNames: string[]){                              //vai lohko parametrinä
        for(let i = 0; i< this.feedback.questionItems.length; i++){
            if(this.feedback.questionItems[i].pluginNames === pluginNames){             //
                for(let j = 0; j< this.feedback.questionItems[i].correctAnswer.length; j++){
                    if(this.feedback.questionItems[i].correctAnswer[j] !== answer[j]){
                        if(this.currentFeedbackLevel < this.feedback.feedbackLevel) this.currentFeedbackLevel++;
                        //this.compareChoices(this.feedback.questionItems[i].choices, answer, pluginNames)
                        for (let k = 0; k<this.feedback.questionItems[i].choices.length; k++){
                            if(this.feedback.questionItems[i].choices[k])
                        }



                    }
                    else{
                        if(this.feedback.feedbackLevelRise){
                            if(this.currentFeedbackLevel > 0) this.currentFeedbackLevel--
                        }
                        this.hideBlock();
                        this.printFeedback();
                        this.openBlock();
                    }
                }
            }
        }

    }

    compareChoices(choices: object[], answer:string[], pluginNames:string[]){
        for(let i =0; i<choices.length; i++){
            for(let j = 0; j<choices[i].match.length; j++){
                if(choices[i].match[j] !== answer[j]) break;
                if(j === choices[i].match.length-1)
            }
        }
    }

    hideBlock(){
        return;
    }

    printFeedback(){
        return;
    }

    openBlock(){
        return;
    }


*/
    getDefaultMarkup() {
        return {};
    }

    buttonText() {
        return "OK";
    }

    $onInit() {
        super.$onInit();
        this.attrs.questionItems[0].choices
        this.addToCtrl();
    }



    /**
     * Adds this plugin to ViewCtrl so other plugins can get information about the plugin though it.
     */
    addToCtrl() {
        this.vctrl.addTimComponent(this);
    }

    get autoupdate(): number {
        return this.attrs.autoupdate;
    }

    async doSave(nosave: boolean) {
        this.error = "... saving ...";

        this.result = undefined;
        const params = {
            input: {
                nosave: false,
            },
        };

        if (nosave) {
            params.input.nosave = true;
        }
        const url = this.pluginMeta.getAnswerUrl();
        const r = await to($http.put<{web: {result: string, error?: string}}>(url, params));
        if (r.ok) {
            const data = r.result.data;
            this.error = data.web.error;
            this.result = data.web.result;
        } else {
            this.error = "Infinite loop or some other error?";
        }
    }

    /**
     * Returns the content inside this plugin
     * @returns {string} The content inside this plugin
     */
    getContent(): string {
      return "";
    }

    /**
     * Does nothing at the moment
     */
    save(): string {
        this.doSave(false);
        return "";
    }

    /**
     * Gets the user's answer from the plugin this feedback-plugin is assigned to.
     * Doesn't work for paragraphs with multiple plugins at the moment.
     */
    getAnswer() {
        const timComponent = this.vctrl.getTimComponentByName(this.attrs.field || "");
        if(timComponent) {
            const par = timComponent.getPar();
            const content = par.children(".parContent");
            const nodes = content[0].childNodes;
            // console.log(nodes);
            let answer = "";
            for (let n in nodes) {
                let node = nodes[n];
                if(node.nodeName == "#text") {
                    let text = node.textContent || "";
                    text.trim();
                    answer = answer + text;
                }
                if(node.nodeName == "TIM-PLUGIN-LOADER") {
                    // ei toimi usean lohkon sisäisen inline pluginin kanssa
                    answer = answer + timComponent.getContent();
                }
            }
            this.userword = answer;
        }
    }



    protected getAttributeType() {
        return FeedbackAll;
    }

    getGroups():string[] {
        return [""];
    }
    getName(): (string | undefined) {
        if (this.attrs.followid) { return this.attrs.followid; }
        const taskId = this.pluginMeta.getTaskId();
        if (taskId) { return taskId.split(".")[1]; }
    }

    belongsToGroup(group: string): boolean {
        return false;
    }
}

feedbackApp.component("feedbackRunner", {
    bindings: {
        json: "@",
    },
    controller: FeedbackController,
    require: {
        vctrl: "^timView",
    },
    template: `
<div class="csRunDiv no-popup-menu">
    <tim-markup-error ng-if="::$ctrl.markupError" data="::$ctrl.markupError"></tim-markup-error>
    <h4 ng-if="::$ctrl.header" ng-bind-html="::$ctrl.header"></h4>
    <p ng-if="::$ctrl.stem">{{::$ctrl.stem}}</p>
    <div class="form-inline"><label>{{::$ctrl.inputstem}} <span>
        {{$ctrl.userword}}</span></label>
    </div>
    <button class="timButton"
            ng-if="::$ctrl.buttonText()"
            ng-click="$ctrl.getAnswer()">
        {{::$ctrl.buttonText()}}
    </button>
    <div ng-if="$ctrl.error" ng-bind-html="$ctrl.error"></div>
    <pre ng-if="$ctrl.result">{{$ctrl.result}}</pre>
    <p ng-if="::$ctrl.footer" ng-bind="::$ctrl.footer" class="plgfooter"></p>
</div>
`,
});

/*

<div class="csRunDiv no-popup-menu">
    <h4 ng-if="::$ctrl.header" ng-bind-html="::$ctrl.header"></h4>
    <p ng-if="::$ctrl.stem">{{::$ctrl.stem}}</p>
    <div class="form-inline"><label>{{::$ctrl.inputstem}} <span>
        {{$ctrl.userword}}</span></label>
    </div>
    <button class="timButton"
            ng-if="::$ctrl.buttonText()"
            ng-click="$ctrl.getAnswer()">
        {{::$ctrl.buttonText()}}
    </button>
    <div ng-if="$ctrl.error" ng-bind-html="$ctrl.error"></div>
    <pre ng-if="$ctrl.result">{{$ctrl.result}}</pre>
    <p ng-if="::$ctrl.footer" ng-bind="::$ctrl.footer" class="plgfooter"></p>
</div>
 */