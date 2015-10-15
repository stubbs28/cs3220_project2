asm_grammar.py: asm.ebnf
	grako -m asm_grammar -o asm_grammar.py asm.ebnf

test: asm_grammar.py
	python asm_grammar.py test.a32 start
