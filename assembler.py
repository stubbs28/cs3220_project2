import math
from asm_grammar import asm_grammarParser

ALUR = ['add',     'sub',      '',         '',
        'and',     'or',       'xor',      '',
        '',        '',         '',         '',
        'nand',    'nor',      'xnor',     '']

ALUI = [a if a == '' else a + 'i' for a in ALUR]
ALUI[11] = 'mvhi'

CMPR = ['f',       'eq',       'lt',       'lte',
        '',        '',         '',         '',
        't',       'ne',       'gte',      'gt',
        '',        '',         '',         '']

CMPI = [a if a == '' else a + 'i' for a in CMPR]

BRANCH = [a if a == '' else 'b' + a for a in CMPR]
for x in range(1,4):
    BRANCH[x + 4] = BRANCH[x] + 'z'
    BRANCH[x + 12] = BRANCH[x + 8] + 'z'

OPCODE = [('alur',ALUR),    ('',None),      ('cmpr',CMPR),      ('',None),
        ('',None),          ('sw',None),    ('branch',BRANCH),  ('',None),
        ('alui',ALUI),      ('lw',None),    ('cmpi',CMPI),      ('jal',None),
        ('',None),          ('',None),      ('',None),          ('',None)]

REG = [['r' + str(x)] for x in range(16)]
for x in range(4):
    REG[x] += ['a' + str(x)]
for x in range(2):
    REG[x + 4] += ['t' + str(x)]
for x in range(3):
    REG[x + 6] += ['s' + str(x)]
REG[12] += ['gp']
REG[13] += ['fp']
REG[14] += ['sp']
REG[15] += ['ra']

PC = 0
LABEL = {}

def getReg(fmt, key):
    x = 0
    key = key.lower()
    if key in fmt:
        reg = fmt[key].lower()
        for num in REG:
            if reg in num:
                return '{0:x}'.format(x)
            x += 1
    return ''

def getImm(ast):
    global PC
    if not 'imm' in ast['fmt']:
        return None
    ret = 0
    imm = ast['fmt']['imm']
    if imm['n'] is not None:
        ret = imm['n']
    else:
        ret = LABEL[imm['s']]
        if 'pcrel' in ast:
            ret = ret - ast['pc'] - 1
        elif ast['instr'].lower() == 'mvhi':
            ret = ret >> 16
    if ast['instr'] == 'word':
        return '{0:08x}'.format(ret & 0xFFFFFFFF)
    return '{0:04x}'.format(ret & 0xFFFF)

def getOpcode(group, instr):
    global OPCODE
    lower = 0
    upper = 0
    for g,funcs in OPCODE:
        if group == g:
            if funcs is not None:
                for f in funcs:
                    if instr.lower() == f:
                        break
                    upper += 1
            break
        lower += 1
    return '{0:02x}'.format((upper << 4) | lower)

def writeComment(ast):
    memaddr = (ast['pc'] << 2) & 0xffffffff
    return '-- @ {0:#010x} : {1}\t{2}\n'.format(memaddr, ast['instr'].upper(), ast['fmt']['comment'].upper())

def writeMem(ast):
    memaddr = ast['pc'] & 0xffffffff
    fmt = ast['fmt']
    val = getReg(fmt, 'rd') + getReg(fmt, 'rs1') + getReg(fmt, 'rs2')
    imm = getImm(ast)
    val = val.ljust(6,'0') if imm is None else val.ljust(2,'0') + imm
    return '{0:08x} : {1}{2};\n'.format(memaddr, val, ast['opcode'])

class asm_grammarSemantics(object):
    def orig(self, ast):
        global PC
        oldpc = PC
        PC = (ast >> 2)
        diff = PC - oldpc - 1
        if diff >= 0:
            return {'dead':(oldpc, diff)}
        return None

    def name(self, ast):
        global LABEL
        LABEL[ast[0]] = int(ast[1])
        return None

    def word(self, ast):
        global PC
        ret = {'word':{'pc':PC,'instr':'word','fmt':{'imm':ast['word']}}}
        PC += 1
        return ret

    def instruction(self, ast):
        global PC
        ast['pc'] = PC
        PC += 1
        return ast

    def alui(self, ast):
        ast['opcode'] = getOpcode('alui', ast['instr'])
        return ast

    def alur(self, ast):
        global ALUR
        ast['opcode'] = getOpcode('alur', ast['instr'])
        return ast

    def load(self, ast):
        ast['opcode'] = getOpcode('lw', ast['instr'])
        return ast

    def store(self, ast):
        ast['opcode'] = getOpcode('sw', ast['instr'])
        return ast

    def cmpi(self, ast):
        ast['opcode'] = getOpcode('cmpi', ast['instr'])
        return ast

    def cmpr(self, ast):
        ast['opcode'] = getOpcode('cmpr', ast['instr'])
        return ast

    def branchz(self, ast):
        ast['pcrel'] = True
        ast['opcode'] = getOpcode('branch', ast['instr'])
        return ast

    def branch(self, ast):
        ast['pcrel'] = True
        ast['opcode'] = getOpcode('branch', ast['instr'])
        return ast

    def jal(self, ast):
        ast['opcode'] = getOpcode('jal', ast['instr'])
        return ast

    #ToDo
    def pseudo(self, ast):
        global PC
        p = ast['instr'].lower()
        ret = {}
        ast['pc'] = PC
        if p == 'br':
            ast['pcrel'] = True
            ast['opcode'] = getOpcode('branch', 'beq')
            ast['fmt']['rs1'] = 'r6'
            ast['fmt']['rs2'] = 'r6'
        elif p == 'not':
            ast['opcode'] = getOpcode('alur', 'nand')
            ast['fmt']['rs1'] = ast['fmt']['rs']
            ast['fmt']['rs2'] = ast['fmt']['rs']
            del ast['fmt']['rs']
        elif p == 'ble' or p == 'bge':
            rs1 = ast['fmt']['rs1']
            rs2 = ast['fmt']['rs2']
            imm = ast['fmt']['imm']
            ret = [{
                        'pc':PC,
                        'instr': p,
                        'opcode': getOpcode('cmpr', p[1] + 'te'),
                        'fmt': { 'comment':ast['fmt']['comment'], 'rd':'r6', 'rs1':rs1, 'rs2':rs2 }
                   },
                   {
                        'pcrel': True,
                        'pc':(PC + 1),
                        'instr': p,
                        'opcode':getOpcode('branch', 'bnez'),
                        'fmt': { 'rs1':'r6', 'imm':imm }
                   }]
            ast.clear()
            ast = ret
            PC += 1
        elif p == 'call':
            ast['opcode'] = getOpcode('jal', None)
            ast['fmt']['rd'] = 'ra'
        elif p == 'ret':
            ast['opcode'] = getOpcode('jal', None)
            ast['fmt'] = {'rd':'r9', 'rs1':'ra', 'imm':{'n':0, 's':None}, 'comment':''}
        elif p == 'jmp':
            ast['opcode'] = getOpcode('jal', None)
            ast['fmt']['rd'] = 'r9'
        PC += 1
        return ast

    def label(self, ast):
        LABEL[ast['label']] = PC
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
        return int(ast, 16)

    def dec(self, ast):
        return int(ast)

    def __default__(self, ast):
        return ast

def main(filename):
    global OUTPUT, PC
    import json
    with open(filename) as f:
        text = f.read()
    parser = asm_grammarParser(parseinfo=False)
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

    OUTPUT = 'WIDTH=32;\nDEPTH=2048;\nADDRESS_RADIX=HEX;\nDATA_RADIX=HEX;\nCONTENT BEGIN\n'
    for s in ast:
        if 'dead' in s:
            d = s['dead']
            if d[1] == 0:
                OUTPUT += '{0:08x} : DEAD;\n'.format(d[0])
            else:
                if d[0] == 0:
                    OUTPUT += '[{0:08x}..{1:08x}] : DEAD;\n'.format(d[0], d[1])
                else:
                    OUTPUT += '[{0:04x}..{1:04x}] : DEAD;\n'.format(d[0], d[0] + d[1])
            continue
        if 'word' in s:
            w = s['word']
            OUTPUT += '{0} : {1}'.format(w['pc'], getImm(w))
            print('{0:08x} : {1}'.format(w['pc'], getImm(w)))
            continue
        OUTPUT += writeComment(s)
        OUTPUT += writeMem(s)
    OUTPUT += '[{0}..07ff] : DEAD;\nEND;\n'.format('{0:04x}'.format(PC))
   
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
