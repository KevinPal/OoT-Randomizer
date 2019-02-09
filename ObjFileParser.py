
try:
    import pywavefront
except ImportError as e:
    print("You need to pywavefront module for parsing objects. run pip install PyWavefront")
    raise e

def hexstr(val, minlen):
    return str(hex(int(val)))[2:].zfill(minlen)

class Vector4f():

    def __init__(self, x, y, z, w):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def __str__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ", " + str(self.w) + ")"

    def __eq__(self, other):
        return other != None and type(self) == type(other) and self.x == other.x and self.y == other.y and self.z == other.z and self.w == other.w

class Vector3f():

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def to_int64(self, scale=1):
        out = 0
        out = out | ((int(self.x*scale) & 0xFFFF) << 48)
        out = out | ((int(self.y*scale) & 0xFFFF) << 32)
        out = out | ((int(self.z*scale) & 0xFFFF) << 16)
        return out

    def to_int32(self, scale=1):
        out = 0
        out = out | ((int(self.x*scale) & 0xFF) << 24)
        out = out | ((int(self.y*scale) & 0xFF) << 16)
        out = out | ((int(self.z*scale) & 0xFF) << 8)
        return out
    def __str__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def __eq__(self, other):
        return other != None and type(self) == type(other) and self.x == other.x and self.y == other.y and self.z == other.z

class Vector2f():

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_2fixed10_5(self):
        out = 0
        out = out | (int((self.x * 1023.96875*2-1023.96875) * 32) & 0xFFFF) << 16
        out = out | (int((self.y * 1023.96875*2-1023.96875) * 32) & 0xFFFF)
        return out

    def __str__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ")"

    def __eq__(self, other):
        return other != None and type(self) == type(other) and self.x == other.x and self.y == other.y


class Vertex():

    def __init__(self, coordinate=None, texture=None, normal=None, color=None):
        self.coordinate = coordinate
        self.texture = texture
        self.normal = normal
        self.color = color


    def update_vertex(self, vector, v_type):
        #Type 0 for coordinates, 1 for normals, 2 for textures, 3 for colors
        if v_type == 0:
            self.coordinate = vector
        elif v_type == 1:
            self.normal = vector
        elif v_type == 2:
            self.texture = vector
        elif v_type == 3:
            self.color = vector

    def to_F3DZEX(self, scale=1):
        out = 0
        out = out | (self.coordinate.to_int64(scale) << 64)
        out = out | ((self.texture.to_2fixed10_5() << 32) if self.texture != None else 0)
        alpha = 0xFF if self.color == None or type(self) != "Vector4f" else (self.color.w & 0xFF)
        shading = self.normal
        shading = Vector3f(shading.x, shading.y, shading.z) 
        out = out | shading.to_int32(127)
        out = out | alpha
        return out

    def __str__(self):
        out = ""
        if self.coordinate != None:
            out += " Coordinate: " + str(self.coordinate)
        if self.normal != None:
            out += " Normal: " + str(self.normal)
        if self.texture != None:
            out += " Texture: " + str(self.texture)
        if self.color != None:
            out += " Color: " + str(self.color)

        return out

    def __eq__(self, other):
        return other != None and self.coordinate == other.coordinate and self.normal == other.normal and self.texture == other.texture and self.color == other.color

class Face():
    
    def __init__(self, vindx1, vindx2, vindx3):
        self.vindx1 = vindx1
        self.vindx2 = vindx2
        self.vindx3 = vindx3


    def to_F3DZEX_05(self):
        out = (0x05 << 7*8)
        out = out | ((self.vindx1*2) << (6*8))
        out = out | ((self.vindx2*2) << (5*8))
        out = out | ((self.vindx3*2) << (4*8))
        return out

    def to_F3DZEX_06(self, face):
        face1out = self.to_F3DZEX_05() & ~(0xFF << (7*8))
        face1out = face1out | (0x06 << (7*8))
        face2out = face.to_F3DZEX_05() & ~(0xFF << (7*8))
        return face1out | (face2out >> (4*8))


    def __str__(self):
        return "(" + str(self.vindx1) + ", " + str(self.vindx2) + ", " + str(self.vindx3) + ")"


def load_obj(path):
    try:
        scene = pywavefront.Wavefront(path)
    except FileNotFoundError as e:
        print("Could not find file: " + path);
        raise e

    vertices = []

    # Iterate vertex data collected in each material
    for name, material in scene.materials.items():
        # Contains the vertex format (string) such as "T2F_N3F_V3F"
        vertex_format_str = material.vertex_format.split("_")
        #Type 0 for coordinates, 1 for normals, 2 for textures, 3 for colors
        vertex_format = []
        for v_format in vertex_format_str:
            if v_format[0] == 'V':
                d_type = 0
            elif v_format[0] == 'N':
                d_type = 1
            elif v_format[0] == 'T':
                d_type = 2
            elif v_format[0] == 'C':
                d_type = 3
    
            d_len = int(v_format[1])

            vertex_format.append( (d_type, d_len))
            
        vertex_len = sum(v[1] for v in vertex_format)
        for index in range(0, int(len(material.vertices) / vertex_len)):
            vertex = Vertex()
            offset = 0
            for d_type in vertex_format:
                if d_type[1] == 4:
                    data = Vector3f(material.vertices[index * vertex_len + offset],
                            material.vertices[index * vertex_len + offset + 1],
                            material.vertices[index * vertex_len + offset + 2],
                            material.vertices[index * vertex_len + offset + 3])
                elif d_type[1] == 3:
                    data = Vector3f(material.vertices[index * vertex_len + offset],
                            material.vertices[index * vertex_len + offset + 1],
                            material.vertices[index * vertex_len + offset + 2])
                elif d_type[1] == 2:
                    data = Vector2f(material.vertices[index * vertex_len + offset],
                            material.vertices[index * vertex_len + offset + 1])

                offset += d_type[1]

                vertex.update_vertex(data, d_type[0])
            vertices.append(vertex)
    return vertices

def get_displaylist_data(vertices, scale=1):
    all_v_buffers = [[]]
    all_faces = [[]]
    for index in range(0, int(len(vertices)), 3):
        vbixs = [-2, -2, -2]
        for i in range(0, 3):
            v = vertices[index + i]
            try:
                v_index = all_v_buffers[-1].index(v)
                vbixs[i] = v_index
            except ValueError:
                if(len(all_v_buffers[-1]) >= 32):
                    all_v_buffers.append([])
                    all_faces.append([])
                    for j, old_vbidx in enumerate(vbixs):
                        if old_vbidx == -2:
                            all_v_buffers[-1].append(v)
                            vbixs[j] = len(all_v_buffers[-1]) - 1
                            break
                        else:
                            all_v_buffers[-1].append(all_v_buffers[-2][old_vbidx])
                            vbixs[j] = len(all_v_buffers[-1]) - 1
                else:
                    all_v_buffers[-1].append(v)
                    vbixs[i] = len(all_v_buffers[-1]) - 1
        print(vbixs)
        all_faces[-1].append( Face(*vbixs))

    vertex_buffer_data = []
    vertex_render_data = []

    for vertex_buffer in all_v_buffers:
        vertex_buffer_data.append([])
        for v in vertex_buffer:
            vertex_buffer_data[-1].append(v.to_F3DZEX(scale))

    for group_num, face_group in enumerate(all_faces):
        vertex_render_data.append([])
        for face_num in range(0, int(len(face_group)/2)):
            vertex_render_data[-1].append(face_group[face_num*2].to_F3DZEX_06(face_group[face_num*2+1]))
        if len(face_group) % 2 != 0:
            vertex_render_data[-1].append(face_group[-1].to_F3DZEX_05())


    return vertex_buffer_data, vertex_render_data
