class Tools {

    constructor(data, currDoc, markup) {
        this.data = data;
        this.currDoc = currDoc;
        this.markup = markup;
        this.result = {};
        this.regex = /^[0-9]+\./;
        this.printP = "";
        this.error = "";
    }

    normalizeField(fieldName) {
        if (this.regex.test(fieldName)) {
            return fieldName;
        } else {
            return this.currDoc + fieldName;
        }
    }

    getStudentName() {
        return this.data.user.real_name;
    }

    getDouble(fieldName, def = 0) {
        let fn = this.normalizeField(fieldName);
        let s = this.data.fields[fn];
        let r = parseFloat(s);
        if (isNaN(r)) r = def;
        return r;
    }

    getInt(fieldName, def = 0) {
        let fn = this.normalizeField(fieldName);
        let s = this.data.fields[fn];
        let r = parseInt(s);
        if (isNaN(r)) r = def;
        return r;
    }

    getString(fieldName, def = "") {
        let fn = this.normalizeField(fieldName);
        let r = this.data.fields[fn];
        if (r === null) r = def;
        return r;
    }

    getValue(fieldName, def = "") {
        let fn = this.normalizeField(fieldName);
        let r = this.data.fields[fn];
        if (r === null) r = def;
        return r;
    }

    /*
    getSum() {
        let sum = 0;
        for (let i = 0; i < arguments.length; i++) {
            sum += arguments[i];
        }
        return sum;
    }
    */

    getSum(fieldName, start, end, def = 0) {
        let fn = this.normalizeField(fieldName);
        let sum = 0;
        for (let i = start; i <= end; i++) {
            let fnn = fn + i.toString();
            let s = this.data.fields[fnn];
            let r = parseFloat(s);
            if (isNaN(r)) r = def;
            sum += r;
        }
        return sum;
    }

    setString(fieldName, content) {
        let fn = this.normalizeField(fieldName);
        this.result[fn] = content;
    }

    setInt(fieldName, content) {
        let fn = this.normalizeField(fieldName);
        let r = parseInt(content);
        // TODO: if (isNaN(r)) error
        this.result[fn] = r;
    }

    setDouble(fieldName, content) {
        let fn = this.normalizeField(fieldName);
        let r = parseFloat(content);
        // TODO: if (isNaN(r)) error
        this.result[fn] = r;
    }

    getDefaultPoints(def = this.markup.defaultPoints) {
        // TODO: error if default not set
        if (!this.markup.defaultPoints) this.error = "Default points have not been set";
        return def;
    }

    getGrade(points) {
        const scale = this.markup.gradingScale; // TODO: error if gardingScale not set
        const values = Object.values(scale);
        values.sort(function (a, b) {
            return b - a
        });
        let grade = "";
        for (let i = 0; i < values.length; i++) {
            if (points >= values[i]) {
                grade = Object.keys(scale).find(key => scale[key] === values[i]);
                break;
            }
            grade = this.markup.failGrade || "";
        }
        return grade;
    }

    //TODO: fix
    saveGrade(gradeVal, points) {
        let d = this.markup.gradeField || "grade";
        let fn = this.normalizeField(d);
        this.result[fn] = gradeVal;
        if (arguments.length === 2) { // TODO: ?
            let c = this.markup.creditField || "credit";
            let fnc = this.normalizeField(c);
            this.result[fnc] = points;
        }

    }

    print() {
        for (let i = 0; i < arguments.length; i++) {
            let a = arguments[i].toString();
            this.printP += a + " "; // TODO: millä merkillä halutaan erotella

        }
        this.printP += "\n";
    }

    getResult() {
        return {'user': this.data.user.id, 'fields': this.result};
    }

    getPrint() {
        return this.printP;
    }

    getError() {
        return this.error;
    }
}

module.exports = Tools;
