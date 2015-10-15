import math
from asm_grammar import asm_grammarParser

ADDR = None
OUTPUT = ''
LABEL = {}

ALU = {'add':0, 'sub':1, 'and':4, 'or':5, 'xor':6, 'nand':12, 'nor':13, 'xnor':14, 'mvhi':11}
CMP = {'f':0, 'eq':1, 'lt':2, 'lte':3, 't':8, 'ne':9, 'gte':10, 'gt':11}

def htosi(val):
    uintval = int(val,16)
    bits = 4 * (len(val) - 2)
    if uintval >= math.pow(2, bits-1):
        uintval = int(0 - (math.pow(2, bits) - uintval))
    return uintval

def getReg(reg, key):
    if not key in reg:
        return ''
    ret = reg[key].lower()
    if ret == 'rv':
        ret = 3
    elif ret == 'ra':
        ret = 15
    elif ret == 'sp':
        ret = 14
    elif ret == 'fp':
        ret = 13
    elif ret == 'gp':
        ret = 12
    elif ret[0] == 't':
        ret = int(ret[1]) + 4
    elif ret[0] == 's':
        ret = int(ret[1]) + 6
    else:
        ret = int(ret[1:])
    return hex(ret)[2:]

def getImm(ast):
    if not 'imm' in ast['fmt']:
        return '000'
    imm = ast['fmt']['imm']
    ret = ''
    if imm['n'] is not None:
        ret = imm['n']
    else:
        ret = LABEL[imm['s']]
        if 'pc_rel' in ast:
            ret -= ast['addr']
        ret = hex(ret & 0xFFFF)[2:].rjust(4, '0')
    return ret

def writeOut(ast):
    global OUTPUT
    addr = '0x' + hex(ast['addr'])[2:].rjust(8, '0')
    func_pre = ast['func_pre'] if 'func_pre' in ast else ''
    func_post = ast['func_post'] if 'func_post' in ast else ''
    func = func_pre + ast['func'] + func_post
    OUTPUT += '-- @ {0} : {1}\t{2}\n'.format(addr, func, ast['fmt']['comment'])

    addr = hex(ast['addr'] >> 2)[2:].rjust(8, '0')
    func = hex(ast['func_val'])[2:]
    opcd = hex(ast['opcd'])[2:]

    fmt = ast['fmt']
    val = (getReg(fmt, 'rd') + getReg(fmt, 'rs1') + getReg(fmt, 'rs2')).ljust(2,'0') + getImm(ast)

    OUTPUT += '{0} : {1}{2}{3};\n'.format(addr, val, func, opcd)

class asm_grammarSemantics(object):
    def orig(self, ast):
        global ADDR
        ADDR = ast
        return None

    def name(self, ast):
        global LABEL
        print (ast)
        LABEL[ast[0]] = int(ast[1])
        return None

    def word(self, ast):
        global ADDR
        ast.update({'addr' : ADDR})
        ADDR += 4
        return ast

    def instruction(self, ast):
        global ADDR
        if ast is None:
            ast = {}
        ast.update({'addr': ADDR})
        ADDR += 4
        return ast

    def alu(self, ast):
        func = ALU[ast['func'].lower()]
        ast['func_val'] = int(func)
        return ast

    def alui(self, ast):
        ast['func_post'] = 'i'
        ast['opcd'] = 8 
        return ast

    def alur(self, ast):
        ast['opcd'] = 0 
        return ast

    def load(self, ast):
        ast['func_val'] = 0
        ast['opcd'] = 9 
        return ast

    def store(self, ast):
        ast['func_val'] = 0
        ast['opcd'] = 5
        return ast

    def cmp(self, ast):
        func_val = ast['func_val'] + CMP[ast['func'].lower()]
        del ast['func_val']
        ast['func_val'] = func_val
        return ast

    def cmpi(self, ast):
        ast['func_post'] = 'i'
        ast['func_val'] = 0
        ast['opcd'] = 10
        return ast

    def cmpr(self, ast):
        ast['func_val'] = 0
        ast['opcd'] = 2 
        return ast

    def branchz(self, ast):
        ast['pc_rel'] = True
        ast['func_pre'] = 'b'
        ast['func_post'] = 'z'
        ast['func_val'] = 4
        ast['opcd'] = 2 
        return ast

    def branch(self, ast):
        ast['pc_rel'] = True
        ast['func_pre'] = 'b'
        ast['func_val'] = 0
        ast['opcd'] = 2 
        return ast

    def jal(self, ast):
        ast['pc_rel'] = True
        ast['func_val'] = 0
        ast['opcd'] = 11 

    #ToDo
    def pseudo(self, ast):
        p = ast['func'].lower()
        if p == 'br':
            pass
        elif p == 'not':
            pass
        elif p == 'ble':
            pass
        elif p == 'bge':
            pass
        elif p == 'call':
            pass
        elif p == 'ret':
            pass
        elif p == 'jmp':
            pass

    def label(self, ast):
        LABEL[ast['label']] = ADDR
        return None

    def fmt0(self, ast):
        ast.update({'comment' : '{0}, {1}, {2}'.format(ast['rd'], ast['rs1'], ast['rs2'])})
        return ast

    def fmt1(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}, {1}, {2}'.format(ast['rd'], ast['rs1'], imm)})
        return ast

    def fmt2(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}, {1}'.format(ast['rd'], imm)})
        return ast

    def fmt3(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}, {1}({2})'.format(ast['rd'], imm, ast['rs1'])})
        return ast

    def fmt4(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}, {1}({2})'.format(ast['rs2'], imm, ast['rs1'])})
        return ast

    def fmt5(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}, {1}, {2}'.format(ast['rs1'], ast['rs2'], imm)})
        return ast

    def fmt6(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}, {1}'.format(ast['rs1'], imm)})
        return ast

    def fmt7(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}'.format(imm)})
        return ast

    def fmt8(self, ast):
        ast.update({'comment' : '{0}, {1}'.format(ast['rd'], ast['rs'])})
        return ast

    def fmt9(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}({1})'.format(imm, ast['rs1'])})
        return ast

    def hex(self, ast):
        x = htosi('0x' + ast[2:].rjust(4, '0'))
        return x

    def dec(self, ast):
        return int(ast)

    def __default__(self, ast):
        return ast

def main(filename):
    global OUTPUT
    import json
    with open(filename) as f:
        text = f.read()
    parser = asm_grammarParser(eol_comments_re=';.*?$', ignorecase=True, parseinfo=False)
    ast = parser.parse(
        text,
        'start',
        filename=filename,
        trace=False,
        whitespace=None,
        nameguard=None,
        semantics=asm_grammarSemantics())

    print('AST:')
    print(ast)
    print()
    print('JSON:')
    print(json.dumps(ast, indent=2))
    print()

    for s in ast:
        if 'word' in s:
            continue
        writeOut(s)

    print(OUTPUT)


if __name__ == '__main__':
    import argparse
    import string
    import sys

    parser = argparse.ArgumentParser(description="Simple parser for asm_grammar.")
    parser.add_argument('file', metavar="FILE", help="the input file to parse")
    args = parser.parse_args()

    main(args.file)
