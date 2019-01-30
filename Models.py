from ModelParser import clear_renders, get_objectfile_data
from ObjFileParser import get_displaylist_data, load_obj
from MQ import update_dmadata

def write_model_to_rom(path, file, rom):

    data, raw_data, vertex_data_end = get_objectfile_data(file, rom) #Pa
    clear_renders(file, rom, data) #Remove all render operations in the object file's display lists

    #file.relocate(rom)

    new_vertices = load_obj(path) #Load and parse new obj file
    v_data, r_data = get_displaylist_data(new_vertices, scale=0x50) #Convert the obj file object data into binary data

    def to_bytes(value, num_bytes):
        mask = 0xFF << ((num_bytes-1)*8)
        b = []
        for _ in range(0, num_bytes):
            b.append((mask & value) >> ((num_bytes-1)*8) )
            value = value << 8
        return b

    def gsSPVertex(vaddr, numv, vbidx):
        out = 0x01 << (7*8)
        out = out | ((numv & 0xFF) << (11*4))
        aa = ((vbidx + numv) & 0x7F) << 1
        out = out | (aa << (4*8))
        out = out | (vaddr & 0x00FFFFFF)
        out = out | (0x06000000)
        return out

    # Start filling vertex data in the original locations, then fill at the end of the file if we run out of space
    
    group = 0
    v_write = file.start
    #r_write = file.start + 0x0778
    r_write = file.end - 16
    r_data_len = sum(len(d)+1 for d in r_data) * 8
    while(group < len(v_data) and (vertex_data_end * 16 + file.start) - v_write > len(v_data[group]))*16:
        for i, vertex in enumerate(v_data[group]):
            rom.write_bytes(v_write + i * 16, to_bytes(vertex, 16))
            print(str(to_bytes(vertex, 16)) + " -> " + str(hex(v_write + i)))
        
        load = gsSPVertex(v_write - file.start, len(v_data[group]), 0)

        rom.write_bytes(r_write, to_bytes(load, 8))
        for i, v_draw in enumerate(r_data[group]):
            rom.write_bytes(r_write + (i+1)*8, to_bytes(v_draw, 8))
            print(str(to_bytes(v_draw, 8)) + " -> " + str(hex(r_write + (i+1)*8)))

        v_write += len(v_data[group]) * 16
        r_write += (len(r_data[group])+1) * 8
        group += 1

    v_write = file.end + r_data_len
    end_group = group

    for group in range(end_group, len(v_data)):
        for i, vertex in enumerate(v_data[group]):
            rom.write_bytes(v_write + i * 16, to_bytes(vertex, 16))
            print(str(to_bytes(vertex, 16)) + " -> " + str(hex(v_write + i)))
        
        load = gsSPVertex(v_write - file.start, len(v_data[group]), 0)

        rom.write_bytes(r_write, to_bytes(load, 8))
        for i, v_draw in enumerate(r_data[group]):
            rom.write_bytes(r_write + (i+1)*8, to_bytes(v_draw, 8))
            print(str(to_bytes(v_draw, 8)) + " -> " + str(hex(r_write + (i+1)*8)))

        v_write += len(v_data[group]) * 16
        r_write += (len(r_data[group])+1) * 8


    rom.write_bytes(r_write, [0xDF, 0, 0, 0, 0, 0, 0, 0])
    rom.write_bytes(r_write + 8, [0, 0, 0, 0, 0, 0, 0, 0])

    #file.end += 16
    file.end = max(r_write, file.end)
    update_dmadata(rom, file)
    
    print("File start: " + hex(file.start))
    print("File end: " + hex(file.end))


