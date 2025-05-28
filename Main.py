import re

class Grammar:
    def __init__(self):
        self.rules = {}
        self.token_regex = {}
        self.first_sets = {}
        self.follow_sets = {}
        self.non_terminals = set()
        self.terminals = set()
        self.start_symbol = None

    def load_from_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('%token'):
                    _, name, pattern = line.split(maxsplit=2)
                    self.token_regex[name] = re.compile(pattern)
                    self.terminals.add(name)
                    continue

                if '->' not in line:
                    continue
                lhs, rhs = line.split('->')
                lhs = lhs.strip()
                if self.start_symbol is None:
                    self.start_symbol = lhs

                productions = [prod.strip().split() for prod in rhs.strip().split('|')]
                if lhs not in self.rules:
                    self.rules[lhs] = []
                self.rules[lhs].extend(productions)

                self.non_terminals.add(lhs)
                for prod in productions:
                    for symbol in prod:
                        if symbol != 'eps' and symbol not in self.rules:
                            self.terminals.add(symbol)

    def display(self):
        for lhs, rhs_list in self.rules.items():
            rhs_str = ' | '.join([' '.join(prod) for prod in rhs_list])
            print(f"{lhs} -> {rhs_str}")

    def compute_first_sets(self):
        for symbol in self.rules:
            self.first_sets[symbol] = set()

        def first(symbol):
            if symbol not in self.rules:
                return {symbol}
            if self.first_sets[symbol]:
                return self.first_sets[symbol]
            result = set()
            for prod in self.rules[symbol]:
                for sym in prod:
                    sym_first = first(sym)
                    result.update(sym_first - {'eps'})
                    if 'eps' not in sym_first:
                        break
                else:
                    result.add('eps')
            self.first_sets[symbol] = result
            return result

        for non_terminal in self.rules:
            first(non_terminal)

    def compute_follow_sets(self):
        for non_terminal in self.rules:
            self.follow_sets[non_terminal] = set()
        self.follow_sets[self.start_symbol].add('$')

        changed = True
        while changed:
            changed = False
            for lhs, productions in self.rules.items():
                for prod in productions:
                    for i in range(len(prod)):
                        B = prod[i]
                        if B in self.rules:
                            beta = prod[i + 1:]
                            if beta:
                                first_beta = self.compute_first_of_string(beta)
                                before = len(self.follow_sets[B])
                                self.follow_sets[B].update(first_beta - {'eps'})
                                if 'eps' in first_beta:
                                    self.follow_sets[B].update(self.follow_sets[lhs])
                                if len(self.follow_sets[B]) > before:
                                    changed = True
                            else:
                                before = len(self.follow_sets[B])
                                self.follow_sets[B].update(self.follow_sets[lhs])
                                if len(self.follow_sets[B]) > before:
                                    changed = True

    def compute_first_of_string(self, symbols):
        result = set()
        for symbol in symbols:
            symbol_first = self.first_sets.get(symbol, {symbol})
            result.update(symbol_first - {'eps'})
            if 'eps' not in symbol_first:
                break
        else:
            result.add('eps')
        return result

    def display_first_follow(self):
        print("\nFIRST sets:")
        for symbol, f_set in self.first_sets.items():
            print(f"FIRST({symbol}) = {f_set}")

        print("\nFOLLOW sets:")
        for symbol, f_set in self.follow_sets.items():
            print(f"FOLLOW({symbol}) = {f_set}")

    def build_parsing_table(self):
        table = {}
        for lhs, productions in self.rules.items():
            for prod in productions:
                first_prod = self.compute_first_of_string(prod)
                for terminal in first_prod - {'eps'}:
                    table[(lhs, terminal)] = prod
                if 'eps' in first_prod:
                    for terminal in self.follow_sets[lhs]:
                        table[(lhs, terminal)] = prod
        return table

    def tokenize(self, input_string):
        tokens = []
        while input_string:
            input_string = input_string.lstrip()
            match = None
            for name, pattern in self.token_regex.items():
                match = pattern.match(input_string)
                if match:
                    tokens.append(name)
                    input_string = input_string[match.end():]
                    break
            if not match:
                raise ValueError(f"Unexpected token at: {input_string}")
        return tokens


class DPDA:
    def __init__(self, parsing_table, start_symbol, non_terminals):
        self.parsing_table = parsing_table
        self.start_symbol = start_symbol
        self.non_terminals = non_terminals

    def process(self, input_tokens):
        stack = ['$', self.start_symbol]
        input_tokens = input_tokens + ['$']
        pointer = 0

        while stack:
            top = stack.pop()
            current_token = input_tokens[pointer]

            if top == current_token:
                pointer += 1
            elif top in self.non_terminals:
                key = (top, current_token)
                if key in self.parsing_table:
                    production = self.parsing_table[key]
                    if production != ['eps']:
                        stack.extend(reversed(production))
                else:
                    return False
            else:
                return False

        return pointer == len(input_tokens)


if __name__ == "__main__":
    grammar = Grammar()
    grammar.load_from_file("grammar.txt")
    print("Loaded Grammar:")
    grammar.display()

    grammar.compute_first_sets()
    grammar.compute_follow_sets()
    grammar.display_first_follow()

    parsing_table = grammar.build_parsing_table()

    dpda = DPDA(parsing_table, start_symbol=grammar.start_symbol, non_terminals=grammar.non_terminals)

    test_inputs = [
        
        '(a + b) * (c + d)',
        '(123)',
        'a * b * c + d'
    ]

    for input_str in test_inputs:
        try:
            tokenized = grammar.tokenize(input_str.replace('id', 'x'))  # replacing 'id' with 'x' as IDENTIFIER
            result = dpda.process(tokenized)
            print(f"Input: {input_str:<25} => {'Accepted' if result else 'Rejected'}")
        except ValueError as e:
            print(f"Input: {input_str:<25} => Error: {e}")
