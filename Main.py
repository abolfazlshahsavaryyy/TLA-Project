import re
from typing import Dict, List, Set, Optional
from graphviz import Digraph


class ParseTreeNode:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.children: List['ParseTreeNode'] = []

    def add_child(self, child: 'ParseTreeNode'):
        self.children.append(child)

    def print_tree(self, indent: str = ""):
        print(indent + self.symbol)
        for child in self.children:
            child.print_tree(indent + "  ")
    def rename_symbol(self, old: str, new: str, count: Optional[int] = None):
        replaced = 0
        def _rename(node: 'ParseTreeNode'):
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

        def add_nodes_edges(node: 'ParseTreeNode', parent_id: Optional[str] = None):
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
        self.productions: Dict[str, List[str]] = {}
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        self.parse_table: Dict[str, Dict[str, str]] = {}
        self.non_terminals: Set[str] = set()
        self.terminals: Set[str] = set()

    def load_from_file(self, filename: str):
        rhs_symbols = set()
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                match = re.match(r'^(\w+)\s*->\s*(.+)$', line)
                if match:
                    lhs = match.group(1)
                    self.non_terminals.add(lhs)
                    rhs_list = [alt.strip() for alt in match.group(2).split('|')]
                    for rule in rhs_list:
                        rhs_symbols.update(rule.split())
                    if lhs in self.productions:
                        self.productions[lhs].extend(rhs_list)
                    else:
                        self.productions[lhs] = rhs_list
        self.terminals = rhs_symbols - self.non_terminals

    def compute_first_sets(self):
        self.first_sets = {non_term: set() for non_term in self.non_terminals}
        changed = True
        while changed:
            changed = False
            for non_term, rules in self.productions.items():
                for rule in rules:
                    symbols = rule.split()
                    for symbol in symbols:
                        if symbol in self.terminals or symbol == 'eps':
                            if symbol not in self.first_sets[non_term]:
                                self.first_sets[non_term].add(symbol)
                                changed = True
                            break
                        else:
                            before = len(self.first_sets[non_term])
                            self.first_sets[non_term].update(
                                s for s in self.first_sets[symbol] if s != 'eps'
                            )
                            if 'eps' in self.first_sets[symbol]:
                                continue
                            break
                    else:
                        if 'eps' not in self.first_sets[non_term]:
                            self.first_sets[non_term].add('eps')
                            changed = True

    def compute_follow_sets(self):
        self.follow_sets = {non_term: set() for non_term in self.non_terminals}
        start_symbol = next(iter(self.productions))
        self.follow_sets[start_symbol].add('$')
        changed = True
        while changed:
            changed = False
            for lhs, rules in self.productions.items():
                for rule in rules:
                    symbols = rule.split()
                    for i, symbol in enumerate(symbols):
                        if symbol in self.non_terminals:
                            next_symbols = symbols[i+1:]
                            follow_before = self.follow_sets[symbol].copy()
                            if next_symbols:
                                first_of_next = self._first_of_sequence(next_symbols)
                                self.follow_sets[symbol].update(first_of_next - {'eps'})
                                if 'eps' in first_of_next:
                                    self.follow_sets[symbol].update(self.follow_sets[lhs])
                            else:
                                self.follow_sets[symbol].update(self.follow_sets[lhs])
                            if follow_before != self.follow_sets[symbol]:
                                changed = True

    def _first_of_sequence(self, sequence: List[str]) -> Set[str]:
        result = set()
        for symbol in sequence:
            if symbol in self.terminals:
                result.add(symbol)
                return result
            elif symbol in self.non_terminals:
                result.update(s for s in self.first_sets[symbol] if s != 'eps')
                if 'eps' not in self.first_sets[symbol]:
                    return result
            else:
                result.add(symbol)
                return result
        result.add('eps')
        return result

    def build_parse_table(self):
        self.compute_first_sets()
        self.compute_follow_sets()
        for non_term in self.non_terminals:
            self.parse_table[non_term] = {}
        for non_term, rules in self.productions.items():
            for rule in rules:
                symbols = rule.split()
                first = self._first_of_sequence(symbols)
                for terminal in first:
                    if terminal != 'eps':
                        self.parse_table[non_term][terminal] = rule
                if 'eps' in first:
                    for terminal in self.follow_sets[non_term]:
                        self.parse_table[non_term][terminal] = rule

    def display_parse_table(self):
        print("\nParse Table LL(1):")
        for non_term, row in self.parse_table.items():
            for terminal, production in row.items():
                print(f"{non_term} , {terminal} => {non_term} -> {production}")

class DPDA:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.parse_table = grammar.parse_table

    def build_parse_tree(self, tokens: List[str]) -> Optional[ParseTreeNode]:
        tokens.append('$')
        index = 0
        root = ParseTreeNode(next(iter(self.grammar.productions)))
        stack = [('$', None), (root.symbol, root)]

        while stack:
            top_symbol, top_node = stack.pop()
            current_token = tokens[index]

            if top_symbol == current_token == '$':
                return root

            elif top_symbol == current_token:
                index += 1
                continue

            elif top_symbol in self.grammar.terminals:
                leaf = ParseTreeNode(current_token)
                if top_node:
                    top_node.add_child(leaf)
                index += 1

            elif top_symbol in self.grammar.non_terminals:
                rule = self.parse_table.get(top_symbol, {}).get(current_token)
                if not rule:
                    print(f"Error: no rule for {top_symbol} with lookahead '{current_token}'")
                    return None
                symbols = rule.split()
                children = [ParseTreeNode(sym) for sym in symbols if sym != 'eps']
                if top_node:
                    for child in children:
                        top_node.add_child(child)
                for sym, child_node in reversed(list(zip(symbols, children))):
                    if sym != 'eps':
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
    grammar.load_from_file("grammar.txt")
    grammar.build_parse_table()
    grammar.display_parse_table()

    # Parse Tree
    print("\nMaking Parse Tree")
    input_tokens = ['id', '+', 'id', '*', 'id']
    dpda = DPDA(grammar)
    parse_tree = dpda.build_parse_tree(input_tokens)
    print("\nGenerating Graphviz parse tree...")
    dot = parse_tree.to_graphviz()
    dot.render("parse_tree", view=True, format='pdf')

    if parse_tree:
        parse_tree.print_tree()
        print("\nThe string was parsed successfully.")
    else:
        print("\nThe parse tree was not created.")
    if parse_tree:
        print("\nOriginal Parse Tree:")
        parse_tree.print_tree()

        print("\nRenaming 'id' to 'x' (only first occurrence):")
        parse_tree.rename_symbol('id', 'x', count=1)
        parse_tree.print_tree()

        print("\nRenaming remaining 'id' to 'y':")
        parse_tree.rename_symbol('id', 'y')
        parse_tree.print_tree()
    else:
        print("\nParse tree was not created.")


