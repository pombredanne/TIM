// noinspection DuplicatedCode

// For Lexer see: https://github.com/aaditmshah/lexer
class Lexer {
    deferror(chr) {
        throw new Error("Unexpected character at index " + (this.index - 1) + ": " + chr);
    };


    constructor(defunct) {
        this.defunc = defunct;
        if (typeof defunct !== "function") this.defunct = this.deferror;

        try {
            Lexer.engineHasStickySupport = typeof /(.)/.sticky == 'boolean';
        } catch (ignored) {
            Lexer.engineHasStickySupport = false;
        }
        try {
            Lexer.engineHasUnicodeSupport = typeof /(.)/.unicode == 'boolean';
        } catch (ignored) {
            Lexer.engineHasUnicodeSupport = false;
        }

        this.tokens = [];
        this.rules = [];
        this.setInput("")
    }

    addRule(pattern, action, start) {
        let global = pattern.global;

        if (!global || Lexer.engineHasStickySupport && !pattern.sticky) {
            let flags = Lexer.engineHasStickySupport ? "gy" : "g";
            if (pattern.multiline) flags += "m";
            if (pattern.ignoreCase) flags += "i";
            if (Lexer.engineHasUnicodeSupport && pattern.unicode) flags += "u";
            pattern = new RegExp(pattern.source, flags);
        }

        if (Object.prototype.toString.call(start) !== "[object Array]") start = [0];

        this.rules.push({
            pattern: pattern,
            global: global,
            action: action,
            start: start
        });

        return this;
    }

    setInput(input) {
        this.remove = 0;
        this.state = 0;
        this.index = 0;
        this.tokens.length = 0;
        this.input = input;
        return this;
    }

    lex() {
        let token;
        if (this.tokens.length) return this.tokens.shift();

        this.reject = true;

        while (this.index <= this.input.length) {
            let matches = this.scan().splice(this.remove);
            let index = this.index;

            while (matches.length) {
                if (!this.reject) break;
                let match = matches.shift();
                let result = match.result;
                let length = match.length;
                this.index += length;
                this.reject = false;
                this.remove++;

                token = match.action.apply(this, result);
                if (this.reject) this.index = result.index;
                else if (typeof token !== "undefined") {
                    // noinspection FallThroughInSwitchStatementJS
                    switch (Object.prototype.toString.call(token)) {
                        case "[object Array]":
                            this.tokens = token.slice(1);
                            token = token[0];
                        default:
                            if (length) this.remove = 0;
                            return token;
                    }
                }
            }

            let input = this.input;

            if (index < input.length) {
                if (this.reject) {
                    this.remove = 0;
                    token = this.defunct.call(this, input.charAt(this.index++));
                    if (typeof token !== "undefined") {
                        if (Object.prototype.toString.call(token) === "[object Array]") {
                            this.tokens = token.slice(1);
                            return token[0];
                        } else return token;
                    }
                } else {
                    if (this.index !== index) this.remove = 0;
                    this.reject = true;
                }
            } else if (matches.length)
                this.reject = true;
            else break;
        }
    }

    scan() {
        let matches = [];
        let index = 0;

        let state = this.state;
        let lastIndex = this.index;
        let input = this.input;

        for (let i = 0; i < this.rules.length; i++) {
            let rule = this.rules[i];
            let start = rule.start;
            let states = start.length;

            if ((!states || start.indexOf(state) >= 0) ||
                (state % 2 && states === 1 && !start[0])) {
                let pattern = rule.pattern;
                pattern.lastIndex = lastIndex;
                let result = pattern.exec(input);

                if (!result || result.index !== lastIndex) continue;

                let j = matches.push({
                    result: result,
                    action: rule.action,
                    length: result[0].length
                });

                if (rule.global) index = j;

                while (--j > index) {
                    let k = j - 1;

                    if (matches[j].length > matches[k].length) {
                        let temple = matches[j];
                        matches[j] = matches[k];
                        matches[k] = temple;
                    }
                }
            }
        }

        return matches;
    }
}

// Dijkstra's shunting yard algorithm
// Parser see: https://gist.github.com/aaditmshah/6683499
class Parser {

    constructor() { }

    parse(input) {
        let output = [];
        let stack = [];
        let index = 0;

        while (index < input.length) {
            let token = input[index++];

            switch (token.name()) {
                case "(":
                    stack.unshift(token);
                    break;
                case ")":
                    while (stack.length) {
                        token = stack.shift();
                        if (token.name() === "(") break;
                        output.push(token);
                    }

                    if (token.name() !== "(")
                        throw new Error("Missing (.");
                    break;
                default:
                    if (token.type() === undefined) {
                        output.push(token);
                        break;
                    }
                    while (stack.length) {
                        let punctuator = stack[0].name();
                        if (punctuator === "(") break;
                        let operator = token.type();
                        let precedence = operator.precedence;
                        let antecedence = stack[0].type().precedence;

                        if (precedence > antecedence ||
                            precedence === antecedence &&
                            operator.associativity === "right") break;
                        output.push(stack.shift());
                    }

                    stack.unshift(token);
            }
        }

        while (stack.length) {
            let token = stack.shift();
            if (token.name() !== "(") output.push(token);
            else throw new Error("Missing ).");
        }

        return output;
    }
}

function roundToNearest(num, decimals) {
  decimals = decimals || 0;
  let p = Math.pow(10, decimals);
  let p2 = p;
  while (Math.abs(num) > 10) {
      p2 /= 10;
      num /= 10;
  }
  let n = (num * p) * (1 + Number.EPSILON);
  return Math.round(n) / p2;
}

class CalculatorOp {

    static factor = {
        precedence: 2,
        associativity: "left"
    };

    static term = {
        precedence: 1,
        associativity: "left"
    };

    static func = {
        precedence: 1,
        associativity: "right"
    };

    constructor(calculator) {
        this.calculator = calculator;
    }

    type() {   }
    op() { return "";  }  // regexp to match thos opertation
    params() { return "";} // regexp options for this match

    pop() {
        if (this.calculator.stack.length === 0)
            return this.calculator.lastResult;
        return this.calculator.stack.pop();
    }

    push(v) { this.calculator.stack.push(this.r(v)); }
    name() { return this.op(); } // needed if name is different from op
    output(extraBefore) { return ` ${this.name()} `;  }
    extraSpaceAfter() { return ""; } // need space before some operation
    mapValue() { return this.name(); }
    doCalc() {  }
    calc() { this.doCalc(); }
    r(v) { return roundToNearest(v, this.calculator.params.decimals);  }
    lexfunc(lexme) { return this;  }
    allowSignRight() { return true; }
    checkSign(lastToken) { return this; } // deny 2-3 as a sign

    getnum(s) {
        if (s === undefined) return this.calculator.lastResult;
        s = (""+s).trim();
        if (s === "") return this.calculator.lastResult;
        if (s.startsWith("p")) {
            if (s==="p") return this.calculator.lastResult;
            let idx = this.calculator.row - parseInt(s.substring(1));
            idx = Math.max(0, Math.min(idx, this.calculator.row-1));
            return this.calculator.mem["r"+idx] || 0;
        }
        if (s[0].match(/[a-z]/)) {
            let val = this.calculator.mem[s];
            if (val === undefined) throw new Error(`Unknown variable '${s}'`);
            return val;
        }
        return parseFloat(s.replace(",", "."));
    }
}

// See https://regex101.com/r/e5iqja/latest
const num = "((?:(?:[-+][0-9]+)|(?:[0-9]*))(?:[.,][0-9]*)?(?:[eE]-?[0-9]+)?|-?pi|-?π|[a-z][a-z0-9]*)";

class Command extends  CalculatorOp {
}

class FuncRROperation extends  CalculatorOp {
    type() { return CalculatorOp.func; }
    doCalc(a) { return 0; }
    output(extraBefore) { return extraBefore + this.name(); }
    extraSpaceAfter() { return " "; }

    calc() {
        let a = this.pop();
        this.push(this.doCalc(a));
    }
}

class BracketOperation extends  CalculatorOp {
    output(extraBefore) { return this.name(); }
}

class LeftBracketOperation extends  BracketOperation {
    op() { return "[(]";}
    name() { return "("; }
    extraSpaceAfter() { return ""; }
}

class RightBracketOperation extends  BracketOperation {
    op() { return "[)]";}
    name() { return ")"; }
    allowSignRight() { return false; }
}

class ValueOperation extends  CalculatorOp {
    constructor(calculator) {
        super(calculator);
        this.value = "";
    }
    name() { return ""+this.value; }
    output(extraBefore) { return extraBefore + this.name(); }
    calc() { this.push(this.value);}
    allowSignRight() { return false; }
}

class NumOperation extends  ValueOperation {
    op() {
        // return "((?:(?:[-][0-9]+)|(?:[0-9]*))(?:[.,][0-9]*)?(?:[eE]-?[0-9]+)?)"
        return "([0-9]+(?:[.,][0-9]*)?(?:[eE]-?[0-9]+)?)";
    }
    lexfunc(lexme) {
        const oper = new NumOperation(this.calculator);
        oper.value = parseFloat(lexme.replace(",", "."))
        return oper;
    }
}

class PiOperation extends  ValueOperation {
    op() { return "pi|π" }
    lexfunc(lexme) {
        const oper = new PiOperation(this.calculator);
        oper.value = Math.PI;
        return oper;
    }
}

class MemOperation extends  ValueOperation {
    op() { return "[a-z][a-z0-9]*" }
    lexfunc(lexme) {
        const oper = new MemOperation(this.calculator);
        oper.value = this.getnum(lexme)
        return oper;
    }
}

class BinOperation extends  CalculatorOp {
    type() { return CalculatorOp.term; }
    doCalc(a,b) { return 0; }
    calc() {
        let b = this.pop();
        let a = this.pop();
        this.push(this.doCalc(a,b));
    }
}

class Deg extends Command {
    op() { return "deg"; }
    calc() { this.calculator.deg = true; }
}

class Rad extends Command {
    op() { return "rad"; }
    calc() { this.calculator.deg = false; }
}

class SignOperation extends FuncRROperation{
    type() { return CalculatorOp.func; }
    extraSpaceAfter() { return ""; }
    output(extraBefore) { return extraBefore + this.name().trim(); }
}

class SignMinus extends SignOperation {
    op() { return " *-"; }
    name() { return " -"; }
    calc() {
        let a = this.pop();
        this.push(-a);
    }
    checkSign(lastToken) {
        if (lastToken.allowSignRight()) return this;
        return new Minus(this.calculator);
    }
}

class SignPlus extends SignOperation {
    op() { return " *\\+"; }
    name() { return " +"; }
    calc() {  }
    checkSign(lastToken) {
        if (lastToken.allowSignRight()) return this;
        return new Plus(this.calculator);
    }
}

class Plus extends BinOperation {
    op() { return " *\\+ "; }
    name() { return "+"; }
    doCalc(a, b) { return a + b; }
}

class Minus extends BinOperation {
    op() { return " *- "; }
    // params() { return "g";}
    name() { return "-"; }
    doCalc(a, b) { return a - b; }
}

class Mul extends BinOperation {
    op() { return "\\*"; }
    name() { return "*"; }
    type() { return CalculatorOp.factor; }
    doCalc(a, b) { return a * b; }
}

class Div extends BinOperation {
    op() { return "/"; }
    type() { return CalculatorOp.factor; }
    doCalc(a, b) { return a / b; }
}

class Sin extends FuncRROperation {
    op() { return "sin"; }
    doCalc(a) { return Math.sin(this.calculator.toAngle(a)); }
}

class Cos extends FuncRROperation {
    op() { return "cos"; }
    doCalc(a) { return Math.cos(this.calculator.toAngle(a)); }
}

class Sqrt extends FuncRROperation {
    op() { return "sqrt"; }
    doCalc(a) { return Math.sqrt(a); }
}

const operations = [
    LeftBracketOperation,
    RightBracketOperation,
    Plus,
    Minus,
    SignMinus,
    SignPlus,
    Mul,
    Div,
    Sin,
    Cos,
    Sqrt,
    Deg,
    Rad,
    NumOperation,
    PiOperation,
    MemOperation,
];


class Calculator {
    isIn(reglist, cmd, def) {
        let name = cmd.name();
        if (!reglist || reglist.length === 0) return def;
        for (let rs of reglist) {
            if (rs === "+" || rs === "*") rs = "\\" + rs;
            const re = new RegExp("^" + rs + "$");
            if (re.test(name)) {
                return true;
            }
        }
        return false;
    }

    constructor(params) {
        this.params = params || {};
        this.params.decimals = this.params.decimals || 13;
        this.deg = this.params.deg || true;
        this.lastResult = 0;
        this.operations = [];
        this.mem = {};
        this.row = 0;
        this.stack = [];
        this.lexer = new Lexer();
        /*
        this.lexer.addRule(/[()]/, function (lexeme) {
             return lexeme; // punctuation (i.e. "(", ")")
        });
         */
        for (const op of operations) {
            const oper = new op(this);
            if (!this.isIn(this.params.allowed, oper, true)) {
                continue;
            }
            if (this.isIn(this.params.illegals, oper, false)) {
                continue;
            }
            this.operations.push(oper);
            this.lexer.addRule(new RegExp(oper.op(), oper.params()),function (lexme) {
               return oper.lexfunc(lexme);
            })
        }
        this.lexer.addRule(/\s+/, function () {
             /* skip whitespace */
        });
        this.parser = new Parser();
    }

    toAngle(a) {
        if (!this.deg) return a;
        return a*Math.PI/180;
    }

    calcOne(s) {
        try {
            this.stack = [];
            this.lexer.setInput(s);
            let tokens = [], token;
            let lastToken = new LeftBracketOperation(this);
            while (token = this.lexer.lex()) {
                token = token.checkSign(lastToken);
                tokens.push(token);
                lastToken = token;
            }
            let cmds = this.parser.parse(tokens);
            let calc = "";
            for (const cmd of cmds) {
                cmd.calc();
            }

            let extraBefore = "";
            for (const cmd of tokens) {
                calc += cmd.output(extraBefore);
                extraBefore = cmd.extraSpaceAfter();
            }

            let res = "";
            if (this.stack.length > 0) {
                res = this.stack.pop();
                this.lastResult = res;
                calc += " = " + res;
            }

            return {res: res, calc: calc};
        } catch (e) {
            return {res: undefined, calc: e.message};
        }
    }

    calc(s) {
        let result = [];
        let lines = s.split("\n");
        let i = 0;
        for (const line of lines) {
            i++;
            this.row = i;
            this.mem["r"] = this.lastResult;
            // remove comments # and trim
            let tline = line.replace(/ *#.*/, "").trim();
            if (!tline) continue;
            const parts = tline.split("->");
            let toMem = "";
            const mi = tline.indexOf("->");
            if (mi >= 0) {
                toMem = " " + tline.substring(mi);
            }
            tline = parts[0].trim();
            let r = {res: this.lastResult, calc: ""};
            if (tline)
                r = this.calcOne(tline);
            r.calc = `r${i}: ${r.calc}${toMem}`;
            result.push(r);
            this.mem["r"+i] = r.res;
            this.mem["r"] = this.lastResult;
            for (let i=1; i<parts.length; i++) {
                const mem = parts[i].trim();
                if (mem) this.mem[mem] = r.res;
            }
        }
        return result;
    }
}

