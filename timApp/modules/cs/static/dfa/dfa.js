/*!
* Class for deterministic finite automate
*/
class DFA {

    /*!
     * Convert string to dfa
     * \fn constructor(s)
     * \param string s DFA as a string representation
     * \return JSON resulting DFA structure
     */
    constructor(s) {
        // regexps for various syntaxes
        // syntax 1:  0: S1 -> S2
        // syntax 2:  S1 0-> S2
        // syntax 3:  +S1 0 S2
        // start node: ->S1
        const re1 = /^ *([^ >:+-]+): *([^ >:+-]+) *-?>? *([^ >:+-]+) *$/;
        const re2 = /^ *([^ >:+-]+) +([^ >:+-]+) *(->|-|>| ) *([^ >:+-]+) *$/;
        const re3 = /^\+ *([^ ]+) +([^ ]+) +([^ ]+) *$/;
        const reStart = /^ *->? *([^ >:+-]+)$/;

        this.arcs = [];
        this.nodes = {};
        this.first = null;

        let firstFound = undefined;
        let lastUsed = undefined;
        let dfa = this;

        // Helper functions
        function addLNode(s) { // remembers last name
            lastUsed = addNode(s);
            return lastUsed;
        }


        function addNode(s) {
            let accept = false;
            if (s.indexOf('*') >= 0) accept = true;
            s = s.replace("*", "").trim();
            if (s === ".") s = lastUsed;
            if (s === undefined) s = "???";
            let node = dfa.nodes[s];
            if (!node) node = {name: s, arcs: {}};
            if (accept) node.accept = true;
            dfa.nodes[s] = node;
            if (!firstFound) firstFound = s;
            return s;
        }


        function addArc(value, from, to) {
            const arc = {value: value, from: from, to: to};
            dfa.arcs.push(arc);
            if (value === -1) return;
            const node = dfa.nodes[from];
            if (node.arcs[value]) node.error = true;
            node.arcs[value] = arc;
        }


        // Checking lines from string representation
        for (let line of s.split("\n")) {
            line = line.trim();
            if (!line) continue; // forget empty lines

            let r = reStart.exec(line);
            if (r) { // start node
                const n = addLNode(r[1])
                addArc(-1, 'startpoint', n);
                this.first = this.nodes[n];
                continue;
            }

            r = re1.exec(line);
            if (r) { // syntax 1: 1: S1 -> S2
                const v = r[1];
                const f = addLNode(r[2]);
                const t = addNode(r[3]);
                addArc(v, f, t);
                continue;
            }

            r = re2.exec(line);
            if (r) { // syntax 2: S1 1-> S2
                const v = r[2];
                const f = addLNode(r[1]);
                const t = addNode(r[4]);
                addArc(v, f, t);
                continue;
            }

            r = re3.exec(line);
            if (r) { // syntax 3: +S1 S2 S3
                const f = addLNode(r[1]);
                const t1 = addNode(r[2]);
                const t2 = addNode(r[3]);
                addArc(0, f, t1);
                addArc(1, f, t2);
            }
        }


        // check if there is no start node
        if (!this.first && firstFound) {
            addArc(-1, 'startpoint', firstFound);
            this.first = this.nodes[firstFound];
        }


        // check if self transitions are needed
        for (let n in this.nodes) {
            const node = this.nodes[n];
            let count = 0;
            let startFound = false;
            for (let a in node.arcs) {
                count++;
                if (a === "*") {
                    startFound = true;
                    break;
                }
            }
            if (count === 1 && !startFound) {
                addArc("*", n, n);
            }
        }
    }


    /*!
     * Check if input s is accepted by this dfa
     * \param s input to check
     * \return boolean true if accpeted
     */
    accepts(s) {
        let active = this.first;
        if (!active) return false;
        for (let value of s) {
            let activeArc = active.arcs[value];
            if (!activeArc) activeArc = active.arcs['*'];
            if (!activeArc) return false;
            active = this.nodes[activeArc.to];
        }
        if (!active || !active.accept) return false;
        return active.accept;
    }
} // DFA

