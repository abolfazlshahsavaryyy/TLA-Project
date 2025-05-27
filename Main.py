class Grammar:
    def __init__(self):
        self.rules = {}

    def load_from_file(self, filepath):
       
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or '->' not in line:
                    continue

                lhs, rhs = line.split('->')
                lhs = lhs.strip()
                productions = [prod.strip().split() for prod in rhs.strip().split('|')]

                if lhs not in self.rules:
                    self.rules[lhs] = []
                self.rules[lhs].extend(productions)

    def display(self):
       
        for lhs, rhs_list in self.rules.items():
            rhs_str = ' | '.join([' '.join(prod) for prod in rhs_list])
            print(f"{lhs} -> {rhs_str}")

if __name__ == "__main__":
    grammar = Grammar()
    grammar.load_from_file("grammar.txt")
    grammar.display()
