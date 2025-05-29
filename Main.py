import re
from typing import Dict, List, Set

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

        # شناسایی ترمینال‌ها
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
        print("جدول تجزیه LL(1):")
        for non_term, row in self.parse_table.items():
            for terminal, production in row.items():
                print(f"{non_term} , {terminal} => {non_term} -> {production}")


# ====================== تست در main ======================

if __name__ == "__main__":
    grammar = Grammar()
    grammar.load_from_file("grammar.txt")
    grammar.build_parse_table()
    grammar.display_parse_table()
