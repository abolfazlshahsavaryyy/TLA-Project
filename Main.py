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


# ====================== تست در main ======================

if __name__ == "__main__":
    grammar = Grammar()
    grammar.load_from_file("grammar.txt")
    grammar.build_parse_table()
    grammar.display_parse_table()
