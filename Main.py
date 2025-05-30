import re
from typing import Dict, List, Set, Optional, Tuple
from graphviz import Digraph


class ParseTreeNode:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.children: List["ParseTreeNode"] = []

    def add_child(self, child: "ParseTreeNode"):
        self.children.append(child)

    def print_tree(self, indent: str = ""):
        print(indent + self.symbol)
        for child in self.children:
            child.print_tree(indent + "  ")

    def rename_symbol(self, old: str, new: str, count: Optional[int] = None):
        replaced = 0

        def _rename(node: "ParseTreeNode"):
            nonlocal replaced
            if node.symbol == old and (count is None or replaced < count):
                node.symbol = new
                replaced += 1
            for child in node.children:
                _rename(child)

        _rename(self)

    def to_graphviz(self) -> Digraph:
        dot = Digraph()
        node_id_counter = [0]

        def add_nodes_edges(node: "ParseTreeNode", parent_id: Optional[str] = None):
            node_id = f"n{node_id_counter[0]}"
            node_id_counter[0] += 1
            dot.node(node_id, node.symbol)
            if parent_id:
                dot.edge(parent_id, node_id)
            for child in node.children:
                add_nodes_edges(child, node_id)

        add_nodes_edges(self)
        return dot


class Grammar:
    def __init__(self):
        self.start_symbol: Optional[str] = None
        self.non_terminals: Set[str] = set()
        self.terminals: Set[str] = set()
        self.productions: Dict[str, List[str]] = {}
        self.lexical_rules: Dict[str, str] = {}  # Terminal -> regex pattern (string)
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        self.parse_table: Dict[str, Dict[str, str]] = {}

    def load_from_file(self, filename: str):
        mode = None
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    # Skip comments and empty lines
                    continue

                # Detect mode by line pattern
                if line.startswith("START"):
                    # e.g. START = E
                    self.start_symbol = line.split("=")[1].strip()
                    mode = None
                    continue

                if line.startswith("NON_TERMINALS"):
                    # e.g. NON_TERMINALS = E , E_prime , T , T_prime , F
                    nts = line.split("=")[1]
                    self.non_terminals = {nt.strip() for nt in nts.split(",")}
                    mode = None
                    continue

                if line.startswith("TERMINALS"):
                    # e.g. TERMINALS = IDENTIFIER , LITERAL , PLUS , STAR , LEFT_PAR , RIGHT_PAR
                    ts = line.split("=")[1]
                    self.terminals = {t.strip() for t in ts.split(",")}
                    mode = None
                    continue

                # Now productions or lexical definitions
                if "->" in line:
                    # Production or lexical rule
                    # Distinguish lexical rule by regex delimiters "/" or "\"
                    lhs, rhs = line.split("->", 1)
                    lhs = lhs.strip()
                    rhs = rhs.strip()

                    # Check if rhs looks like a regex (starts and ends with / or \)
                    if (rhs.startswith("/") and rhs.endswith("/")) or (
                        rhs.startswith("\\") and rhs.endswith("\\")
                    ):
                        # Lexical rule
                        # Remove surrounding / or \ and trim spaces
                        regex_pattern = rhs[1:-1].strip()
                        self.lexical_rules[lhs] = regex_pattern
                    else:
                        # Production rule
                        mode = "productions"
                        if lhs not in self.productions:
                            self.productions[lhs] = []
                        # Split alternatives on "|"
                        alternatives = [alt.strip() for alt in rhs.split("|")]
                        self.productions[lhs].extend(alternatives)
                else:
                    # If no arrow, just ignore or end
                    pass

        # Some terminals might be defined by lexical rules but not listed explicitly
        self.terminals.update(self.lexical_rules.keys())

    def compute_first_sets(self):
        self.first_sets = {nt: set() for nt in self.non_terminals}
        changed = True
        while changed:
            changed = False
            for nt, rules in self.productions.items():
                for rule in rules:
                    symbols = rule.split()
                    for symbol in symbols:
                        if symbol in self.terminals or symbol == "eps":
                            if symbol not in self.first_sets[nt]:
                                self.first_sets[nt].add(symbol)
                                changed = True
                            break
                        else:
                            before_len = len(self.first_sets[nt])
                            self.first_sets[nt].update(
                                s
                                for s in self.first_sets.get(symbol, set())
                                if s != "eps"
                            )
                            if "eps" in self.first_sets.get(symbol, set()):
                                continue
                            break
                    else:
                        # If all symbols had eps
                        if "eps" not in self.first_sets[nt]:
                            self.first_sets[nt].add("eps")
                            changed = True

    def _first_of_sequence(self, seq: List[str]) -> Set[str]:
        result = set()
        for sym in seq:
            if sym in self.terminals:
                result.add(sym)
                return result
            elif sym in self.non_terminals:
                result.update(s for s in self.first_sets.get(sym, set()) if s != "eps")
                if "eps" not in self.first_sets.get(sym, set()):
                    return result
            else:
                result.add(sym)
                return result
        result.add("eps")
        return result

    def compute_follow_sets(self):
        self.follow_sets = {nt: set() for nt in self.non_terminals}
        if not self.start_symbol:
            raise RuntimeError("Start symbol not set!")
        self.follow_sets[self.start_symbol].add("$")
        changed = True
        while changed:
            changed = False
            for lhs, rules in self.productions.items():
                for rule in rules:
                    symbols = rule.split()
                    for i, sym in enumerate(symbols):
                        if sym in self.non_terminals:
                            next_symbols = symbols[i + 1 :]
                            follow_before = self.follow_sets[sym].copy()
                            first_next = self._first_of_sequence(next_symbols)
                            self.follow_sets[sym].update(first_next - {"eps"})
                            if "eps" in first_next or not next_symbols:
                                self.follow_sets[sym].update(self.follow_sets[lhs])
                            if follow_before != self.follow_sets[sym]:
                                changed = True

    def build_parse_table(self):
        self.compute_first_sets()
        self.compute_follow_sets()
        self.parse_table = {nt: {} for nt in self.non_terminals}
        for nt, rules in self.productions.items():
            for rule in rules:
                symbols = rule.split()
                first = self._first_of_sequence(symbols)
                for terminal in first:
                    if terminal != "eps":
                        self.parse_table[nt][terminal] = rule
                if "eps" in first:
                    for terminal in self.follow_sets[nt]:
                        self.parse_table[nt][terminal] = rule

    def display_parse_table(self):
        print("\nParse Table LL(1):")
        for nt, row in self.parse_table.items():
            for term, prod in row.items():
                print(f"{nt} , {term} => {nt} -> {prod}")


class Lexer:
    def __init__(self, lexical_rules: Dict[str, str]):
        # lexical_rules: terminal -> regex pattern (string)
        # Compile regex patterns into one big regex with named groups
        self.terminals = list(lexical_rules.keys())
        parts = []
        for term in self.terminals:
            pattern = lexical_rules[term]
            # Remove whitespace in pattern for safety in case user used spaces in regex like [a -z]
            pattern = pattern.replace(" ", "")
            parts.append(f"(?P<{term}>{pattern})")
        self.master_pattern = re.compile("|".join(parts))

    def tokenize(self, text: str) -> List[str]:
        tokens = []
        pos = 0
        while pos < len(text):
            match = self.master_pattern.match(text, pos)
            if not match:
                # Skip whitespace or unknown characters gracefully
                if text[pos].isspace():
                    pos += 1
                    continue
                raise RuntimeError(
                    f"Unexpected character at position {pos}: {text[pos]!r}"
                )
            term = match.lastgroup
            tokens.append(term)
            pos = match.end()
        return tokens


class DPDA:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.parse_table = grammar.parse_table

    def build_parse_tree(self, tokens: List[str]) -> Optional[ParseTreeNode]:
        tokens = tokens + ["$"]
        index = 0
        root = ParseTreeNode(self.grammar.start_symbol)
        stack: List[Tuple[str, Optional[ParseTreeNode]]] = [
            ("$", None),
            (self.grammar.start_symbol, root),
        ]

        while stack:
            top_symbol, top_node = stack.pop()
            current_token = tokens[index]

            if top_symbol == current_token == "$":
                return root

            if top_symbol == current_token:
                index += 1
                if top_node:
                    top_node.add_child(ParseTreeNode(current_token))
                continue

            if top_symbol in self.grammar.terminals:
                # Terminal mismatch
                print(
                    f"Error: expected terminal {top_symbol} but found {current_token}"
                )
                return None

            if top_symbol in self.grammar.non_terminals:
                rule = self.parse_table.get(top_symbol, {}).get(current_token)
                if not rule:
                    print(
                        f"Error: no rule for {top_symbol} with lookahead '{current_token}'"
                    )
                    return None
                symbols = rule.split()
                children_nodes = [ParseTreeNode(sym) for sym in symbols if sym != "eps"]
                if top_node:
                    for child in children_nodes:
                        top_node.add_child(child)
                # Push in reverse order
                for sym, child_node in reversed(list(zip(symbols, children_nodes))):
                    if sym != "eps":
                        stack.append((sym, child_node))
            else:
                print(f"Error: unknown symbol {top_symbol}")
                return None

        if index != len(tokens) - 1:
            print("Error: input not fully consumed")
            return None
        return root


if __name__ == "__main__":
    grammar = Grammar()
    grammar.load_from_file("grammar2.txt")

    print("Start symbol:", grammar.start_symbol)
    print("Non-terminals:", grammar.non_terminals)
    print("Terminals:", grammar.terminals)
    print("Productions:")
    for nt, rules in grammar.productions.items():
        for rule in rules:
            print(f"  {nt} -> {rule}")
    print("Lexical Rules:")
    for t, r in grammar.lexical_rules.items():
        print(f"  {t} -> {r}")

    grammar.build_parse_table()
    grammar.display_parse_table()

    lexer = Lexer(grammar.lexical_rules)

    input_string = input("please inpute your language: ")
    print("\nInput string:", input_string)

    try:
        tokens = lexer.tokenize(input_string)
        print("Tokens:", tokens)
    except RuntimeError as e:
        print("Lexer error:", e)
        tokens = []

    if tokens:
        dpda = DPDA(grammar)
        parse_tree = dpda.build_parse_tree(tokens)
        if parse_tree:
            print("\nParse tree:")
            parse_tree.print_tree()

            print("\nGenerating Graphviz parse tree...")
            dot = parse_tree.to_graphviz()
            dot.render("parse_tree", view=True, format="pdf")
        else:
            print("\nParsing failed.")
