import sys
from Rom import LocalRom
from Settings import Settings
from pathlib import Path
import pprint
import os
from enum import Enum
import copy

def str_hex(val):
    return "0x" + str(hex(val))[2:].zfill(16)

class Arg():

    def __init__(self, name, func):
        self.name = name
        self.func = func

    def __str__(self):
        return self.name

class Opcode():
    
    def __init__(self, name, check_hex, *args, is_data=False):
        self.args = args
        self.name = name
        self.check_hex = list(check_hex)
        self.is_data = is_data

    def copy(self):
        return copy.deepcopy(self)

    def load_data(self, data):
        self.raw_data = data
        self.is_data = False

        try:
            hex(data)
            str_data = list(str(hex(data))[2:].zfill(16))
            for i in range(0, len(self.check_hex)):
                if '0' <= self.check_hex[i]  <= '9':
                    if self.check_hex[i] != str_data[i]:
                        self.is_data = True
                        break
        except TypeError:
            str_data = [j for i in [list(hex(d)[2:].zfill(16)) for d in data] for j in i]
            for i in range(0, len(self.check_hex)):
                if '0' <= self.check_hex[i]  <= '9':
                    if self.check_hex[i] != str(hex(data[i % 16]))[i+2]:
                        self.is_data = True
                        break
        values = []
        for a in self.args:
            values.append(a.func(data))
        copy = self.copy()
        copy.values = values
        copy.__dict__.update({self.args[i].name: values[i] for i in range(0, len(values))})
        return copy

    def __str__(self):
        str_args = ""
        for i in range(0, len(self.args)):
            str_args += str(self.args[i].name)
            str_args += ' = '
            try:
                str_args += str(hex(self.values[i]))
            except Exception:
                str_args += str(self.values[i])
            if i != len(self.args) - 1:
                str_args += ", "
        return (self.name + "(" + str_args + ")" ) if not self.is_data else "-- Data -- 0x" + str(hex(self.raw_data))[2:].zfill(16)

def check_hex(val, check):
    str_data = list(str(hex(val))[2:].zfill(16))
    for i in range(0, len(check)):
        if '0' <= check[i]  <= '9':
            if check[i] != str_data[i]:
                return True
                break
    return False


def mask(x, arg):
    val = 0
    output_mask = 0xFF
    input_mask = 0x1
    first_mask = -1
    for i in range(0, 8):
        if arg & input_mask != 0:
            val = val | output_mask
            if first_mask == -1:
                first_mask = i
        input_mask = input_mask << 1
        output_mask = output_mask << 8
    x = x & val
    x = x >> first_mask * 8
    return x

def get_objectfile_data(file, rom):

    all_data = rom.read_bytes(file.start, file.end - file.start)
    iterator = iter(all_data)
    line = 0

    opcodes = []
    raw_data = []
    for address in range(file.start, file.end, 4):
        
        data = (rom.read_int32(address) << 32) | rom.read_int32(address+4)
        code = mask(data, 0x80)

        if code in opcode_data:
            if(code in [0xE4, 0xE5]): #TODO
                line += 1
                opcode = None
                raw = data
                continue
                multi_line = [data]
                multi_line.append( next(iterator))
                multi_line.append( next(iterator))
                opcode.load_data(multi_line)
                raw = multi_line
                line += 3
            elif(code == 7):
                code = 6
                opcode_raw = opcode_data[code]
                opcode = opcode_raw.load_data(data)
                raw = data
                line += 1
            else:
                opcode_raw = opcode_data[code]
                opcode = opcode_raw.load_data(data)
                raw = data
                line += 1
        else:
            line += 1
            opcode = None
            raw = data

        opcodes.append(opcode)
        raw_data.append(None if raw == None else raw)

    last_vertex = 0

    for line, opcode in enumerate(opcodes):
        if opcode != None and opcode.name == "gsSPVertex" and not opcode.is_data and mask(opcode.vaddr, 0x08) == 0x06:
            start_offset = int(mask(opcode.vaddr, 0x07) / 8)
            for data_line in range(start_offset, start_offset + opcode.numv*2):
                opcodes[data_line] = None
                last_vertex = line

    return (opcodes, raw_data, last_vertex)

def clear_renders(file, rom, opcodes=None):
    if opcodes == None:
        opcodes, _, _ = get_objectfile_data(file, rom)
    line = 0
    for i, opcode in enumerate(opcodes):
        if opcode != None and not opcode.is_data and (opcode.name == "gsSP1Triangle" or opcode.name == "gsSP2Triangle"):
            opcodes[i] = opcode_data[0xE0]
            rom.write_int32(file.start + line * 4, 0xE0000000)
            rom.write_int32(file.start + line * 4 + 4, 0x00000000)
        line += 1

opcode_data = {
        0: Opcode("gsDPNoOpTag", "00000000tttttttt", 
            Arg("tag",      lambda x: mask(x, 0x0F))),
        1: Opcode("gsSPVertex", "010nn0aavvvvvvvv",
            Arg("vaddr",    lambda x: mask(x, 0x0F)),
            Arg("numv",     lambda x: mask(x, 0x60) >> 4),
            Arg("vbidx",    lambda x: (mask(x, 0x10) >> 1) - (mask(x, 0x60) >> 8))),
        2: Opcode("gsSPModifyVertex", "02wwnnnnvvvvvvvv",
            Arg("vbidx",    lambda x: mask(x, 0x30)/2), 
            Arg("where",    lambda x: mask(x, 0x40)), 
            Arg("val",      lambda x: mask(x, 0x0F))),
        3: Opcode("gsSPCullDisplayList", "0300vvvv0000wwww",
            Arg("vfirst",   lambda x: mask(x, 0x30)/2), 
            Arg("vlast",    lambda x: mask(x, 0x03)/2)),
        5: Opcode("gsSP1Triangle", "05aabbcc00000000",
            Arg("v0",       lambda x: mask(x, 0x40)/2), 
            Arg("v1",       lambda x: mask(x, 0x20)/2), 
            Arg("v2",       lambda x: mask(x, 0x10)/2)),
        6: Opcode("gsSP2Triangle", "06aabbcc00ddeeff",
            Arg("v00",      lambda x: mask(x, 0x40)/2), 
            Arg("v01",      lambda x: mask(x, 0x20)/2), 
            Arg("v02",      lambda x: mask(x, 0x10)/2),
            Arg("v10",      lambda x: mask(x, 0x04)/2),
            Arg("v11",      lambda x: mask(x, 0x02)/2), 
            Arg("v12",      lambda x: mask(x, 0x01)/2)),

        0xD3: Opcode("G_SPECIAL_3", "D3??????????????"),
        0xD4: Opcode("G_SPECIAL_2", "D2??????????????"),
        0xD5: Opcode("G_SPECIAL_1", "D1??????????????"),

        0xD7: Opcode("gsSPTexture", "D700BBnnsssstttt",
            Arg("scaleS",   lambda x: mask(x, 0x0C)),
            Arg("scaleT",   lambda x: mask(x, 0x03)),
            Arg("level",    lambda x: (x & 0x20) >> 3),
            Arg("tile",     lambda x: (x & 0x20) & 0x38),
            Arg("on",       lambda x: mask(x, 0x20))),
        0xD8: Opcode("gsSPPopMatrixN", "D8380002aaaaaaaa",
            Arg("which",    lambda x: 0),
            Arg("num",      lambda x: mask(x, 0x0F) * 64)),
        0xD9: Opcode("gsSPGeomentryMode", "D9ccccccssssssss",
            Arg("clearbits",lambda x: ~mask(x, 0x70)),
            Arg("setbits",  lambda x: mask(x, 0x0F))),
        0xDA: Opcode("gsSPMatrix", "DA3800ppmmmmmmmm",
            Arg("mtxaddr",  lambda x: mask(x, 0x0F)),
            Arg("params",   lambda x: (mask(x, 0x10)))),
        0xDB: Opcode("gsMoveWd","DBiioooodddddddd",
            Arg("index",    lambda x: (mask(x, 0x40))),
            Arg("offset",   lambda x: mask(x, 0x30)),
            Arg("data",     lambda x: mask(x, 0x0F))),
        0xDC: Opcode("gsMoveMem", "DCnnooiiaaaaaaaa",
            Arg("size",     lambda x: (((mask(x, 0x40) >> 3) + 1) * 8)),
            Arg("index",    lambda x: (mask(x, 0x10))),
            Arg("offset",   lambda x: mask(x, 0x20) * 8),
            Arg("address",  lambda x: mask(x, 0x0F))),
        0xDE: Opcode("gsSPBranch/DisplayList", "DEpp0000dddddddd",
            Arg("flag",     lambda x: mask(x, 0x40)),
            Arg("address",  lambda x: mask(x, 0x0F))),
        0xDF: Opcode("gsSPEndDisplayList", "DF00000000000000"),
        0xE0: Opcode("gsSpNoOp", "E000000000000000"),
        0xE1: Opcode("gsDPWord", "E1000000hhhhhhhh",
            Arg("wordhi",   lambda x: mask(x, 0x0F))),
        0xE2: Opcode("gsSPSetOtherMode", "E200ssnndddddddd",
            Arg("const",    lambda x: 0xE2),
            Arg("shift",    lambda x: 32 - mask(x, 0x02) - (mask(x, 0x01) - 1)),
            Arg("length",   lambda x: mask(x, 0x01) + 1),
            Arg("data",    lambda x: mask(x, 0x0F))),
        0xE3: Opcode("gsSPSetOtherMode", "E300ssnndddddddd",
            Arg("const",    lambda x: 0xE3),
            Arg("shift",   lambda x: 32 - mask(x, 0x02) - (mask(x, 0x01) - 1)),
            Arg("length",   lambda x: mask(x, 0x01) + 1),
            Arg("data",     lambda x: mask(x, 0x0F))),
        0xE4: Opcode("gsSPTextireRectangle", "E4xxxyyy0iXXXYYYE1000000ssssttttF1000000ddddeeee",
            Arg("ulx",      lambda x: mask(x[0], 0x06) >> 24),
            Arg("uly",      lambda x: mask(x[0], 0x03) & 0xFFF),
            Arg("lrx",     lambda x: mask(x[0], 0x60) >> 24),
            Arg("lry",      lambda x: mask(x[0], 0x30) & 0xFFF),
            Arg("tile",     lambda x: mask(x[0], 0x08)),
            Arg("uls",      lambda x: mask(x[1], 0x0C)),
            Arg("ult",      lambda x: mask(x[1], 0x03)),
            Arg("dsdx",     lambda x: mask(x[2], 0x0C)),
            Arg("dtdy",     lambda x: mask(x[2], 0x03))),
        0xE5: Opcode("gsSPTextireRectangleFlip", "E4xxxyyy0iXXXYYYE1000000ssssttttF1000000ddddeeee",
            Arg("ulx",      lambda x: mask(x[0], 0x06) >> 24),
            Arg("uly",      lambda x: mask(x[0], 0x03) & 0xFFF),
            Arg("lrx",      lambda x: mask(x[0], 0x60) >> 24),
            Arg("lry",      lambda x: mask(x[0], 0x30) & 0xFFF),
            Arg("tile",     lambda x: mask(x[0], 0x08)),
            Arg("uls",      lambda x: mask(x[1], 0x0C)),
            Arg("ult",      lambda x: mask(x[1], 0x03)),
            Arg("dsdx",     lambda x: mask(x[2], 0x0C)),
            Arg("dtdy",     lambda x: mask(x[2], 0x03))),
        0xE6: Opcode("gsDPLoadSync", "E600000000000000"),
        0xE7: Opcode("gsDPPipeSync", "E700000000000000"),
        0xE8: Opcode("gsDPTileSync", "E800000000000000"),
        0xE9: Opcode("gsDPFullSync", "E900000000000000"),
        0xEA: Opcode("gsDPSetKeyGB", "EAwwwxxxccssddtt",
            Arg("centerG",  lambda x: mask(x, 0x08)),
            Arg("scaleG",   lambda x: mask(x, 0x04)),
            Arg("widthG",   lambda x: mask(x, 0x60) >> 8),
            Arg("centerB",  lambda x: mask(x, 0x02)),
            Arg("scaleB",   lambda x: mask(x, 0x01)),
            Arg("widthB",   lambda x: mask(x, 0x30) & 0xFFF)),
        0xEB: Opcode("gsDPSetKeyR", "EB0000000wwwccss",
            Arg("centerR",  lambda x: mask(x, 0x02)),
            Arg("widthR",   lambda x: mask(x, 0x0C)),
            Arg("scaleR",   lambda x: mask(x, 0x01))),
        0xF2: Opcode("gsDPSetTileSize", "F2sssttt0iuuuvvv",
            Arg("tile",     lambda x: mask(x, 0x08)),
            Arg("uls",      lambda x: mask(x, 0x60) >> 4),
            Arg("ult",      lambda x: mask(x, 0x30) & 0xFFF),
            Arg("lrs",      lambda x: mask(x, 0x06) >> 4),
            Arg("lrt",      lambda x: x & 0xFFF)),
        0xF3: Opcode("gsDPLoadBlock", "F3sssttt0iuuuvvv",
            Arg("tile",     lambda x: mask(x, 0x08)),
            Arg("uls",      lambda x: mask(x, 0x60) >> 4),
            Arg("ult",      lambda x: mask(x, 0x30) & 0xFFF),
            Arg("texels",   lambda x: mask(x, 0x06) >> 4),
            Arg("dxt",      lambda x: x & 0xFFF)),
        0xF4: Opcode("gsDPLoadTile", "F4sssttt0iuuuvvv",
            Arg("tile",     lambda x: mask(x, 0x08)),
            Arg("uls",      lambda x: mask(x, 0x60) >> 4),
            Arg("ult",      lambda x: mask(x, 0x30) & 0xFFF),
            Arg("lrs",      lambda x: mask(x, 0x06) >> 4),
            Arg("lrt",      lambda x: x & 0xFFF)),
        0xF5: Opcode("gsDPSetTile", "F5FINNMM0TPCSSBU",
            Arg("fmt",      lambda x: (x & 0x00E0000000000000) >> (13*4+1)),
            Arg("siz",      lambda x: (x & 0x0018000000000000) >> (12*4+3)),
            Arg("line",     lambda x: (x & 0x0003FE0000000000) >> (10*4+1)),
            Arg("tmem",     lambda x: (x & 0x000001FF00000000) >> ( 8*4+0)),
            Arg("tile",     lambda x: (x & 0x0000000007000000) >> ( 6*4+0)),
            Arg("palette",  lambda x: (x & 0x0000000000F00000) >> ( 5*4+0)),
            Arg("cmT",      lambda x: (x & 0x00000000000C0000) >> ( 4*4+2)),
            Arg("maskT",    lambda x: (x & 0x000000000003C000) >> ( 3*4+2)),
            Arg("shiftT",   lambda x: (x & 0x0000000000003C00) >> ( 2*4+2)),
            Arg("cmS",      lambda x: (x & 0x0000000000000300) >> ( 2*4+0)),
            Arg("maskS",    lambda x: (x & 0x00000000000000F0) >> ( 1*4+0)),
            Arg("shiftS",   lambda x: (x & 0x000000000000000F) >> ( 0*4+0))),
        0xF7: Opcode("gsDPSetFillColor", "F7000000cccccccc",
            Arg("color",    lambda x: mask(x, 0x0F))),
        0xF8: Opcode("gsDPSetFogColor", "F8000000rrggbbaa",
            Arg("R",        lambda x: mask(x, 0x08)),
            Arg("G",        lambda x: mask(x, 0x04)),
            Arg("B",        lambda x: mask(x, 0x02)),
            Arg("A",        lambda x: mask(x, 0x01))),
        0xF9: Opcode("gsDPBlendColor", "F9000000rrggbbaa",
            Arg("R",        lambda x: mask(x, 0x08)),
            Arg("G",        lambda x: mask(x, 0x04)),
            Arg("B",        lambda x: mask(x, 0x02)),
            Arg("A",        lambda x: mask(x, 0x01))),
        0xFA: Opcode("gsDPSetPrimColor", "FA00mmffrrggbbaa",
            Arg("minlevel", lambda x: mask(x, 0x20)),
            Arg("lodfrac",  lambda x: mask(x, 0x10)),
            Arg("R",        lambda x: mask(x, 0x08)),
            Arg("G",        lambda x: mask(x, 0x04)),
            Arg("B",        lambda x: mask(x, 0x02)),
            Arg("A",        lambda x: mask(x, 0x01))),
        0xFB: Opcode("gsDPSetEnvColor", "FB000000rrggbbaa",
            Arg("R",        lambda x: mask(x, 0x08)),
            Arg("G",        lambda x: mask(x, 0x04)),
            Arg("B",        lambda x: mask(x, 0x02)),
            Arg("A",        lambda x: mask(x, 0x01))),
        0xFC: Opcode("gsDPSetTile", "FCACZXEGFVTDWHUS",
            Arg("a0",    lambda x: (x & 0x00F0000000000000) >> (13*4+0)),
            Arg("b0",    lambda x: (x & 0x00000000F0000000) >> ( 7*4+0)),
            Arg("c0",    lambda x: (x & 0x000F100000000000) >> (11*4+3)),
            Arg("d0",    lambda x: (x & 0x0000000000038000) >> ( 3*4+3)),
            Arg("Aa0",   lambda x: (x & 0x0000700000000000) >> (11*4+0)),
            Arg("Ab0",   lambda x: (x & 0x0000000000007000) >> ( 3*4+0)),
            Arg("Ac0",   lambda x: (x & 0x00000E0000000000) >> (10*4+1)),
            Arg("Ad0",   lambda x: (x & 0x0000000000000E00) >> ( 2*4+1)),
            Arg("a1",    lambda x: (x & 0x000001E000000000) >> ( 9*4+1)),
            Arg("b1",    lambda x: (x & 0x000000000F000000) >> ( 6*4+0)),
            Arg("c1",    lambda x: (x & 0x0000001F00000000) >> ( 8*4+0)),
            Arg("d1",    lambda x: (x & 0x00000000000001C0) >> ( 1*4+2)),
            Arg("Aa1",   lambda x: (x & 0x0000000000E00000) >> ( 5*4+1)),
            Arg("Ab1",   lambda x: (x & 0x0000000000000038) >> ( 0*4+3)),
            Arg("Ac1",   lambda x: (x & 0x00000000001C0000) >> ( 4*4+2)),
            Arg("Ad1",   lambda x: (x & 0x0000000000000003) >> ( 0*4+0))),
        0xFD: Opcode("gsDPSetTextureImage", "FDFS0wwwiiiiiiii",
            Arg("fmt",      lambda x: mask(x, 0x40) >> 5),
            Arg("siz",      lambda x: (mask(x, 0x40) >> 3) & 0x3),
            Arg("width",    lambda x: mask(x, 0x30)+1),
            Arg("imgaddr",  lambda x: mask(x, 0x0F))),
        0xFE: Opcode("gsDPSetDepthImage", "FE000000iiiiiiii",
            Arg("imgaddr",  lambda x: mask(x, 0x0F))),
        0xFF: Opcode("gsDPSetColorImage", "FFFS0wwwiiiiiiii",
            Arg("fmt",      lambda x: mask(x, 0x40) >> 5),
            Arg("siz",      lambda x: (mask(x, 0x40) >> 3) & 0x3),
            Arg("width",    lambda x: mask(x, 0x30)+1),
            Arg("imgaddr",  lambda x: mask(x, 0x0F)))



}
