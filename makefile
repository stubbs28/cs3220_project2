asm_grammar.py: asm.ebnf
	grako -m asm_grammar -o asm_grammar.py asm.ebnf

clean:
	rm asm_grammar.py
