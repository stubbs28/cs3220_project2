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
    ret = 0
    if imm['n'] is not None:
        ret = imm['n']
    else:
        ret = LABEL[imm['s']]
        if 'pc_rel' in ast:
            ret = (ret - (ast['addr']>>2) - 1)
    if ast['func'] == 'mvh':
        ret = ret >> 16
    return hex(ret & 0xFFFF)[2:].rjust(4, '0')

def writeOut(ast):
    global OUTPUT
    if 'comment' in ast['fmt']:
        addr = '0x' + hex(ast['addr'])[2:].rjust(8, '0')
        func_pre = ast['func_pre'] if 'func_pre' in ast else ''
        func_post = ast['func_post'] if 'func_post' in ast else ''
        func = func_pre + ast['func'] + func_post
        OUTPUT += '-- @ {0} : {1}\t{2}\n'.format(addr.lower(), func.upper(), ast['fmt']['comment'].upper())

    addr = hex(ast['addr'] >> 2)[2:].rjust(8, '0')
    func = hex(ast['func_val'])[2:]
    opcd = hex(ast['opcd'])[2:]

    fmt = ast['fmt']
    val = getReg(fmt, 'rd') + getReg(fmt, 'rs1') + getReg(fmt, 'rs2')
    val = val.ljust(2,'0') + getImm(ast)

    OUTPUT += '{0} : {1}{2}{3};\n'.format(addr.lower(), val.lower(), func.lower(), opcd.lower())

class asm_grammarSemantics(object):
    def orig(self, ast):
        global ADDR
        ADDR = ast
        return None

    def name(self, ast):
        global LABEL
        LABEL[ast[0]] = int(ast[1])
        return None

    def word(self, ast):
        global ADDR
        ast.update({'addr' : ADDR})
        ADDR += 4
        return ast

    def instruction(self, ast):
        global ADDR
        ast['addr'] = ADDR
        ADDR += 4
        return ast

    def alu(self, ast):
        func = ALU[ast['func'].lower()]
        if ast['func'].lower() == 'mvhi':
            del ast['func']
            ast['func'] = 'mvh'
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
        ast['opcd'] = 6 
        return ast

    def branch(self, ast):
        ast['pc_rel'] = True
        ast['func_pre'] = 'b'
        ast['func_val'] = 0
        ast['opcd'] = 6 
        return ast

    def jal(self, ast):
        ast['func_val'] = 0
        ast['opcd'] = 11 
        return ast

    #ToDo
    def pseudo(self, ast):
        global ADDR
        p = ast['func'].lower()
        ret = {}
        if p == 'br':
            ast['pc_rel'] = True
            ast['func_val'] = CMP['eq']
            ast['opcd'] = 6
            ast['fmt']['rs1'] = 'r6'
            ast['fmt']['rs2'] = 'r6'
            ast['addr'] = ADDR
        elif p == 'not':
            ast['func_val'] = ALU['nand']
            ast['opcd'] = 0
            ast['fmt']['rs1'] = ast['fmt']['rs']
            ast['fmt']['rs2'] = ast['fmt']['rs']
            del ast['fmt']['rs']
            ast['addr'] = ADDR
        elif p == 'ble' or p == 'bge':
            rs1 = ast['fmt']['rs1']
            rs2 = ast['fmt']['rs2']
            imm = ast['fmt']['imm']
            ret = [{
                        'addr':ADDR,
                        'func': p,
                        'func_val':CMP[p[1]+'te'],
                        'opcd':2,
                        'fmt': { 'comment':ast['fmt']['comment'], 'rd':'r6', 'rs1':rs1, 'rs2':rs2 }
                   },
                   {
                        'addr':(ADDR + 4),
                        'func': p,
                        'func_val':CMP['ne'] + 4,
                        'opcd':6,
                        'fmt': { 'rs1':'r6', 'imm':imm }
                   }]
            ast.clear()
            ast = ret
            ADDR += 4
        elif p == 'call':
            ast['addr'] = ADDR
            ast['func_val'] = 0 
            ast['opcd'] = 11
            ast['fmt']['rd'] = 'ra'
        elif p == 'ret':
            ast['addr'] = ADDR
            ast['func_val'] = 0 
            ast['opcd'] = 11
            ast['fmt'] = {'rd':'r9', 'rs1':'ra', 'imm':{'n':0, 's':None}, 'comment':''}
        elif p == 'jmp':
            ast['addr'] = ADDR
            ast['func_val'] = 0 
            ast['opcd'] = 11
            ast['fmt']['rd'] = 'r9'
        ADDR += 4
        return ast

    def label(self, ast):
        LABEL[ast['label']] = ADDR >> 2
        return None

    def fmt0(self, ast):
        ast.update({'comment' : '{0},{1},{2}'.format(ast['rd'], ast['rs1'], ast['rs2'])})
        return ast

    def fmt1(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0},{1},{2}'.format(ast['rd'], ast['rs1'], imm)})
        return ast

    def fmt2(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0},{1}'.format(ast['rd'], imm)})
        return ast

    def fmt3(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0},{1}({2})'.format(ast['rd'], imm, ast['rs1'])})
        return ast

    def fmt4(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0},{1}({2})'.format(ast['rs2'], imm, ast['rs1'])})
        return ast

    def fmt5(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0},{1},{2}'.format(ast['rs1'], ast['rs2'], imm)})
        return ast

    def fmt6(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0},{1}'.format(ast['rs1'], imm)})
        return ast

    def fmt7(self, ast):
        imm = ast['imm']['n'] if ast['imm']['s'] is None else ast['imm']['s']
        ast.update({'comment' : '{0}'.format(imm)})
        return ast

    def fmt8(self, ast):
        ast.update({'comment' : '{0},{1}'.format(ast['rd'], ast['rs'])})
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

#    print('AST:')
#    print(ast)
#    print()
#    print('JSON:')
#    print(json.dumps(ast, indent=2))
#    print()

    OUTPUT = 'WIDTH=32;\nDEPTH=2048;\nADDRESS_RADIX=HEX;\nDATA_RADIX=HEX;\nCONTENT BEGIN\n[00000000..0000000f] : DEAD;\n'
    for s in ast:
        if 'word' in s:
            continue
        writeOut(s)
    OUTPUT += '[{0}..07ff] : DEAD;\nEND;\n'.format(hex(ADDR>>2)[2:].rjust(4, '0'))
   
    with open(filename[0:filename.find('.')] + '.mif', 'w') as f:
        f.writelines(OUTPUT)

if __name__ == '__main__':
    import argparse
    import string
    import sys

    parser = argparse.ArgumentParser(description="Simple parser for asm_grammar.")
    parser.add_argument('file', metavar="FILE", help="the input file to parse")
    args = parser.parse_args()

    main(args.file)
