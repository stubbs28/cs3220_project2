asm_grammar.py: asm.ebnf
	grako -m asm_grammar -o asm_grammar.py asm.ebnf

test: asm_grammar.py
	python assembler.py Test2.a32

sorter: asm_grammar.py
	python assembler.py Sorter2.a32
