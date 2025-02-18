import moment, {Moment} from "moment";
import {mandatoryAndOptional} from "tim/util/utils";
import * as t from "io-ts";
import {ReadonlyMoment} from "tim/util/readonlymoment";
import {IItem} from "../item/IItem";
import {IGenericPluginMarkup, nullable} from "../plugin/attributes";
import {DurationChoice} from "../ui/duration-picker.component";
import {IUser} from "../user/IUser";

export type IExplCollection = Record<string, string>;

export interface IQuestionMarkup extends IAskedJsonJson, IGenericPluginMarkup {}

export interface IQuestionParagraph extends IUniqueParId {
    markup: IQuestionMarkup;
    qst: boolean;
    taskId?: string;
    isPreamble: boolean;
    // TODO: include also other attributes
}

export interface IAskedJsonBase {
    answerFieldType: AnswerFieldType;
    defaultPoints?: number;
    expl?: IExplCollection | null;
    doNotMove?: number[] | number;
    matrixType?: MatrixType; // is useless
    points?: string;
    questionText: string;
    questionTitle: string;
    questionType: QuestionType;
    randomizedRows?: number;
    timeLimit?: number;
    size?: string;
}

export interface IAskedJsonJson extends IUnprocessedHeaders, IAskedJsonBase {}

export type QuestionType =
    | "checkbox-vertical"
    | "matrix"
    | "radio-vertical"
    | "true-false"
    | "textarea"
    | "likert"
    | "";

export type MatrixType =
    | "textArea"
    | "radiobutton-horizontal"
    | "checkbox"
    | "inputText";

export type AnswerFieldType =
    | "radio"
    | "checkbox"
    | "matrix"
    | "text"
    | "inputText"; // TODO matrix seems wrong

export const RowCodec = t.type({
    text: t.string,
    type: t.string,
    id: t.number,
    columns: t.array(t.type({id: t.number})),
});

export const AskedJsonJsonCodec = mandatoryAndOptional(
    {
        headers: t.array(
            t.union([
                t.string,
                t.type({text: t.string, type: t.string, id: t.number}),
            ])
        ),
        rows: t.array(t.union([RowCodec, t.string])),

        answerFieldType: t.keyof({
            radio: null,
            checkbox: null,
            matrix: null,
            text: null,
            inputText: null,
        }),
        questionText: t.string,
        questionTitle: t.string,
        questionType: t.keyof({
            "checkbox-vertical": null,
            matrix: null,
            "radio-vertical": null,
            "true-false": null,
            textarea: null,
            likert: null,
            "": null,
        }),
    },
    {
        defaultPoints: t.number,
        expl: nullable(t.record(t.string, t.string)),
        doNotMove: t.union([t.number, t.array(t.number)]),
        customHeader: t.string,
        matrixType: t.keyof({
            textArea: null,
            "radiobutton-horizontal": null,
            checkbox: null,
            inputText: null,
        }),
        points: t.string,
        randomizedRows: t.number,
        timeLimit: t.number,
        size: t.string,
        autosave: t.boolean,
    }
);

export interface IHeader {
    text: string;
    type: string;
    id: number;
}

export interface IColumn {
    id: number;
}

export interface IRow extends IHeader {
    columns: IColumn[];
}

export interface IUnprocessedHeaders {
    headers: Array<IHeader | string>;
    rows: Array<IRow | string>;
}

export interface IProcessedHeaders {
    headers: IHeader[];
    rows: IRow[];
}

export interface IQuestionUI {
    durationAmount?: number;
    durationType: DurationChoice;
}

export interface IAskedJson {
    hash: string;
    json: IAskedJsonJson;
}

export interface IAskedQuestion {
    asked_id: number;
    lecture_id: number;
    doc_id: number;
    par_id: string;
    asked_time: ReadonlyMoment;
    json: IAskedJson;
}

export interface ILectureMessage {
    msg_id: number;
    user: IUser;
    timestamp: ReadonlyMoment;
    message: string;
}

export type ILectureFormParams = ILecture | IItem;

export interface ILectureOptions {
    max_students: number | null;
    poll_interval: number;
    poll_interval_t: number;
    long_poll: boolean;
    long_poll_t: boolean;
    teacher_poll: string;
}

export interface ILecture<TimeType = ReadonlyMoment> {
    doc_id: number;
    lecture_id: number;
    lecture_code: string;
    start_time: TimeType;
    end_time: TimeType;
    password: string;
    options: ILectureOptions;
    is_full: boolean;
    is_access_code: boolean;
}

export interface IQuestionAnswerPlain {
    answer_id: number;
    user_id: number;
    points: number;
    answer: AnswerTable;
    answered_on: ReadonlyMoment;
    asked_id: number;
}

export interface IQuestionAnswer {
    answer_id: number;
    user: IUser;
    points: number;
    answer: AnswerTable;
    answered_on: Moment;
    asked_question: IAskedQuestion;
}

export interface ILecturePerson {
    user: IUser;
    activeSecondsAgo: number;
}

export function isLectureListResponse(
    response: unknown
): response is ILectureListResponse {
    return (
        (response as ILectureListResponse).lectures != null &&
        (response as ILectureListResponse).futureLectures != null
    );
}

export function isNoUpdatesResponse(
    response: unknown
): response is INoUpdatesResponse {
    return (response as INoUpdatesResponse).ms != null;
}

export interface ILectureListResponse2 {
    currentLectures: ILecture[];
    futureLectures: ILecture[];
    pastLectures: ILecture[];
}

export interface ILectureListResponse {
    isLecturer: boolean;
    lectures: ILecture[];
    futureLectures: ILecture[];
}

export interface ILectureResponse {
    isInLecture: boolean;
    isLecturer: boolean;
    lecture: ILecture;
    students: ILecturePerson[];
    lecturers: ILecturePerson[];
    useQuestions: boolean;
    correctPassword?: boolean;
}

export interface ILectureSettings {
    inLecture: boolean;
    lectureMode: boolean;
    useAnswers: boolean;
    useQuestions: boolean;
    useWall: boolean;
}

export function hasLectureEnded(lecture: ILecture) {
    return lecture.end_time < moment();
}

export interface IUniqueParId {
    parId: string;
    docId: number;
}

export type IUpdateResponse =
    | IGotUpdatesResponse
    | INoUpdatesResponse
    | ILectureListResponse;

export interface IPointsClosed {
    points_closed: true;
}

export interface IAlreadyAnswered {
    already_answered: true;
}

export interface IQuestionAsked {
    type: "question";
    data: IAskedQuestion;
}

export interface IQuestionHasAnswer {
    type: "answer";
    data: IQuestionAnswer;
}

export interface IQuestionResult {
    type: "result";
    data: IQuestionAnswer;
}

export type IExtraResponse = IPointsClosed | IGetNewQuestionResponse;

export type IGetNewQuestionResponse =
    | IAlreadyAnswered
    | IQuestionAsked
    | IQuestionResult
    | IQuestionHasAnswer
    | null;

export interface IGotUpdatesResponse extends INoUpdatesResponse {
    msgs: ILectureMessage[];
    lectureEnding: 1 | 5 | 100;
    lectureId: number;
    lecturers: ILecturePerson[];
    students: ILecturePerson[];
    extra?: IExtraResponse;
}

export interface IEmptyResponse {
    empty: true;
}

export function isEmptyResponse(
    r: ILectureResponse | ILectureListResponse | IEmptyResponse
): r is IEmptyResponse {
    return (r as IEmptyResponse).empty;
}

export interface INoUpdatesResponse {
    ms: number;
    question_end_time?: ReadonlyMoment | null;
}

export function hasUpdates(r: IUpdateResponse): r is IGotUpdatesResponse {
    return (r as IGotUpdatesResponse).msgs != null;
}

export function pointsClosed(r: IExtraResponse): r is IPointsClosed {
    return (r as IPointsClosed).points_closed != null;
}

export function alreadyAnswered(r: IExtraResponse): r is IAlreadyAnswered {
    return (r as IAlreadyAnswered).already_answered != null;
}

export function questionAsked(r: IExtraResponse): r is IQuestionAsked {
    return (r as IQuestionAsked).type === "question";
}

export function questionAnswerReceived(
    r: IExtraResponse
): r is IQuestionResult {
    return (r as IQuestionResult).type === "result";
}

export function questionHasAnswer(r: IExtraResponse): r is IQuestionHasAnswer {
    return (r as IQuestionHasAnswer).type === "answer";
}

export type QuestionOrAnswer = IAskedQuestion | IQuestionAnswer;

export function isAskedQuestion(qa: QuestionOrAnswer): qa is IAskedQuestion {
    return (qa as IAskedQuestion).asked_id != null;
}

export type AnswerTable = string[][];
