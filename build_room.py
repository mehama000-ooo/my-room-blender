import bpy, bmesh, os, math, random, json
from mathutils import Matrix, Vector, Euler

bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(7)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
ROOT = scene.collection

W, D, H = 4.5, 5.0, 2.4
DIV = 1.8               # 커튼/파티션 라인 (x)

_cols = {}
def col(name):
    if name not in _cols:
        c = bpy.data.collections.new(name)
        ROOT.children.link(c)
        _cols[name] = c
    return _cols[name]

_mats = {}
def mat(name, rgba, rough=0.5, metal=0.0, emit=0.0, alpha=1.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit > 0:
        for nm in ("Emission Color", "Emission"):
            if nm in b.inputs:
                b.inputs[nm].default_value = rgba
                break
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    m.diffuse_color = rgba
    _mats[name] = m
    return m

def finish(name, bm, m, coll, loc=(0, 0, 0), smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    o.location = loc
    me.materials.append(m)
    col(coll).objects.link(o)
    return o

def box(name, x0, x1, y0, y1, z0, z1, m, coll):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=bm.verts)
    return finish(name, bm, m, coll, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))

def boxes(name, specs, m, coll):
    """여러 상자를 한 물체로 (specs: (x0,x1,y0,y1,z0,z1))"""
    bm = bmesh.new()
    for x0, x1, y0, y1, z0, z1 in specs:
        mtx = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)
    return finish(name, bm, m, coll)

def cyl(name, r, z0, z1, x, y, m, coll, segs=32, r2=None, axis='Z'):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=z1 - z0)
    o = finish(name, bm, m, coll, smooth=True)
    if axis == 'Z':
        o.location = (x, y, (z0 + z1) / 2)
    return o

def sphere(name, r, loc, m, coll, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
    o = finish(name, bm, m, coll, loc, smooth=True)
    o.scale = scale
    return o


# =============== 재질 (우드톤 + 베이지 리넨 + 크림) ===============
M = {
    "floor": mat("Floor_Light_Oak", (0.7, 0.56, 0.41, 1), 0.5),
    "wall": mat("Wall_Warm_Cream", (0.84, 0.79, 0.72, 1), 0.85),
    "oak": mat("Wood_Oak", (0.6, 0.42, 0.26, 1), 0.55),
    "oak_light": mat("Wood_Oak_Light", (0.72, 0.56, 0.38, 1), 0.55),
    "white": mat("Furniture_White", (0.93, 0.92, 0.89, 1), 0.4),
    "whitewash": mat("Wood_Whitewash", (0.85, 0.82, 0.77, 1), 0.7),
    "metal": mat("Metal_Black", (0.05, 0.05, 0.05, 1), 0.3, 0.9),
    "silver": mat("Metal_Silver", (0.8, 0.8, 0.82, 1), 0.2, 1.0),
    "mirror": mat("Mirror_Glass", (0.92, 0.93, 0.95, 1), 0.02, 1.0),
    "linen": mat("Curtain_Linen_White", (0.95, 0.93, 0.88, 1), 0.95),
    "sheer": mat("Window_Sheer", (0.98, 0.97, 0.94, 1), 0.9),
    "jute": mat("Rug_Jute", (0.72, 0.55, 0.33, 1), 1.0),
    "jute_dark": mat("Rug_Jute_Border", (0.38, 0.26, 0.15, 1), 1.0),
    "shag": mat("Rug_Round_Cream", (0.93, 0.9, 0.84, 1), 1.0),
    "shag_line": mat("Rug_Round_Pattern", (0.35, 0.3, 0.26, 1), 1.0),
    "sheet": mat("Bed_Sheet_White", (0.96, 0.95, 0.93, 1), 0.85),
    "duvet": mat("Bed_Duvet_Beige", (0.74, 0.6, 0.46, 1), 0.95),
    "throw": mat("Bed_Throw_Sand", (0.62, 0.5, 0.38, 1), 0.95),
    "pillow": mat("Pillow_Beige", (0.8, 0.72, 0.62, 1), 0.95),
    "boucle": mat("Chair_Boucle_Beige", (0.72, 0.66, 0.58, 1), 1.0),
    "screen": mat("Monitor_Screen", (0.3, 0.42, 0.6, 1), 0.2, emit=1.0),
    "plastic": mat("Plastic_Black", (0.04, 0.04, 0.045, 1), 0.4),
    "hole": mat("Pegboard_Hole", (0.2, 0.14, 0.09, 1), 0.9),
    "glow": mat("Light_Warm_Glow", (1.0, 0.9, 0.72, 1), 0.5, emit=4.0),
    "sky": mat("Window_Daylight", (0.85, 0.92, 1.0, 1), 0.3, emit=2.0),
    "door": mat("Door_Cream", (0.92, 0.9, 0.86, 1), 0.4),
    "plant": mat("Plant_Green", (0.25, 0.42, 0.22, 1), 0.7),
    "pot": mat("Pot_Ceramic_White", (0.95, 0.94, 0.9, 1), 0.4),
    "art1": mat("Art_Canvas_Sand", (0.85, 0.78, 0.66, 1), 0.9),
    "art2": mat("Art_Canvas_Clay", (0.7, 0.56, 0.44, 1), 0.9),
    "cloth1": mat("Clothes_Gray", (0.55, 0.55, 0.57, 1), 0.9),
    "cloth2": mat("Clothes_Cream", (0.92, 0.9, 0.85, 1), 0.9),
}
BOOK_COLS = [mat("Book_" + n, c, 0.6) for n, c in [
    ("Cream", (0.9, 0.86, 0.78, 1)), ("Brown", (0.45, 0.3, 0.2, 1)), ("Sage", (0.55, 0.62, 0.5, 1)),
    ("Terracotta", (0.72, 0.42, 0.3, 1)), ("Charcoal", (0.2, 0.2, 0.22, 1)), ("Sand", (0.8, 0.7, 0.55, 1))]]

def chord_boxes(cx, cy, r, spacing, angle, w, z0, z1):
    """원 안에 들어가는 평행 선(무늬)들"""
    specs = []
    ca, sa = math.cos(angle), math.sin(angle)
    k = -r
    while k <= r:
        half = math.sqrt(max(r * r - k * k, 0)) - 0.03
        if half > 0.05:
            specs.append((k, half))
        k += spacing
    bm = bmesh.new()
    for k, half in specs:
        mtx = Matrix.Translation((cx - sa * k, cy + ca * k, (z0 + z1) / 2)) @ Matrix.Rotation(angle, 4, 'Z') @ Matrix.Diagonal((2 * half, w, z1 - z0, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)
    return bm

# =============== 방: 바닥, 벽, 문, 창문 ===============
box("Floor", 0, W, 0, D, -0.03, 0, M["floor"], "Room")
T = 0.1
box("Wall_Left", -T, 0, -T, D + T, 0, H, M["wall"], "Room")
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 1.25, 2.65, 0.8, 2.2      # 오른쪽 벽 창문
boxes("Wall_Right_Window", [(W, W + T, -T, WIN_Y0, 0, H), (W, W + T, WIN_Y1, D + T, 0, H),
                            (W, W + T, WIN_Y0, WIN_Y1, 0, WIN_Z0), (W, W + T, WIN_Y0, WIN_Y1, WIN_Z1, H)], M["wall"], "Room")
wd = box("Window_Daylight", W + T - 0.01, W + T, WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1, M["sky"], "Room")
try:
    wd.visible_shadow = False
except Exception:
    pass
boxes("Window_Frame", [(W, W + 0.04, WIN_Y0 - 0.04, WIN_Y0, WIN_Z0 - 0.04, WIN_Z1 + 0.04), (W, W + 0.04, WIN_Y1, WIN_Y1 + 0.04, WIN_Z0 - 0.04, WIN_Z1 + 0.04),
                       (W, W + 0.04, WIN_Y0, WIN_Y1, WIN_Z0 - 0.04, WIN_Z0), (W, W + 0.04, WIN_Y0, WIN_Y1, WIN_Z1, WIN_Z1 + 0.04),
                       (W + 0.03, W + 0.05, (WIN_Y0 + WIN_Y1) / 2 - 0.015, (WIN_Y0 + WIN_Y1) / 2 + 0.015, WIN_Z0, WIN_Z1)], M["white"], "Room")
box("Wall_Back", -T, W + T, D, D + T, 0, H, M["wall"], "Room")
DX0, DX1, DH = 0.15, 0.95, 2.05
boxes("Wall_Front_Entrance", [(-T, DX0, -T, 0, 0, H), (DX1, W + T, -T, 0, 0, H), (DX0, DX1, -T, 0, DH, H)], M["wall"], "Room")
boxes("Door_Frame", [(DX0 - 0.04, DX0, -T - 0.01, 0.01, 0, DH + 0.04), (DX1, DX1 + 0.04, -T - 0.01, 0.01, 0, DH + 0.04),
                     (DX0 - 0.04, DX1 + 0.04, -T - 0.01, 0.01, DH, DH + 0.04)], M["oak_light"], "Room")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(((DX1 - DX0) / 2, -0.02, (DH - 0.01) / 2)) @ Matrix.Diagonal((DX1 - DX0, 0.04, DH - 0.01, 1)))
door = finish("Door", bm, M["door"], "Room", (DX0, 0, 0))
door.rotation_euler = (0, 0, math.radians(75))
handle = cyl("Door_Handle", 0.02, 0.95, 1.0, 0, 0, M["silver"], "Room", 16)
handle.parent = door; handle.location = (0.72, 0.03, 0.97)
# 바닥 걸레받이
boxes("Baseboards", [(0, 0.015, 0, D, 0, 0.07), (W - 0.015, W, 0, D, 0, 0.07), (0, W, D - 0.015, D, 0, 0.07)], M["white"], "Room")

# =============== 입구 쪽 공간: 전신거울, 화장대, 네모난 라탄 러그 ===============
mirror = boxes("Mirror_Floor_Frame", [(0.0, 0.05, -0.3, 0.3, 0, 1.75)], M["whitewash"], "Entry_Zone")
glass = boxes("Mirror_Floor_Glass", [(0.051, 0.055, -0.25, 0.25, 0.05, 1.7)], M["mirror"], "Entry_Zone")
for o in (mirror, glass):
    o.location = (0.27, 2.8 + 0.14 + 0.3, 0)   # 거울 입구쪽 끝 = 러그 겉에서 2번째 줄
    o.rotation_euler = (0, math.radians(-8), 0)      # 벽에 살짝 기대어 세운 거울

VX0, VX1 = 0.05, 0.75                                   # 화장대 (뒷벽 구석)
box("Vanity_Top", VX0, VX1, D - 0.42, D - 0.02, 0.72, 0.75, M["white"], "Entry_Zone")
box("Vanity_Drawer", VX0 + 0.05, VX1 - 0.05, D - 0.42, D - 0.05, 0.62, 0.72, M["white"], "Entry_Zone")
boxes("Vanity_Legs", [(VX0 + 0.02, VX0 + 0.05, D - 0.4, D - 0.37, 0, 0.62), (VX1 - 0.05, VX1 - 0.02, D - 0.4, D - 0.37, 0, 0.62),
                      (VX0 + 0.02, VX0 + 0.05, D - 0.07, D - 0.04, 0, 0.62), (VX1 - 0.05, VX1 - 0.02, D - 0.07, D - 0.04, 0, 0.62)], M["oak_light"], "Entry_Zone")
box("Vanity_Mirror", (VX0 + VX1) / 2 - 0.2, (VX0 + VX1) / 2 + 0.2, D - 0.05, D - 0.03, 0.8, 1.35, M["mirror"], "Entry_Zone")
boxes("Vanity_Mirror_Lights", [((VX0 + VX1) / 2 - 0.23, (VX0 + VX1) / 2 - 0.2, D - 0.06, D - 0.03, 0.8, 1.35),
                               ((VX0 + VX1) / 2 + 0.2, (VX0 + VX1) / 2 + 0.23, D - 0.06, D - 0.03, 0.8, 1.35)], M["glow"], "Entry_Zone")
cyl("Vanity_Bottle_1", 0.02, 0.75, 0.87, VX0 + 0.13, D - 0.15, M["pot"], "Entry_Zone", 12)
cyl("Vanity_Bottle_2", 0.018, 0.75, 0.83, VX0 + 0.19, D - 0.12, BOOK_COLS[3], "Entry_Zone", 12)
box("Vanity_Makeup_Box", VX1 - 0.23, VX1 - 0.07, D - 0.25, D - 0.12, 0.75, 0.8, BOOK_COLS[5], "Entry_Zone")
cyl("Vanity_Stool", 0.17, 0.0, 0.45, (VX0 + VX1) / 2, D - 0.75, M["boucle"], "Entry_Zone", 32)

RX0, RX1, RY0, RY1 = 0.02, DIV - 0.05, 2.8, 4.97              # 네모난 라탄(주트) 러그
box("Rug_Square_Border", RX0, RX1, RY0, RY1, 0, 0.012, M["jute_dark"], "Entry_Zone")
for i, inset in enumerate([0.06, 0.14, 0.2, 0.28, 0.34]):
    box("Rug_Square_Ring_%d" % i, RX0 + inset, RX1 - inset, RY0 + inset, RY1 - inset, 0, 0.013 + 0.0005 * i,
        M["jute"] if i % 2 == 0 else M["jute_dark"], "Entry_Zone")

# =============== 파티션 (천장까지 나무 살) + 커튼 ===============
PY0 = 3.65
slats = [(DIV - 0.025, DIV + 0.025, PY0 + i * 0.07, PY0 + i * 0.07 + 0.05, 0.0, H) for i in range(19)]   # 틈 2cm
slats += [(DIV - 0.03, DIV + 0.03, PY0, D, H - 0.04, H), (DIV - 0.03, DIV + 0.03, PY0, D, 0, 0.04)]
boxes("Partition_Wood_Slats", slats, M["oak_light"], "Divider")

CY0, CY1 = 1.15, PY0
bm = bmesh.new()
n = 150
rows = []
for i in range(n + 1):
    y = CY0 + (CY1 - CY0) * i / n
    amp = 0.03 + 0.02 * math.sin(i * 0.37)
    x = DIV - 0.08 + amp * math.sin(2 * math.pi * (y - CY0) / 0.14)
    rows.append((bm.verts.new((x + 0.01, y, 0.0)), bm.verts.new((x, y, H - 0.06))))
for i in range(n):
    bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
curtain = finish("Curtain_Linen", bm, M["linen"], "Divider", smooth=True)
curtain.modifiers.new("Thickness", 'SOLIDIFY').thickness = 0.006
rail = cyl("Curtain_Rail", 0.012, -(D - CY0) / 2, (D - CY0) / 2, 0, 0, M["metal"], "Divider", 16)
rail.rotation_euler = (math.radians(90), 0, 0)
rail.location = (DIV - 0.08, (CY0 + D) / 2, H - 0.04)

# =============== 옷장 (파티션 옆, 문 하나 열림 + 옷) ===============
OX0, OX1, OY0, OY1, OH = 0.95, 1.76, D - 0.6, D - 0.02, 2.1   # 옷장 (화장대 바로 옆, 뒷벽)
boxes("Wardrobe_Body", [(OX0, OX1, OY0 + 0.02, OY1, 0, OH)], M["oak"], "Wardrobe")
boxes("Wardrobe_Doors", [(OX0 + 0.01, (OX0 + OX1) / 2 - 0.004, OY0, OY0 + 0.02, 0.06, OH - 0.02),
                         ((OX0 + OX1) / 2 + 0.004, OX1 - 0.01, OY0, OY0 + 0.02, 0.06, OH - 0.02)], M["oak_light"], "Wardrobe")
boxes("Wardrobe_Handles", [((OX0 + OX1) / 2 - 0.05, (OX0 + OX1) / 2 - 0.035, OY0 - 0.025, OY0, 0.85, 1.25),
                           ((OX0 + OX1) / 2 + 0.035, (OX0 + OX1) / 2 + 0.05, OY0 - 0.025, OY0, 0.85, 1.25)], M["metal"], "Wardrobe")
box("Wardrobe_Plinth", OX0 + 0.03, OX1 - 0.03, OY0 + 0.03, OY1, 0, 0.06, M["oak"], "Wardrobe")

# 옷장 문에 압정(연두색)으로 꽂아둔 하늘 사진 폴라로이드 3장 (8.8 x 10.7cm)
def photo_mat(name, path):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 0.35
    tex = nt.nodes.new("ShaderNodeTexImage"); img = bpy.data.images.load(path); img.pack(); tex.image = img
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    m.diffuse_color = (0.8, 0.85, 0.95, 1)
    return m
pin_green = mat("Push_Pin_Lime", (0.55, 0.85, 0.3, 1), 0.25)
PW, PH = 0.088, 0.107
PHOTO_DIR = os.path.join(os.path.expanduser('~/Documents/Claude_Room'), 'textures')
for i, (px, pz, ang) in enumerate(((OX0 + 0.16, 1.52, -6), ((OX0 + OX1) / 2 + 0.07, 1.6, 4), (OX1 - 0.17, 1.42, -3))):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((-PW / 2, 0, -PH / 2), (PW / 2, 0, -PH / 2), (PW / 2, 0, PH / 2), (-PW / 2, 0, PH / 2))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, co in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = co
    ph = finish("Polaroid_Sky_%d" % (i + 1), bm, photo_mat("Polaroid_Sky_%d" % (i + 1), os.path.join(PHOTO_DIR, "polaroid_sky_%d.png" % (i + 1))), "Wardrobe",
                (px, OY0 - 0.0015, pz))
    a = math.radians(ang)
    ph.rotation_euler = (0, a, 0)
    top = PH / 2 - 0.012
    pin_loc = (px + top * math.sin(a), OY0 - 0.006, pz + top * math.cos(a))
    head = cyl("Push_Pin_%d" % (i + 1), 0.0065, -0.004, 0.004, 0, 0, pin_green, "Wardrobe", 20)
    head.rotation_euler = (math.radians(90), 0, 0); head.location = pin_loc
    bevp = head.modifiers.new("Round", 'BEVEL'); bevp.width = 0.002; bevp.segments = 3

# =============== 침대 (머리 = 오른쪽 벽) + 액자 + 협탁 ===============
BX0, BX1, BY0, BY1 = 2.30, W - 0.02, D - 1.47, D - 0.07
box("Bed_Frame", BX0, BX1 - 0.06, BY0, BY1, 0.1, 0.3, M["oak"], "Bed")
boxes("Bed_Legs", [(BX0 + 0.03, BX0 + 0.09, BY0 + 0.03, BY0 + 0.09, 0, 0.1), (BX0 + 0.03, BX0 + 0.09, BY1 - 0.09, BY1 - 0.03, 0, 0.1),
                   (BX1 - 0.15, BX1 - 0.09, BY0 + 0.03, BY0 + 0.09, 0, 0.1), (BX1 - 0.15, BX1 - 0.09, BY1 - 0.09, BY1 - 0.03, 0, 0.1)], M["oak"], "Bed")
# 헤드보드: 침대 프레임과 같은 원목 수납형 (위쪽 선반 + 은은한 조명이 들어간 오픈 칸)
hb_wood = M["oak"]   # 침대 프레임과 같은 원목
HY0, HY1, HD = BY0 - 0.03, BY1 + 0.03, 0.2
HX0 = BX1 - HD
YC, YW = (BY0 + BY1) / 2, (BY1 - BY0 + 0.06)
boxes("Bed_Headboard", [
    (HX0, BX1, HY0, HY0 + 0.03, 0.1, 1.22), (HX0, BX1, HY1 - 0.03, HY1, 0.1, 1.22),      # 양쪽 기둥
    (HX0, BX1, HY0, HY1, 0.1, 0.78),                                                  # 아래 패널 (앞면을 위 칸과 맞춰서 튀어나온 곳 없게)
    (BX1 - 0.02, BX1, HY0, HY1, 0.78, 1.2),                                           # 뒷판
    (HX0, BX1, HY0, HY1, 0.78, 0.8),                                                  # 조명 칸 바닥(선반)
    (HX0, BX1, HY0, HY1, 1.0, 1.03),                                                  # 위 선반 바닥
    (HX0, HX0 + 0.02, HY0, YC - 0.22 * YW, 1.03, 1.2), (HX0, HX0 + 0.02, YC + 0.22 * YW, HY1, 1.03, 1.2),   # 앞 턱 (양쪽 높게)
    (HX0, HX0 + 0.02, YC - 0.22 * YW, YC + 0.22 * YW, 1.03, 1.12),                    # 앞 턱 가운데 (낮게 파임)
], hb_wood, "Bed")
# 파임 부분 곡선 느낌 (양쪽 경사)
for k, sgn in enumerate((-1, 1)):
    bm = bmesh.new()
    y_hi, y_lo = YC + sgn * 0.22 * YW, YC + sgn * 0.16 * YW
    pts = [(y_hi, 1.12), (y_hi, 1.2), (y_hi - sgn * 0.0001, 1.2)]
    prof = [(y_hi, 1.12)] + [(y_hi + (y_lo - y_hi) * t, 1.12) for t in (1,)]
    vs_front = []
    steps = 8
    for j in range(steps + 1):
        t = j / steps
        yv = y_hi + (y_lo - y_hi) * t
        zv = 1.2 - 0.08 * (0.5 - 0.5 * math.cos(math.pi * t))
        vs_front.append((yv, zv))
    verts = []
    for (yv, zv) in vs_front:
        verts.append((bm.verts.new((HX0, yv, 1.12)), bm.verts.new((HX0, yv, zv)), bm.verts.new((HX0 + 0.02, yv, zv)), bm.verts.new((HX0 + 0.02, yv, 1.12))))
    for j in range(steps):
        a, b = verts[j], verts[j + 1]
        for q in range(4):
            bm.faces.new((a[q], b[q], b[(q + 1) % 4], a[(q + 1) % 4]))
    bm.faces.new(verts[0][::-1]); bm.faces.new(verts[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    finish("Bed_Headboard_Curve_%d" % k, bm, hb_wood, "Bed")
# 조명 칸 LED (위 선반 아래쪽 앞부분)
box("Bed_Headboard_LED", HX0 + 0.02, HX0 + 0.04, HY0 + 0.03, HY1 - 0.03, 0.992, 1.0, mat("LED_Warm", (1.0, 0.88, 0.68, 1), 0.5, emit=6.0), "Bed")

def apple_model(name, x, y, z, R=0.034, turn=0.0, coll="Bed"):
    """작은 청사과 모형: 위가 살짝 넓고 꼭지 쪽이 쏙 들어간 사과 모양 + 꼭지 + 잎사귀"""
    def am(nm, setup):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        setup(m); return m
    def skin(m):
        nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Roughness"].default_value = 0.28
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60.0
        rp = nt.nodes.new("ShaderNodeValToRGB")
        rp.color_ramp.elements[0].color = (0.42, 0.66, 0.2, 1); rp.color_ramp.elements[1].color = (0.7, 0.8, 0.3, 1)
        rp.color_ramp.elements[0].position = 0.35; rp.color_ramp.elements[1].position = 0.75
        nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], b.inputs["Base Color"])
        m.diffuse_color = (0.5, 0.72, 0.25, 1)
    def flat(rgba, rough):
        def f(m):
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough
            m.diffuse_color = rgba
        return f
    skin_m = am("Apple_Model_Skin", skin)
    stem_m = am("Apple_Model_Stem", flat((0.36, 0.24, 0.14, 1), 0.6))
    leaf_m = am("Apple_Model_Leaf", flat((0.3, 0.52, 0.22, 1), 0.45))
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); cl.objects.link(root)
    root.location = (x, y, z); root.rotation_euler = (0, 0, turn)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0)
    for v in bm.verts:
        px, py, pz = v.co
        rxy2 = px * px + py * py
        s = 1.0 + 0.09 * pz                     # 위가 살짝 넓게
        px, py = px * s, py * s
        pz *= 0.9
        if pz > 0:
            pz -= 0.32 * math.exp(-rxy2 / 0.05)   # 꼭지 쪽 파임
        else:
            pz += 0.16 * math.exp(-rxy2 / 0.03)   # 아래 파임
        v.co = Vector((px * R, py * R, (pz + 0.9) * R * 0.98))
    me = bpy.data.meshes.new(name + "_Body"); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(skin_m)
    o = bpy.data.objects.new(me.name, me); cl.objects.link(o); o.parent = root
    o.modifiers.new("Soft", 'SUBSURF').levels = 1
    top = R * 0.98 * (0.9 + 0.9 - 0.32)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=R * 0.06, radius2=R * 0.045, depth=R * 0.7,
                          matrix=Matrix.Translation((R * 0.05, 0, top + R * 0.3)) @ Matrix.Rotation(math.radians(12), 4, 'Y'))
    me = bpy.data.meshes.new(name + "_Stem"); bm.to_mesh(me); bm.free(); me.materials.append(stem_m)
    so = bpy.data.objects.new(me.name, me); cl.objects.link(so); so.parent = root
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0,
                              matrix=Matrix.Translation((R * 0.32, R * 0.12, top + R * 0.42)) @ Matrix.Rotation(math.radians(-25), 4, 'Y') @ Matrix.Rotation(math.radians(15), 4, 'Z')
                              @ Matrix.Diagonal((R * 0.42, R * 0.2, R * 0.04, 1)))
    me = bpy.data.meshes.new(name + "_Leaf"); bm.to_mesh(me); bm.free(); me.materials.append(leaf_m)
    for p in me.polygons:
        p.use_smooth = True
    lo = bpy.data.objects.new(me.name, me); cl.objects.link(lo); lo.parent = root
    return root
apple_model("Bed_Headboard_Apple", HX0 + 0.09, HY1 - 0.15, 0.8, turn=math.radians(-30))   # 헤드보드 조명 칸 왼쪽 끝: 작은 청사과 모형
led = bpy.data.lights.new("Headboard_Glow", 'AREA'); led.energy = 12; led.size = 1.2; led.size_y = 0.1
led.shape = 'RECTANGLE'; led.color = (1.0, 0.85, 0.62)
lo = bpy.data.objects.new("Headboard_Glow", led); lo.location = (HX0 + 0.1, YC, 0.99); lo.rotation_euler = (0, 0, math.radians(90))
col("Bed").objects.link(lo)
SAGE = (0.6, 0.68, 0.5, 1)
SAGE_LIGHT = (0.7, 0.79, 0.6, 1)
CREAM_WHITE = (0.97, 0.97, 0.94, 1)
def plaid_mat(name, base, c1, c2, period=0.11, w=0.3):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 0.92
    for nm in ("Sheen Weight", "Sheen"):
        if nm in b.inputs:
            b.inputs[nm].default_value = 0.4; break
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    def band(out, width):
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.0 / period
        nt.links.new(out, mul.inputs[0])
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; nt.links.new(mul.outputs[0], fr.inputs[0])
        lt = nt.nodes.new("ShaderNodeMath"); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = width
        nt.links.new(fr.outputs[0], lt.inputs[0])
        return lt.outputs[0]
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'
    nt.links.new(band(sep.outputs[0], w), add.inputs[0]); nt.links.new(band(sep.outputs[1], w), add.inputs[1])
    half = nt.nodes.new("ShaderNodeMath"); half.operation = 'MULTIPLY'; half.inputs[1].default_value = 0.5
    nt.links.new(add.outputs[0], half.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = base
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = c2
    e = ramp.color_ramp.elements.new(0.25); e.color = c1
    nt.links.new(half.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    m.diffuse_color = c1
    return m
plaid = plaid_mat("Bedding_Plaid_Sage", CREAM_WHITE, SAGE_LIGHT, (0.5, 0.61, 0.41, 1), period=0.13, w=0.32)
sheet_sage = mat("Bed_Sheet_Sage", SAGE, 0.9)
pillow_sage = mat("Pillow_Sage", (0.56, 0.64, 0.46, 1), 0.9)
plaid_pillow = plaid_mat("Pillow_Plaid_Sage_Deeper", CREAM_WHITE, (0.52, 0.66, 0.4, 1), (0.32, 0.47, 0.23, 1), period=0.11, w=0.32)

def puffy(name, x0, x1, y0, y1, z0, z1, m, bevel, wrinkle, scale=0.18, billow=0.0, cuts=12, lift=None):
    """두툼하고 푹신한 덩어리 (둥근 모서리 + 주름)"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1)))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    if lift:   # (시작 x, 경사 길이, 높이): 이불 머리쪽을 베개 위로 덮이게 들어올림
        lx, lr, lh = lift
        cx = (x0 + x1) / 2
        for v in bm.verts:
            t = min(max((cx + v.co.x - lx) / lr, 0.0), 1.0)
            t = t * t * (3 - 2 * t)
            if v.co.z > 0:
                v.co.z += lh * t
            else:
                v.co.z += lh * 0.6 * t
    o = finish(name, bm, m, "Bed", ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), smooth=True)
    bv = o.modifiers.new("Round", 'BEVEL'); bv.width = bevel; bv.segments = 4; bv.limit_method = 'NONE'
    sub = o.modifiers.new("Soft", 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    tex = bpy.data.textures.new(name + "_Wrinkles", 'CLOUDS'); tex.noise_scale = scale; tex.noise_depth = 2
    dp = o.modifiers.new("Wrinkles", 'DISPLACE'); dp.texture = tex; dp.strength = wrinkle; dp.mid_level = 0.5
    dp.texture_coords = 'GLOBAL'
    if billow > 0:   # 크게 부풀어 오른 볼륨감
        t2 = bpy.data.textures.new(name + "_Billow", 'CLOUDS'); t2.noise_scale = 0.4; t2.noise_depth = 1
        d2 = o.modifiers.new("Billow", 'DISPLACE'); d2.texture = t2; d2.strength = billow; d2.mid_level = 0.35
        d2.texture_coords = 'GLOBAL'
    return o

def puffy_duvet(name, x0, x1, y0, y1, z0, z1, m, lift=None, dome=0.09, quilt=0.034, period=0.32, R=0.11, cuts=60):
    """폭신한 누빔 이불: 가장자리가 둥글게 말리고, 가운데가 볼록하고, 솜이 칸칸이 볼록한 누빔"""
    W_, D_, H_ = x1 - x0, y1 - y0, z1 - z0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((W_, D_, H_, 1)))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    cx = (x0 + x1) / 2
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        hx, hy = W_ / 2 - abs(x), D_ / 2 - abs(y)
        e, dzt = min(hx, hy), H_ / 2 - z
        if e < R and dzt < R:   # 위 모서리를 반지름 R로 둥글게 말기
            a, b = R - e, R - dzt
            L = math.hypot(a, b)
            if L > 1e-9:
                e2, dzt2 = R - a * R / L, R - b * R / L
                if hx <= hy:
                    x = math.copysign(W_ / 2 - e2, x)
                else:
                    y = math.copysign(D_ / 2 - e2, y)
                z = H_ / 2 - dzt2
        nx, ny = 2 * x / W_, 2 * y / D_
        wz = min(max((z + H_ / 2) / H_, 0.0), 1.0) ** 3
        edge = max(1 - abs(nx) ** 4, 0) * max(1 - abs(ny) ** 4, 0)
        qx = 0.5 - 0.5 * math.cos(2 * math.pi * (x + W_ / 2) / period)
        qy = 0.5 - 0.5 * math.cos(2 * math.pi * (y + D_ / 2) / period)
        z += wz * edge * (dome + quilt * (qx * qy) ** 0.35)
        if lift:   # (시작 x, 경사 길이, 높이): 이불 머리쪽을 베개 위로 덮이게 들어올림
            lx, lr, lh = lift
            t = min(max((cx + x - lx) / lr, 0.0), 1.0)
            t = t * t * (3 - 2 * t)
            z += lh * t * (1.0 if z > 0 else 0.6)
        v.co.x, v.co.y, v.co.z = x, y, z
    o = finish(name, bm, m, "Bed", ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), smooth=True)
    sub = o.modifiers.new("Soft", 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    tex = bpy.data.textures.new(name + "_Wrinkles", 'CLOUDS'); tex.noise_scale = 0.3; tex.noise_depth = 2
    dp = o.modifiers.new("Wrinkles", 'DISPLACE'); dp.texture = tex; dp.strength = 0.006; dp.mid_level = 0.5; dp.texture_coords = 'GLOBAL'
    t2 = bpy.data.textures.new(name + "_Billow", 'CLOUDS'); t2.noise_scale = 0.45; t2.noise_depth = 1
    d2 = o.modifiers.new("Billow", 'DISPLACE'); d2.texture = t2; d2.strength = 0.04; d2.mid_level = 0.35; d2.texture_coords = 'GLOBAL'
    return o

def soften_fabric(m, sheen=0.75, bump=0.22):
    """천 느낌: 부드러운 반짝임(시인) + 아주 고운 천 결"""
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    for key in ("Sheen Weight", "Sheen"):
        if key in b.inputs:
            b.inputs[key].default_value = sheen; break
    if "Sheen Roughness" in b.inputs:
        b.inputs["Sheen Roughness"].default_value = 0.6
    if not b.inputs["Normal"].is_linked:
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 700.0
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.002
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])

box("Bed_Mattress", BX0 + 0.03, BX1 - 0.08, BY0 + 0.03, BY1 - 0.03, 0.3, 0.52, sheet_sage, "Bed")
# 사계절 이불: 두툼하게 부풀고 구겨진 체크 이불 (침대 옆으로 살짝 흘러내림)
soften_fabric(plaid)
puffy_duvet("Bed_Duvet_Plaid", BX0 - 0.05, BX1 - 0.47, BY0 - 0.07, BY1 + 0.03, 0.36, 0.6, plaid, lift=(BX1 - 0.76, 0.14, 0.06))
def nightstand(name, x0, x1, y0, y1, zf, h=0.56, drawers=3, coll="Bed"):
    """침대 옆 작은 원목 서랍장: 짧은 다리 + 서랍 3칸(밝은 원목 앞판) + 동그란 손잡이, 앞면은 -x 쪽(침대 발 쪽)"""
    oak = bpy.data.materials.get("Wood_Oak") or mat("Wood_Oak", (0.6, 0.42, 0.26, 1), 0.55)
    oak_l = bpy.data.materials.get("Wood_Oak_Light") or mat("Wood_Oak_Light", (0.72, 0.56, 0.38, 1), 0.55)
    knob_m = bpy.data.materials.get("Nightstand_Knob_Brass") or mat("Nightstand_Knob_Brass", (0.78, 0.62, 0.36, 1), 0.3, 0.8)
    LEG = 0.09
    zb, zt = zf + LEG, zf + h - 0.025
    body = box(name + "_Body", x0 + 0.004, x1, y0, y1, zb, zt, oak, coll)
    body.modifiers.new("Round", 'BEVEL').width = 0.004
    top = box(name + "_Top", x0 - 0.01, x1, y0 - 0.012, y1 + 0.012, zt, zf + h, oak, coll)
    tb = top.modifiers.new("Round", 'BEVEL'); tb.width = 0.006; tb.segments = 3
    bm = bmesh.new()
    for lx in (x0 + 0.04, x1 - 0.04):
        for ly in (y0 + 0.04, y1 - 0.04):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.011, radius2=0.017, depth=LEG,
                                  matrix=Matrix.Translation((lx, ly, zf + LEG / 2)))
    finish(name + "_Legs", bm, oak, coll, smooth=True)
    gap, inner = 0.006, (zt - zb) - 0.012
    dh = (inner - gap * (drawers - 1)) / drawers
    fronts, kb = bmesh.new(), bmesh.new()
    for k in range(drawers):
        za = zb + 0.006 + k * (dh + gap)
        bmesh.ops.create_cube(fronts, size=1.0, matrix=Matrix.Translation((x0 - 0.004, (y0 + y1) / 2, za + dh / 2)) @ Matrix.Diagonal((0.016, (y1 - y0) - 0.024, dh, 1)))
        bmesh.ops.create_uvsphere(kb, u_segments=16, v_segments=10, radius=1.0,
                                  matrix=Matrix.Translation((x0 - 0.016, (y0 + y1) / 2, za + dh / 2)) @ Matrix.Diagonal((0.009, 0.014, 0.014, 1)))
        bmesh.ops.create_cone(kb, cap_ends=True, segments=12, radius1=0.005, radius2=0.005, depth=0.012,
                              matrix=Matrix.Translation((x0 - 0.009, (y0 + y1) / 2, za + dh / 2)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    fo = finish(name + "_Drawer_Fronts", fronts, oak_l, coll)
    fv = fo.modifiers.new("Round", 'BEVEL'); fv.width = 0.003; fv.segments = 2
    finish(name + "_Knobs", kb, knob_m, coll, smooth=True)
nightstand("Bed_Nightstand", W - 0.44, W - 0.02, BY0 - 0.5, BY0 - 0.08, 0.018)   # 침대 머리맡 옆 작은 서랍장 (러그 위)
# 베개 2개 (눕혀서): 하나는 체크, 하나는 세이지 그린
for i, (yy, mm) in enumerate(((BY0 + 0.37, plaid_pillow), (BY1 - 0.37, pillow_sage))):
    pw = puffy("Bed_Pillow_%d" % i, BX1 - 0.64, BX1 - 0.22, yy - 0.32, yy + 0.32, 0.52, 0.64, mm, 0.055, 0.012, 0.1, billow=0.015, cuts=8)
    cast = pw.modifiers.new("Pillow_Shape", 'CAST'); cast.cast_type = 'SPHERE'; cast.factor = 0.18
    cast.use_z = False   # 모서리만 살짝 둥글게 (높이는 그대로)
    pw.modifiers.move(pw.modifiers.find("Pillow_Shape"), 1)   # 둥근 모서리 다음, 부드럽게 하기 전


# 액자 2개: 수채화 청사과 그림 (이미지는 파일 안에 포함)
def painting_mat(name, img_path):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 0.85
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(img_path); img.pack()
    tex.image = img
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    m.diffuse_color = (0.75, 0.85, 0.6, 1)
    return m
ART_DIR = os.path.join(os.path.expanduser('~/Documents/Claude_Room'), 'textures')

def cd_player(name, cx, cy, zf, turn=0.0, tex_dir=None, coll="Bed"):
    """세워 두는 CD 플레이어 (상표 없는 일반 디자인): 크림색 네모 몸체 + 앞에 돌아가는 CD가 보이는 투명 덮개 + 아래 받침 스피커 + 위 버튼 (앞면 -x)"""
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    def pm(nm, rgba, rough=0.4, metal=0.0, alpha=1.0):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        if alpha < 1:
            b.inputs["Alpha"].default_value = alpha
            for attr, val in (("surface_render_method", "DITHERED"), ("blend_method", "HASHED")):
                try:
                    setattr(m, attr, val)
                except Exception:
                    pass
        m.diffuse_color = rgba
        return m
    body_m = pm("CDPlayer_Cream", (0.93, 0.91, 0.85, 1), 0.35)
    grille_m = bpy.data.materials.get("CDPlayer_Grille")
    if grille_m is None:
        grille_m = bpy.data.materials.new("CDPlayer_Grille"); grille_m.use_nodes = True
        nt = grille_m.node_tree; b = nt.nodes.get("Principled BSDF"); b.inputs["Roughness"].default_value = 0.6
        tc = nt.nodes.new("ShaderNodeTexCoord"); ck = nt.nodes.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 450.0
        ck.inputs["Color1"].default_value = (0.35, 0.34, 0.32, 1); ck.inputs["Color2"].default_value = (0.12, 0.12, 0.12, 1)
        nt.links.new(tc.outputs["Object"], ck.inputs["Vector"]); nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
        grille_m.diffuse_color = (0.25, 0.25, 0.24, 1)
    silver = pm("CDPlayer_Silver", (0.8, 0.81, 0.83, 1), 0.2, 1.0)
    clear = pm("CDPlayer_Clear_Cover", (0.95, 0.97, 1.0, 1), 0.02, 0.0, 0.07)
    sage = bpy.data.materials.get("Gaming_Chair_Sage_Accent") or pm("CDPlayer_Sage", (0.52, 0.64, 0.45, 1), 0.4)
    led = pm("CDPlayer_LED", (0.5, 1.0, 0.6, 1), 0.3)
    if "Emission Strength" in led.node_tree.nodes.get("Principled BSDF").inputs:
        b = led.node_tree.nodes.get("Principled BSDF")
        for k in ("Emission Color", "Emission"):
            if k in b.inputs:
                b.inputs[k].default_value = (0.5, 1.0, 0.6, 1); break
        b.inputs["Emission Strength"].default_value = 3.0
    disc_m = bpy.data.materials.get("CDPlayer_Disc_Print")
    if disc_m is None:
        disc_m = bpy.data.materials.new("CDPlayer_Disc_Print"); disc_m.use_nodes = True
        nt = disc_m.node_tree; b = nt.nodes.get("Principled BSDF"); b.inputs["Roughness"].default_value = 0.25
        tx = nt.nodes.new("ShaderNodeTexImage"); img = bpy.data.images.load(os.path.join(tex_dir, "cd_disc.png")); img.pack(); tx.image = img
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    root = bpy.data.objects.new(name, None); cl.objects.link(root)
    root.location = (cx, cy, zf); root.rotation_euler = (0, 0, turn)
    def ob(oname, bm, m, bev=0.0, smooth=False, rot=(0, 0, 0), loc=(0, 0, 0)):
        me = bpy.data.meshes.new(oname); bm.to_mesh(me); bm.free()
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(oname, me); cl.objects.link(o); o.parent = root; o.location = loc; o.rotation_euler = rot
        if bev:
            bv = o.modifiers.new("Round", 'BEVEL'); bv.width = bev; bv.segments = 4
        return o
    def cube(bm, c, s):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((s[0], s[1], s[2], 1)))
    def disc_x(bm, c, r, depth, segs=48):   # x 방향을 보는 원판
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=depth, matrix=Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    # 받침 (스피커)
    bm = bmesh.new(); cube(bm, (0, 0, 0.018), (0.09, 0.21, 0.036)); ob(name + "_Base", bm, body_m, 0.008)
    bm = bmesh.new()
    for sd in (-1, 1):
        disc_x(bm, (-0.0455, sd * 0.065, 0.018), 0.012, 0.002, 32)
    ob(name + "_Speaker_Grilles", bm, grille_m)
    bm = bmesh.new(); cube(bm, (-0.0455, 0, 0.018), (0.002, 0.07, 0.006)); ob(name + "_Base_Stripe", bm, sage)
    # 세운 몸체 (뒤로 살짝 기울임)
    TILT = (0, math.radians(8), 0)
    pl = (0.008, 0, 0.034)
    bm = bmesh.new(); cube(bm, (0, 0, 0.1), (0.038, 0.2, 0.2)); ob(name + "_Body", bm, body_m, 0.012, rot=TILT, loc=pl)
    bm = bmesh.new(); disc_x(bm, (-0.0195, 0, 0.1), 0.068, 0.003); ob(name + "_Disc_Tray", bm, silver, rot=TILT, loc=pl)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    N = 64; R = 0.06
    ring = [bm.verts.new((-0.0222, R * math.cos(2 * math.pi * i / N), 0.1 + R * math.sin(2 * math.pi * i / N))) for i in range(N)]
    f = bm.faces.new(ring)
    for lp in f.loops:
        lp[uv].uv = (0.5 - 0.5 * lp.vert.co.y / R, 0.5 + 0.5 * (lp.vert.co.z - 0.1) / R)
    bmesh.ops.recalc_face_normals(bm, faces=[f])
    if f.normal.x > 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    ob(name + "_CD", bm, disc_m, rot=TILT, loc=pl)
    bm = bmesh.new(); disc_x(bm, (-0.0275, 0, 0.1), 0.07, 0.004); ob(name + "_Clear_Cover", bm, clear, rot=TILT, loc=pl, smooth=True)
    # 위 버튼 3개 + 전원 불빛
    bm = bmesh.new()
    for k in range(3):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.007, radius2=0.006, depth=0.006, matrix=Matrix.Translation((0, -0.025 + k * 0.025, 0.202)))
    ob(name + "_Buttons", bm, sage, rot=TILT, loc=pl, smooth=True)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.0025, matrix=Matrix.Translation((-0.0195, 0.082, 0.185)))
    ob(name + "_LED", bm, led, rot=TILT, loc=pl, smooth=True)
    return root
cd_player("Bed_CD_Player", W - 0.24, BY0 - 0.29, 0.018 + 0.56, turn=0.0, tex_dir=os.path.join(ART_DIR, "merch"))   # 침대 옆 서랍장 위 CD 플레이어
ARTS = (("Art_Green_Apples", "Painting_Green_Apples_Watercolor", "art_green_apple_3.png"),   # 왼쪽: 청사과 3개
        ("Art_Blue_Guitar", "Painting_Blue_Guitar_Watercolor", "art_guitar_blue_v2.png"))         # 오른쪽: 파란 일렉기타
for i, x0 in enumerate((2.95, 3.65)):
    box("Art_Frame_%d" % i, x0, x0 + 0.58, D - 0.03, D, 1.35, 1.95, M["oak"], "Bed")
    box("Art_Mat_Board_%d" % i, x0 + 0.035, x0 + 0.545, D - 0.033, D - 0.03, 1.385, 1.915, M["white"], "Bed")
    px0, px1, pz0, pz1, py = x0 + 0.07, x0 + 0.51, 1.42, 1.88, D - 0.0345
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((px0, py, pz0), (px1, py, pz0), (px1, py, pz1), (px0, py, pz1))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, co in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = co
    oname, mname, fname = ARTS[i]
    finish(oname, bm, painting_mat(mname, os.path.join(ART_DIR, fname)), "Bed")

# =============== 창문 쪽 시어 커튼 ===============
bm = bmesh.new()
rows = []
for i in range(61):
    y = WIN_Y0 - 0.25 + (WIN_Y1 - WIN_Y0 + 0.25) * i / 60
    x = W - 0.07 + 0.02 * math.sin(2 * math.pi * i / 6)
    rows.append((bm.verts.new((x, y, 0.02)), bm.verts.new((x, y, H - 0.06))))
for i in range(60):
    bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
sheer = finish("Window_Sheer_Curtain", bm, M["sheer"], "Room", smooth=True)
sheer.modifiers.new("Thickness", 'SOLIDIFY').thickness = 0.004
sheer.hide_render = False

# =============== 동그란 러그 (크림색 + 다이아몬드 무늬) ===============
RR = 1.3
RCX, RCY = W - RR - 0.02, D - RR - 0.02   # 크기 그대로, 뒷벽+오른쪽 벽 구석(침대 아래)으로 붙임
cyl("Rug_Round", RR, 0, 0.018, RCX, RCY, M["shag"], "Study_Zone", 128)
bm = chord_boxes(RCX, RCY, RR, 0.24, math.radians(45), 0.012, 0.018, 0.02)
finish("Rug_Round_Pattern_A", bm, M["shag_line"], "Study_Zone")
bm = chord_boxes(RCX, RCY, RR, 0.24, math.radians(-45), 0.012, 0.018, 0.02)
finish("Rug_Round_Pattern_B", bm, M["shag_line"], "Study_Zone")

# =============== 책상 ①, 타공판, 책상 ②, 책장 ===============
DH_ = 0.75
def desk(name, x0, x1):
    box(name + "_Top", x0, x1, 0.0, 0.6, DH_ - 0.035, DH_, M["oak"], "Study_Zone")
    box(name + "_Modesty_Panel", x0 + 0.02, x1 - 0.02, 0.02, 0.05, 0.3, DH_ - 0.035, M["oak"], "Study_Zone")
    boxes(name + "_Legs", [(x0, x0 + 0.04, 0.0, 0.6, 0, DH_ - 0.035), (x1 - 0.04, x1, 0.0, 0.6, 0, DH_ - 0.035)], M["oak"], "Study_Zone")
desk("Desk_1", 1.82, 3.0)
desk("Desk_2", 3.12, 4.48)
# 책상 뒤 벽 장식 (나무 살 패널)
boxes("Wall_Slat_Panel", [(1.82 + i * 0.07, 1.82 + i * 0.07 + 0.04, 0.0, 0.025, 0, 1.05) for i in range(38)], M["oak_light"], "Study_Zone")

PX0, PX1, PY1, PH = 3.04, 3.08, 0.95, 1.55              # 타공판: 책상 사이에서 방 쪽으로 튀어나온 칸막이
box("Pegboard", PX0, PX1, 0.0, PY1, 0.0, PH, M["oak_light"], "Study_Zone")
bm = bmesh.new()
for iy in range(9):
    for iz in range(9):
        y = 0.08 + iy * 0.1; z = 0.82 + iz * 0.08
        for xx in (PX0 - 0.001, PX1 + 0.001):
            mtx = Matrix.Translation((xx, y, z)) @ Matrix.Rotation(math.radians(90), 4, 'Y')
            bmesh.ops.create_circle(bm, cap_ends=True, segments=10, radius=0.008, matrix=mtx)
finish("Pegboard_Holes", bm, M["hole"], "Study_Zone")
boxes("Pegboard_Shelves", [(PX0 - 0.14, PX0, 0.6, 0.85, 1.05, 1.07), (PX1, PX1 + 0.14, 0.55, 0.8, 1.25, 1.27)], M["oak"], "Study_Zone")
cyl("Peg_Plant_Pot", 0.045, 1.07, 1.15, PX0 - 0.07, 0.72, M["pot"], "Study_Zone", 32, r2=0.05)
cyl("Peg_Plant_Soil", 0.046, 1.135, 1.145, PX0 - 0.07, 0.72, mat("Soil_Dark", (0.12, 0.08, 0.05, 1), 0.95), "Study_Zone", 32)

def make_plant(name, cx, cy, cz, n_leaves, seed, coll):
    """잎 하나하나 모양을 만든 진짜 같은 화분 식물 (스킨답서스 느낌)"""
    rnd = random.Random(seed)
    leaf_mats = [mat("Leaf_Deep_Green", (0.1, 0.32, 0.1, 1), 0.45), mat("Leaf_Fresh_Green", (0.2, 0.48, 0.16, 1), 0.45),
                 mat("Leaf_Yellow_Green", (0.36, 0.56, 0.2, 1), 0.45)]
    stem_m = mat("Plant_Stem", (0.25, 0.4, 0.15, 1), 0.6)
    bm_leaf = [bmesh.new() for _ in leaf_mats]
    bm_stem = bmesh.new()
    for k in range(n_leaves):
        yaw = math.pi / 2 + math.pi * (k + 0.5) / n_leaves + rnd.uniform(-0.15, 0.15)   # 타공판 반대쪽(앞)으로만 퍼짐
        reach = rnd.uniform(0.02, 0.07)
        rise = rnd.uniform(0.03, 0.12)
        droop = k % 4 == 0                              # 몇 개는 화분 밖으로 늘어짐
        if droop:
            reach += 0.03; rise = rnd.uniform(-0.05, 0.0)
        base = Vector((cx + reach * math.cos(yaw), cy + reach * math.sin(yaw), cz + 0.005 + max(rise, 0.0) + (rise if droop else 0)))
        root = Vector((cx + 0.008 * math.cos(yaw), cy + 0.008 * math.sin(yaw), cz))
        # 줄기 (살짝 휜 3마디)
        mid = (root + base) / 2 + Vector((0, 0, 0.02 if not droop else 0.03))
        for a, b in ((root, mid), (mid, base)):
            d = b - a
            mtx = Matrix.Translation((a + b) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
            bmesh.ops.create_cone(bm_stem, cap_ends=False, segments=6, radius1=0.0018, radius2=0.0015, depth=d.length, matrix=mtx)
        # 잎 (하트 모양 + 가운데 접힘 + 끝이 휘어짐)
        L = rnd.uniform(0.045, 0.075); Wd = L * rnd.uniform(0.55, 0.7)
        pitch = rnd.uniform(-0.2, 0.5) if not droop else rnd.uniform(-1.2, -0.6)
        roll = rnd.uniform(-0.4, 0.4)
        R = Matrix.Rotation(yaw + rnd.uniform(-0.25, 0.25), 4, 'Z') @ Matrix.Rotation(-pitch, 4, 'Y') @ Matrix.Rotation(roll, 4, 'X')
        nt, ns = 10, 3
        bmL = bm_leaf[rnd.randrange(len(leaf_mats))]
        grid = []
        for i in range(nt + 1):
            t = i / nt
            w = Wd * (math.sin(math.pi * min(t * 1.15, 1.0)) ** 0.8) * (1.0 - 0.25 * t) * (1.15 if t < 0.3 else 1.0)
            row = []
            for j in range(-ns, ns + 1):
                sv = j / ns
                x = L * t
                y = sv * w * 0.5
                z = -0.25 * abs(sv) * w * 0.5 - 0.6 * (x ** 2) / L      # 가운데 접힘 + 아래로 휨
                row.append(bmL.verts.new(base + (R @ Vector((x, y, z)))))
            grid.append(row)
        for i in range(nt):
            for j in range(2 * ns):
                bmL.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    for bmL, m in zip(bm_leaf, leaf_mats):
        o = finish(name + "_Leaves_" + m.name.split("_")[1], bmL, m, coll, smooth=True)
        o.modifiers.new("Leaf_Thickness", 'SOLIDIFY').thickness = 0.0008
    finish(name + "_Stems", bm_stem, stem_m, coll, smooth=True)
def cactus_column(bm, base, R, Hh, ribs=9, tilt=None):
    """골이 진 선인장 몸통 (위가 둥글게 닫힘)"""
    nr, nh = 36, 14
    rot = tilt if tilt is not None else Matrix.Identity(4)
    rings = []
    for i in range(nh + 1):
        t = i / nh
        prof = (1 - t ** 4) ** 0.5 if t < 1 else 0.0
        z = Hh * t
        ring = []
        for j in range(nr):
            th = 2 * math.pi * j / nr
            r = R * prof * (1 + 0.13 * math.cos(ribs * th))
            ring.append(bm.verts.new(base + rot @ Vector((r * math.cos(th), r * math.sin(th), z))))
        rings.append(ring)
    for i in range(nh):
        for j in range(nr):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % nr], rings[i + 1][(j + 1) % nr], rings[i + 1][j]))
    top = bm.verts.new(base + rot @ Vector((0, 0, Hh)))
    for j in range(nr):
        bm.faces.new((rings[nh][j], rings[nh][(j + 1) % nr], top))
    # 가시: 골 꼭대기마다 작은 점
    spines = []
    for i in range(1, nh - 1, 2):
        t = i / nh
        prof = (1 - t ** 4) ** 0.5
        for rb in range(ribs):
            th = 2 * math.pi * rb / ribs
            r = R * prof * 1.13 + 0.001
            spines.append(base + rot @ Vector((r * math.cos(th), r * math.sin(th), Hh * t)))
    return spines

def make_cactus(name, cx, cy, cz, coll):
    bm = bmesh.new(); sp = []
    sp += cactus_column(bm, Vector((cx + 0.004, cy, cz)), 0.027, 0.15)
    sp += cactus_column(bm, Vector((cx - 0.022, cy + 0.018, cz)), 0.016, 0.07, ribs=8)            # 옆에 작은 선인장
    arm = Matrix.Rotation(math.radians(38), 4, 'X')
    sp += cactus_column(bm, Vector((cx + 0.004, cy - 0.022, cz + 0.06)), 0.012, 0.055, ribs=7, tilt=arm)   # 팔 하나
    o = finish(name + "_Body", bm, mat("Cactus_Green", (0.22, 0.42, 0.2, 1), 0.55), coll, smooth=True)
    bs = bmesh.new()
    for p in sp:
        bmesh.ops.create_icosphere(bs, subdivisions=1, radius=0.0016, matrix=Matrix.Translation(p))
    finish(name + "_Spines", bs, mat("Cactus_Spine", (0.93, 0.9, 0.78, 1), 0.6), coll)
    # 꼭대기 작은 꽃
    bf = bmesh.new()
    for k in range(6):
        a = 2 * math.pi * k / 6
        bmesh.ops.create_uvsphere(bf, u_segments=8, v_segments=4, radius=0.006,
                                  matrix=Matrix.Translation((cx + 0.004 + 0.006 * math.cos(a), cy + 0.006 * math.sin(a), cz + 0.15)) @ Matrix.Diagonal((1, 1, 0.4, 1)))
    finish(name + "_Flower", bf, mat("Cactus_Flower_Pink", (0.95, 0.5, 0.6, 1), 0.5), coll, smooth=True)
make_cactus("Peg_Cactus", PX0 - 0.07, 0.72, 1.14, "Study_Zone")
cyl("Peg_Pen_Cup", 0.035, 1.27, 1.37, PX1 + 0.07, 0.67, M["pot"], "Study_Zone", 16)
boxes("Peg_Pens", [(PX1 + 0.06, PX1 + 0.065, 0.66, 0.665, 1.3, 1.45), (PX1 + 0.075, PX1 + 0.08, 0.675, 0.68, 1.3, 1.43)], M["plastic"], "Study_Zone")

def pencil_pouch(name, cx, cy, z0, L=0.2, Wd=0.075, Ht=0.058, turn=0.0, coll="Study_Zone"):
    """지퍼 필통: 폭신한 캔버스 천 파우치 + 위쪽 지퍼(세이지 테이프 + 은색 이빨 + 손잡이) (긴 쪽이 y 방향)"""
    def pm(nm, rgba, rough, metal=0.0, bump=0.0):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        if bump:
            tc = nt.nodes.new("ShaderNodeTexCoord"); ck = nt.nodes.new("ShaderNodeTexWave"); ck.inputs["Scale"].default_value = 500.0
            bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.001
            nt.links.new(tc.outputs["Object"], ck.inputs["Vector"]); nt.links.new(ck.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        m.diffuse_color = rgba
        return m
    canvas = pm("Pouch_Canvas_Cream", (0.9, 0.86, 0.76, 1), 0.9, 0, 0.3)
    tape = bpy.data.materials.get("Gaming_Chair_Sage_Accent") or pm("Pouch_Zip_Tape", (0.52, 0.64, 0.45, 1), 0.7)
    metal = pm("Pouch_Zip_Metal", (0.8, 0.8, 0.82, 1), 0.25, 1.0)
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); cl.objects.link(root)
    root.location = (cx, cy, z0); root.rotation_euler = (0, 0, turn)
    def ob(oname, bm, m, mods=()):
        me = bpy.data.meshes.new(oname); bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(oname, me); cl.objects.link(o); o.parent = root
        for kind, val in mods:
            if kind == "bevel":
                bv = o.modifiers.new("Round", 'BEVEL'); bv.width = val; bv.segments = 4
            elif kind == "sub":
                o.modifiers.new("Soft", 'SUBSURF').levels = val
        return o
    # 파우치 몸통: 아래는 납작하고 위가 둥글게 부푼 모양
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)
    for v in bm.verts:
        u = v.co.z + 0.5
        ny = abs(2 * v.co.y)
        pinch = 1 - 0.35 * (ny ** 4) * u          # 양 끝은 위로 갈수록 모임 (지퍼 끝)
        v.co.x *= Wd * pinch * (1 - 0.25 * u * u)  # 위쪽이 좁아지는 어묵 모양
        v.co.y *= L
        v.co.z = u * Ht
    ob(name + "_Body", bm, canvas, (("sub", 2),))
    # 지퍼
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, Ht + 0.0005)) @ Matrix.Diagonal((0.012, L * 0.82, 0.003, 1)))
    ob(name + "_Zip_Tape", bm, tape, (("bevel", 0.001),))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, Ht + 0.0022)) @ Matrix.Diagonal((0.004, L * 0.8, 0.0016, 1)))
    yp = L * 0.25   # 지퍼 손잡이 위치
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, yp, Ht + 0.004)) @ Matrix.Diagonal((0.009, 0.012, 0.004, 1)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((-0.008, yp + 0.004, Ht - 0.004)) @ Matrix.Rotation(math.radians(70), 4, 'Y') @ Matrix.Diagonal((0.02, 0.006, 0.0015, 1)))
    ob(name + "_Zip_Metal", bm, metal, (("bevel", 0.0007),))
    return root
pencil_pouch("Desk_Pencil_Pouch", PX0 - 0.12, 0.3, DH_, turn=math.radians(4))   # 오른쪽 책상 위 타공판 쪽: 지퍼 필통

def desk_pen(name, cx, cy, z0, turn=0.0, coll="Study_Zone"):
    """책상 위에 눕혀 둔 펜: 세이지 몸통 + 회색 고무 그립 + 은색 펜촉 + 흰 뒷캡과 클립 (긴 쪽이 y 방향)"""
    def pm(nm, rgba, rough, metal=0.0):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        m.diffuse_color = rgba
        return m
    body = bpy.data.materials.get("Gaming_Chair_Sage_Accent") or pm("Pen_Sage", (0.52, 0.64, 0.45, 1), 0.35)
    grip = pm("Pen_Grip_Gray", (0.35, 0.36, 0.37, 1), 0.8)
    tip = pm("Pen_Tip_Silver", (0.8, 0.8, 0.82, 1), 0.2, 1.0)
    cap = pm("Pen_Cap_White", (0.95, 0.95, 0.93, 1), 0.3)
    R = 0.0048
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); cl.objects.link(root)
    root.location = (cx, cy, z0 + R); root.rotation_euler = (0, 0, turn)
    def seg(bm, ya, yb, ra, rb):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=ra, radius2=rb, depth=yb - ya,
                              matrix=Matrix.Translation((0, (ya + yb) / 2, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'X'))
    parts = [(body, [(-0.035, 0.05, R, R)]), (grip, [(-0.06, -0.035, R * 1.06, R * 1.06)]),
             (tip, [(-0.072, -0.06, R * 0.35, R * 0.95), (-0.075, -0.072, R * 0.12, R * 0.35)]), (cap, [(0.05, 0.07, R * 1.08, R * 1.08), (0.07, 0.073, R * 1.08, R * 0.7)])]
    for m, segs in parts:
        bm = bmesh.new()
        for ya, yb, ra, rb in segs:
            seg(bm, ya, yb, ra, rb)
        if m is cap:   # 클립
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0.052, R * 1.08 + 0.0012)) @ Matrix.Diagonal((0.0028, 0.034, 0.0012, 1)))
        me = bpy.data.meshes.new("%s_%s" % (name, m.name)); bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = len(p.vertices) == 4
        me.materials.append(m)
        o = bpy.data.objects.new(me.name, me); cl.objects.link(o); o.parent = root
    return root
desk_pen("Desk_Pen", PX0 - 0.205, 0.31, DH_, turn=math.radians(10))   # 필통 옆 펜
# 동그란 벽시계: 책상 뒤 벽면, 타공판 위쪽 끝에서 19cm 떨어진 곳 (테두리만 연한 원목)
CLK_R = 0.125   # 지름 25cm
CLK_X, CLK_Z = (PX0 + PX1) / 2, PH + 0.19 + CLK_R   # 타공판 위 19cm
def disc_y(name, r, y0, y1, m, segs=48):
    o = cyl(name, r, -(y1 - y0) / 2, (y1 - y0) / 2, 0, 0, m, "Study_Zone", segs)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (CLK_X, (y0 + y1) / 2, CLK_Z)
    return o
rim = disc_y("Clock_Rim_Light_Wood", CLK_R, 0.0, 0.035, M["oak_light"])
rb = rim.modifiers.new("Round", 'BEVEL'); rb.width = 0.006; rb.segments = 3
disc_y("Clock_Face", CLK_R - 0.012, 0.035, 0.037, M["white"])
marks = []
for k in range(12):
    a = 2 * math.pi * k / 12
    rr = CLK_R - 0.026
    xc, zc = CLK_X - rr * math.sin(a), CLK_Z + rr * math.cos(a)
    l = 0.015 if k % 3 == 0 else 0.0075
    marks.append((xc - 0.0015, xc + 0.0015, 0.037, 0.039, zc - l / 2, zc + l / 2))
boxes("Clock_Marks", marks, M["plastic"], "Study_Zone")
for nm, ln, wd, ang in (("Clock_Hour_Hand", 0.056, 0.006, 300), ("Clock_Minute_Hand", 0.085, 0.004, 60)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, ln / 2 - 0.008)) @ Matrix.Diagonal((wd, 0.002, ln, 1)))
    hnd = finish(nm, bm, M["plastic"], "Study_Zone", (CLK_X, 0.041, CLK_Z))
    hnd.rotation_euler = (0, math.radians(-ang), 0)
disc_y("Clock_Center_Cap", 0.006, 0.039, 0.044, M["plastic"], 16)

# 책상 ① 소품
# 와이드 LED 스탠드 (사진 참고): 납작한 받침 + 은색 기둥 + 하얀 곡선 목 + 80cm 삼각 조명 바
lamp_white = mat("Lamp_White_Matte", (0.93, 0.92, 0.89, 1), 0.35)
lamp_silver = mat("Lamp_Silver_Aluminum", (0.78, 0.79, 0.8, 1), 0.3, 0.9)
LPX, LPY = 2.2, 0.1                 # 기둥 위치 (책상 뒤쪽)
Z0, RA = DH_ + 0.33, 0.15           # 기둥 높이, 곡선 반지름
lb = box("Desk1_Lamp_Base", LPX - 0.1, LPX + 0.1, LPY - 0.05, LPY + 0.08, DH_, DH_ + 0.016, lamp_white, "Study_Zone")
lbv = lb.modifiers.new("Round", 'BEVEL'); lbv.width = 0.006; lbv.segments = 4
lp = box("Desk1_Lamp_Pole", LPX - 0.013, LPX + 0.013, LPY - 0.013, LPY + 0.013, DH_ + 0.016, Z0 - 0.04, lamp_silver, "Study_Zone")
lpv = lp.modifiers.new("Round", 'BEVEL'); lpv.width = 0.004; lpv.segments = 3
cyl("Desk1_Lamp_Collar", 0.015, Z0 - 0.045, Z0 + 0.002, LPX, LPY, lamp_white, "Study_Zone", 24)
# 하얀 곡선 목 (위로 올라가다 앞으로 휘어짐)
bm = bmesh.new(); rings = []; nseg, nr, tr = 24, 16, 0.013
for i in range(nseg + 1):
    th = math.radians(90) * i / nseg
    cy_, cz_ = LPY + RA - RA * math.cos(th), Z0 + RA * math.sin(th)
    tang = Vector((0, math.sin(th), math.cos(th)))
    nrm = Vector((0, -math.cos(th), math.sin(th)))
    side = Vector((1, 0, 0))
    ring = []
    for j in range(nr):
        ph = 2 * math.pi * j / nr
        p = Vector((LPX, cy_, cz_)) + tr * (math.cos(ph) * side + math.sin(ph) * nrm)
        ring.append(bm.verts.new(p))
    rings.append(ring)
for i in range(nseg):
    for j in range(nr):
        bm.faces.new((rings[i][j], rings[i][(j + 1) % nr], rings[i + 1][(j + 1) % nr], rings[i + 1][j]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
finish("Desk1_Lamp_Curved_Neck", bm, lamp_white, "Study_Zone", smooth=True)
# 80cm 조명 바 (단면이 삼각형)
BXC, BYC, BZ = LPX + 0.13, LPY + RA + 0.012, Z0 + RA + 0.006
BL, BW, BH = 0.8, 0.05, 0.028
bm = bmesh.new()
prof = [(-BW / 2, 0.0), (BW / 2, 0.0), (BW * 0.15, BH)]
e0 = [bm.verts.new((BXC - BL / 2, BYC + y, BZ + z)) for y, z in prof]
e1 = [bm.verts.new((BXC + BL / 2, BYC + y, BZ + z)) for y, z in prof]
for k in range(3):
    bm.faces.new((e0[k], e1[k], e1[(k + 1) % 3], e0[(k + 1) % 3]))
bm.faces.new(e0[::-1]); bm.faces.new(e1)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bar = finish("Desk1_Lamp_Light_Bar", bm, lamp_silver, "Study_Zone")
bbv = bar.modifiers.new("Round", 'BEVEL'); bbv.width = 0.003; bbv.segments = 2
box("Desk1_Lamp_Bar_Cap_L", BXC - BL / 2 - 0.004, BXC - BL / 2, BYC - BW / 2, BYC + BW / 2, BZ, BZ + 0.012, lamp_white, "Study_Zone")
box("Desk1_Lamp_Bar_Cap_R", BXC + BL / 2, BXC + BL / 2 + 0.004, BYC - BW / 2, BYC + BW / 2, BZ, BZ + 0.012, lamp_white, "Study_Zone")
box("Desk1_Lamp_LED_Strip", BXC - BL / 2 + 0.01, BXC + BL / 2 - 0.01, BYC - BW / 2 + 0.006, BYC + BW / 2 - 0.006, BZ - 0.002, BZ, mat("LED_Neutral_Warm", (1.0, 0.95, 0.85, 1), 0.4, emit=8.0), "Study_Zone")
box("Desk1_Lamp_Touch_Panel", BXC - 0.06, BXC + 0.06, BYC - 0.012, BYC + 0.004, BZ + BH * 0.62, BZ + BH * 0.64, lamp_white, "Study_Zone")
dl = bpy.data.lights.new("Lamp_Desk_Wide", 'AREA'); dl.shape = 'RECTANGLE'; dl.size = 0.78; dl.size_y = 0.04
dl.energy = 35; dl.color = (1.0, 0.94, 0.84)
dlo = bpy.data.objects.new("Lamp_Desk_Wide", dl); dlo.location = (BXC, BYC, BZ - 0.004)
col("Study_Zone").objects.link(dlo)

# 책상 ② 컴퓨터
MXc = 3.7
box("Monitor_Frame", MXc - 0.3, MXc + 0.3, 0.12, 0.145, DH_ + 0.13, DH_ + 0.48, M["white"], "Study_Zone")
box("Monitor_Display", MXc - 0.285, MXc + 0.285, 0.146, 0.148, DH_ + 0.145, DH_ + 0.465, mat("Monitor_Screen_Black", (0.015, 0.015, 0.018, 1), 0.12), "Study_Zone")
box("Monitor_Stand", MXc - 0.025, MXc + 0.025, 0.09, 0.12, DH_, DH_ + 0.2, M["white"], "Study_Zone")
box("Monitor_Base", MXc - 0.12, MXc + 0.12, 0.04, 0.2, DH_, DH_ + 0.01, M["white"], "Study_Zone")
# 키보드: 케이스 + 키캡 하나하나 (풀배열: F키줄, 숫자줄, 쿼티, 방향키, 숫자패드)
KU = 0.0192                       # 키 1칸 크기 (19.2mm)
KW_TOTAL = 22.5 * KU
KY0 = 0.302                       # 벽 쪽(위쪽) 가장자리
kcase = box("Keyboard_Case", MXc - KW_TOTAL / 2 - 0.009, MXc + KW_TOTAL / 2 + 0.009, KY0 - 0.008, KY0 + 6.5 * KU + 0.008,
            DH_, DH_ + 0.016, M["white"], "Study_Zone")
kcv = kcase.modifiers.new("Round", 'BEVEL'); kcv.width = 0.004; kcv.segments = 3
ROWS = [
    [(1, 'm'), (1, None), (1, 'a'), (1, 'a'), (1, 'a'), (1, 'a'), (0.5, None), (1, 'a'), (1, 'a'), (1, 'a'), (1, 'a'), (0.5, None), (1, 'a'), (1, 'a'), (1, 'a'), (1, 'a'),
     (0.25, None), (1, 'm'), (1, 'm'), (1, 'm')],
    [(1, 'a')] * 13 + [(2, 'm'), (0.25, None), (1, 'm'), (1, 'm'), (1, 'm'), (0.25, None), (1, 'm'), (1, 'm'), (1, 'm'), (1, 'm')],
    [(1.5, 'm')] + [(1, 'a')] * 12 + [(1.5, 'a'), (0.25, None), (1, 'm'), (1, 'm'), (1, 'm'), (0.25, None), (1, 'a'), (1, 'a'), (1, 'a'), (1, 'tall')],
    [(1.75, 'm')] + [(1, 'a')] * 11 + [(2.25, 'm'), (3.5, None), (1, 'a'), (1, 'a'), (1, 'a')],
    [(2.25, 'm')] + [(1, 'a')] * 10 + [(2.75, 'm'), (1.25, None), (1, 'm'), (1.25, None), (1, 'a'), (1, 'a'), (1, 'a'), (1, 'tall')],
    [(1.25, 'm'), (1.25, 'm'), (1.25, 'm'), (6.25, 'a'), (1.25, 'm'), (1.25, 'm'), (1.25, 'm'), (1.25, 'm'), (0.25, None), (1, 'm'), (1, 'm'), (1, 'm'),
     (0.25, None), (2, 'a'), (1, 'a')],
]
key_specs = {'a': [], 'm': []}
G = 0.0016                        # 키 사이 틈
for r, row in enumerate(ROWS):
    c = 0.0
    yr = KY0 + (r + (0.5 if r > 0 else 0)) * KU
    if r > 0:
        yr = KY0 + 0.5 * KU + r * KU   # F키줄과 숫자줄 사이 간격
    for w, kind in row:
        if kind is not None:
            hgt = 2 if kind == 'tall' else 1
            k = 'a' if kind in ('a', 'tall') else 'm'
            x_hi = MXc + KW_TOTAL / 2 - c * KU            # 사용자 기준 왼쪽 = +x
            x_lo = x_hi - w * KU
            key_specs[k].append((x_lo + G, x_hi - G, yr + G, yr + hgt * KU - G, DH_ + 0.016, DH_ + 0.0235))
        c += w
kmats = {'a': mat("Keycap_White", (0.96, 0.96, 0.95, 1), 0.45), 'm': mat("Keycap_Light_Gray", (0.8, 0.81, 0.82, 1), 0.45)}
for k, specs in key_specs.items():
    ko = boxes("Keyboard_Keycaps_" + ("Alpha" if k == 'a' else "Mod"), specs, kmats[k], "Study_Zone")
    kb = ko.modifiers.new("Round", 'BEVEL'); kb.width = 0.0012; kb.segments = 2
box("Keyboard_Status_LED", MXc - KW_TOTAL / 2 + 0.6 * KU, MXc - KW_TOTAL / 2 + 1.4 * KU, KY0 + 0.1 * KU, KY0 + 0.35 * KU, DH_ + 0.016, DH_ + 0.0165,
    mat("Keyboard_LED_Green", (0.55, 0.85, 0.4, 1), 0.4, emit=3.0), "Study_Zone")
# 무선 마우스 (인체공학 모양, 오른손용): 키보드 오른쪽(사용자 기준)으로 이동
ML, MWD, MHT = 0.115, 0.066, 0.04
MSX, MSY = MXc - KW_TOTAL / 2 - 0.095, 0.385          # 사용자 기준 오른쪽 = -x
mouse_body = mat("Mouse_Off_White", (0.9, 0.9, 0.88, 1), 0.4)
mouse_dark = mat("Mouse_Graphite", (0.18, 0.18, 0.2, 1), 0.5)
def mouse_pt(u, v):
    """u: 길이 방향(-1=앞/벽 쪽, +1=뒤/손목 쪽), v: 폭 방향(+1=엄지 쪽=왼쪽)"""
    cu = max(1 - u * u, 0.0)
    half = MWD / 2 * (cu ** 0.45) * (0.86 + 0.14 * (u + 1) / 2)
    x = v * half
    if v > 0:   # 엄지 쪽 살짝 오목
        x -= 0.003 * math.sin(math.pi * min(v, 1.0)) * cu
    hump = 0.68 + 0.32 * math.exp(-((u - 0.25) / 0.65) ** 2)
    z = MHT * hump * (max(1 - v * v, 0.0) ** 0.42) * (cu ** 0.35)
    return Vector((MSX + x, MSY + u * ML / 2, DH_ + 0.004 + z))
NU, NV = 96, 90
bm = bmesh.new()
grid = [[bm.verts.new(mouse_pt(-1 + 2 * i / NU, -1 + 2 * j / NV)) for j in range(NV + 1)] for i in range(NU + 1)]
faces = []
for i in range(NU):
    for j in range(NV):
        q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
        try:
            f = bm.faces.new(q)
        except ValueError:
            continue
        uc, vc = -1 + 2 * (i + 0.5) / NU, -1 + 2 * (j + 0.5) / NV
        dark = (abs(vc) < 0.022 and uc < 0.02) \
            or (0.86 < vc < 0.92 and (-0.4 < uc < -0.2 or -0.14 < uc < 0.06))
        f.material_index = 1 if dark else 0
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("Mouse")
bm.to_mesh(me); bm.free()
me.materials.append(mouse_body); me.materials.append(mouse_dark)
for p in me.polygons:
    p.use_smooth = True
mo = bpy.data.objects.new("Mouse", me); col("Study_Zone").objects.link(mo)
mb_ = cyl("Mouse_Bottom", 1.0, DH_, DH_ + 0.004, MSX, MSY, mouse_dark, "Study_Zone", 48)
mb_.scale = (MWD / 2 * 0.9, ML / 2 * 0.92, 1)
# 휠
yw = -0.42
zt = mouse_pt(yw, 0.0).z
whl = cyl("Mouse_Scroll_Wheel", 0.0085, -0.0035, 0.0035, 0, 0, mouse_dark, "Study_Zone", 32)
whl.rotation_euler = (0, math.radians(90), 0); whl.location = (MSX, MSY + yw * ML / 2, zt - 0.0035)

box("Desk_Mat", MXc - 0.4, MXc + 0.42, 0.26, 0.5, DH_, DH_ + 0.003, M["boucle"], "Study_Zone")
# 컴퓨터 본체: 하얀 케이스 + 투명 유리 옆판 + 안쪽 부품(메인보드, CPU 쿨러, 램, 그래픽카드, 팬, 파워 덮개)
PCX0, PCX1, PCY0, PCY1, PCZ0, PCZ1 = 4.22, 4.44, 0.05, 0.47, DH_ + 0.012, DH_ + 0.462
T_ = 0.012
pc_dark = mat("PC_Inner_Black", (0.05, 0.05, 0.055, 1), 0.45)
pc_board = mat("PC_Motherboard", (0.12, 0.13, 0.14, 1), 0.5)
pc_led = mat("PC_LED_White", (0.92, 0.95, 1.0, 1), 0.3, emit=5.0)
pc_glass = mat("PC_Tempered_Glass", (0.85, 0.88, 0.9, 1), 0.03, alpha=0.12)
for attr, val in (("surface_render_method", 'BLENDED'), ("blend_method", 'BLEND')):
    try:
        setattr(pc_glass, attr, val)
    except Exception:
        pass
case = boxes("PC_Case", [
    (PCX1 - T_, PCX1, PCY0, PCY1, PCZ0, PCZ1),                      # 오른쪽 옆판 (벽 쪽)
    (PCX0, PCX1, PCY0, PCY1, PCZ1 - T_, PCZ1),                      # 윗판
    (PCX0, PCX1, PCY0, PCY1, PCZ0, PCZ0 + T_),                      # 바닥판
    (PCX0, PCX1, PCY1 - 0.02, PCY1, PCZ0, PCZ1),                    # 앞판 (사람 쪽)
    (PCX0, PCX1, PCY0, PCY0 + T_, PCZ0, PCZ1),                      # 뒤판
    (PCX0, PCX0 + 0.006, PCY0, PCY1, PCZ0, PCZ0 + 0.02), (PCX0, PCX0 + 0.006, PCY0, PCY1, PCZ1 - 0.02, PCZ1),   # 유리 테두리
    (PCX0, PCX0 + 0.006, PCY0, PCY0 + 0.02, PCZ0, PCZ1), (PCX0, PCX0 + 0.006, PCY1 - 0.04, PCY1, PCZ0, PCZ1),
], M["white"], "Study_Zone")
cbv = case.modifiers.new("Round", 'BEVEL'); cbv.width = 0.003; cbv.segments = 2
box("PC_Glass_Panel", PCX0 + 0.001, PCX0 + 0.004, PCY0 + 0.02, PCY1 - 0.04, PCZ0 + 0.02, PCZ1 - 0.02, pc_glass, "Study_Zone")
boxes("PC_Feet", [(PCX0 + 0.015, PCX0 + 0.05, PCY0 + 0.02, PCY0 + 0.06, DH_, PCZ0), (PCX1 - 0.05, PCX1 - 0.015, PCY0 + 0.02, PCY0 + 0.06, DH_, PCZ0),
                  (PCX0 + 0.015, PCX0 + 0.05, PCY1 - 0.06, PCY1 - 0.02, DH_, PCZ0), (PCX1 - 0.05, PCX1 - 0.015, PCY1 - 0.06, PCY1 - 0.02, DH_, PCZ0)], pc_dark, "Study_Zone")
# 앞판: 세로 통풍 슬릿 + 윗면 전원 버튼(LED 링) + USB 포트
boxes("PC_Front_Vents", [(PCX0 + 0.03 + k * 0.012, PCX0 + 0.036 + k * 0.012, PCY1 - 0.0005, PCY1 + 0.0005, PCZ0 + 0.06, PCZ1 - 0.06) for k in range(14)], pc_dark, "Study_Zone")
cyl("PC_Power_Button", 0.009, PCZ1, PCZ1 + 0.002, PCX0 + 0.06, PCY1 - 0.045, M["white"], "Study_Zone", 24)
pr = cyl("PC_Power_LED_Ring", 0.011, PCZ1 - 0.0005, PCZ1 + 0.0015, PCX0 + 0.06, PCY1 - 0.045, pc_led, "Study_Zone", 24)
boxes("PC_USB_Ports", [(PCX0 + 0.09 + k * 0.022, PCX0 + 0.104 + k * 0.022, PCY1 - 0.052, PCY1 - 0.046, PCZ1 - 0.0005, PCZ1 + 0.0005) for k in range(2)], pc_dark, "Study_Zone")
boxes("PC_Top_Vent", [(PCX0 + 0.03, PCX1 - 0.03, PCY0 + 0.04 + k * 0.014, PCY0 + 0.048 + k * 0.014, PCZ1 - 0.0005, PCZ1 + 0.0005) for k in range(18)], pc_dark, "Study_Zone")
# 안쪽 부품
box("PC_Motherboard", PCX1 - T_ - 0.004, PCX1 - T_, PCY0 + 0.03, PCY1 - 0.08, PCZ0 + 0.1, PCZ1 - 0.03, pc_board, "Study_Zone")
box("PC_PSU_Shroud", PCX0 + 0.006, PCX1 - T_, PCY0 + T_, PCY1 - 0.02, PCZ0 + T_, PCZ0 + 0.09, M["white"], "Study_Zone")
gpu = boxes("PC_GPU", [(PCX0 + 0.06, PCX1 - T_ - 0.004, PCY0 + T_, PCY1 - 0.1, PCZ0 + 0.17, PCZ0 + 0.215)], M["white"], "Study_Zone")
gbv = gpu.modifiers.new("Round", 'BEVEL'); gbv.width = 0.003; gbv.segments = 2
box("PC_GPU_LED_Strip", PCX0 + 0.058, PCX0 + 0.06, PCY0 + 0.06, PCY1 - 0.14, PCZ0 + 0.2, PCZ0 + 0.206, pc_led, "Study_Zone")
for k in range(4):
    yk = PCY1 - 0.31 + k * 0.012
    box("PC_RAM_%d" % k, PCX1 - T_ - 0.04, PCX1 - T_ - 0.004, yk, yk + 0.006, PCZ1 - 0.17, PCZ1 - 0.05, pc_dark, "Study_Zone")
    box("PC_RAM_LED_%d" % k, PCX1 - T_ - 0.04, PCX1 - T_ - 0.004, yk, yk + 0.006, PCZ1 - 0.05, PCZ1 - 0.045, pc_led, "Study_Zone")

def pc_fan(name, c, axis, r):
    """케이스 팬: 가운데 허브 + 날개 7개 + 하얀 LED 링"""
    R = Matrix.Rotation(math.radians(90), 4, 'Y') if axis == 'x' else Matrix.Rotation(math.radians(90), 4, 'X')
    base = Matrix.Translation(c) @ R
    bmh = bmesh.new()
    bmesh.ops.create_cone(bmh, cap_ends=True, segments=24, radius1=r * 0.33, radius2=r * 0.33, depth=0.012, matrix=base)
    for k in range(7):
        a = 2 * math.pi * k / 7
        mtx = base @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((r * 0.63, 0, 0)) @ Matrix.Rotation(math.radians(28), 4, 'X') @ Matrix.Diagonal((r * 0.58, r * 0.34, 0.0015, 1))
        bmesh.ops.create_cube(bmh, size=1.0, matrix=mtx)
    finish(name + "_Blades", bmh, pc_dark, "Study_Zone", smooth=False)
    bmr = bmesh.new()
    bmesh.ops.create_cone(bmr, cap_ends=False, segments=40, radius1=r, radius2=r, depth=0.01, matrix=base)
    ring = finish(name + "_LED_Ring", bmr, pc_led, "Study_Zone", smooth=True)
    ring.modifiers.new("Thick", 'SOLIDIFY').thickness = 0.004
pc_fan("PC_CPU_Cooler_Fan", Vector((PCX1 - T_ - 0.03, PCY1 - 0.15 - 0.02, PCZ1 - 0.11)), 'x', 0.042)
box("PC_CPU_Cooler_Block", PCX1 - T_ - 0.028, PCX1 - T_ - 0.004, PCY1 - 0.21, PCY1 - 0.13, PCZ1 - 0.15, PCZ1 - 0.07, pc_dark, "Study_Zone")
for k, zc in enumerate((PCZ0 + 0.17, PCZ0 + 0.3)):
    pc_fan("PC_Front_Fan_%d" % (k + 1), Vector(((PCX0 + PCX1) / 2 + 0.005, PCY1 - 0.035, zc)), 'y', 0.06)
pc_fan("PC_Rear_Fan", Vector(((PCX0 + PCX1) / 2 + 0.03, PCY0 + 0.025, PCZ1 - 0.09)), 'y', 0.045)
pl = bpy.data.lights.new("PC_Inner_Light", 'AREA'); pl.size = 0.15; pl.energy = 2.5; pl.color = (0.92, 0.95, 1.0)
plo = bpy.data.objects.new("PC_Inner_Light", pl); plo.location = ((PCX0 + PCX1) / 2, (PCY0 + PCY1) / 2, PCZ1 - 0.02)
col("Study_Zone").objects.link(plo)

# 책장 (양쪽이 뚫린 오픈 책장)
SX0, SX1, SY0, SY1, SH = 1.45, 1.78, 0.0, 1.1, 1.85
shelf_z = [0.0, 0.46, 0.92, 1.38, SH - 0.025]
parts = [(SX0, SX1, SY0, SY0 + 0.025, 0, SH), (SX0, SX1, SY1 - 0.025, SY1, 0, SH)]
parts += [(SX0, SX1, SY0, SY1, z, z + 0.025) for z in shelf_z]
boxes("Bookshelf", parts, M["oak"], "Bookshelf")
# (꽃병, 식물은 비워 둠)
def manga_books(x_spine, y_start, z0, series, stack=None, coll="Bookshelf", mirror_x=None):
    """만화책 세트: 같은 시리즈는 같은 색 책등 + 위쪽 색 띠 + 아래 흰 라벨 + 권 번호
    (+x 쪽 책등 기준으로 만들고, mirror_x를 주면 그 x를 기준으로 뒤집어서 책등이 -x 쪽을 보게 함)"""
    def MX(lst):
        if mirror_x is None:
            return lst
        return [(2 * mirror_x - b, 2 * mirror_x - a, c, d_, e, f) for a, b, c, d_, e, f in lst]
    BW, BH = 0.112, 0.176   # 일반 만화책 크기 (11.2 x 17.6cm)
    page_m = mat("Manga_Pages", (0.93, 0.9, 0.82, 1), 0.85)
    label_m = mat("Manga_Spine_Label", (0.97, 0.96, 0.93, 1), 0.6)
    num_m = mat("Manga_Spine_Number", (0.08, 0.08, 0.09, 1), 0.5)
    pages = []
    x0 = x_spine - BW
    def number(oname, k, loc, rot):
        cu = bpy.data.curves.new(oname, 'FONT'); cu.body = str(k); cu.size = 0.008
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.0002
        cu.materials.append(num_m)
        if mirror_x is not None:
            loc = (2 * mirror_x - loc[0], loc[1], loc[2]); rot = (rot[0], rot[1], -rot[2])
        to = bpy.data.objects.new(oname, cu); to.location = loc; to.rotation_euler = rot
        col(coll).objects.link(to)
    y = y_start
    for sname, cover_rgba, band_rgba, count, t in series:
        cm = mat("Manga_%s_Cover" % sname, cover_rgba, 0.45)
        bmm = mat("Manga_%s_Band" % sname, band_rgba, 0.5)
        covers, bands, labels = [], [], []
        for k in range(count):
            y0, y1 = y, y + t
            pages.append((x0, x_spine - 0.002, y0 + 0.0008, y1 - 0.0008, z0, z0 + BH - 0.002))
            covers += [(x_spine - 0.002, x_spine, y0, y1, z0, z0 + BH), (x0, x_spine, y0, y0 + 0.0008, z0, z0 + BH), (x0, x_spine, y1 - 0.0008, y1, z0, z0 + BH)]
            bands.append((x_spine, x_spine + 0.0006, y0 + 0.0015, y1 - 0.0015, z0 + BH - 0.045, z0 + BH - 0.012))
            labels.append((x_spine, x_spine + 0.0006, y0 + 0.002, y1 - 0.002, z0 + 0.012, z0 + 0.034))
            number("Manga_%s_No_%d" % (sname, k + 1), k + 1, (x_spine + 0.0009, (y0 + y1) / 2, z0 + 0.023), (math.radians(90), 0, math.radians(90)))
            y = y1 + 0.0008
        boxes("Manga_%s_Covers" % sname, MX(covers), cm, coll)
        boxes("Manga_%s_Bands" % sname, MX(bands), bmm, coll)
        boxes("Manga_%s_Labels" % sname, MX(labels), label_m, coll)
        y += 0.012
    if stack:   # 끝에 눕혀서 쌓아 둔 몇 권
        sname, cover_rgba, band_rgba, count, t = stack
        cm = mat("Manga_%s_Cover" % sname, cover_rgba, 0.45)
        bmm = mat("Manga_%s_Band" % sname, band_rgba, 0.5)
        y0, y1 = y + 0.01, y + 0.01 + BH
        covers, bands, labels = [], [], []
        for k in range(count):
            za, zb = z0 + k * (t + 0.0005), z0 + k * (t + 0.0005) + t
            pages.append((x0, x_spine - 0.002, y0, y1 - 0.002, za + 0.0008, zb - 0.0008))
            covers += [(x_spine - 0.002, x_spine, y0, y1, za, zb), (x0, x_spine, y0, y1, za, za + 0.0008), (x0, x_spine, y0, y1, zb - 0.0008, zb)]
            bands.append((x_spine, x_spine + 0.0006, y1 - 0.045, y1 - 0.012, za + 0.0015, zb - 0.0015))
            labels.append((x_spine, x_spine + 0.0006, y0 + 0.012, y0 + 0.034, za + 0.002, zb - 0.002))
            number("Manga_%s_No_%d" % (sname, k + 1), k + 1, (x_spine + 0.0009, y0 + 0.023, (za + zb) / 2), (math.radians(90), 0, math.radians(90)))
        boxes("Manga_%s_Covers" % sname, MX(covers), cm, coll)
        boxes("Manga_%s_Bands" % sname, MX(bands), bmm, coll)
        boxes("Manga_%s_Labels" % sname, MX(labels), label_m, coll)
    boxes("Manga_Pages", MX(pages), page_m, coll)

MANGA_SERIES = [("Sky", (0.94, 0.95, 0.97, 1), (0.36, 0.6, 0.85, 1), 14, 0.015),
                ("Coral", (0.97, 0.94, 0.89, 1), (0.88, 0.46, 0.38, 1), 12, 0.0155),
                ("Night", (0.15, 0.18, 0.3, 1), (0.95, 0.8, 0.32, 1), 10, 0.016)]
manga_books(SX1 - 0.012, SY0 + 0.04, shelf_z[1] + 0.025, MANGA_SERIES, stack=("Mint", (0.9, 0.96, 0.93, 1), (0.4, 0.72, 0.6, 1), 4, 0.015),
            mirror_x=(SX0 + SX1) / 2)   # 두 번째 칸: 만화책 (책상 다리에 가려지지 않게 책등이 입구 쪽을 봄)

def chibi_figure(name, fx, fy, fz, face_rot=0.0, scale=1.0, coll="Bookshelf"):
    """오리지널 미니 피규어 (남자아이): 짧은 머리 + 세이지 그린 후드티 + 청바지 + 두 손에 청사과 + 동그란 받침 (기본: +x 쪽을 바라봄)"""
    def fm(nm, rgba, rough=0.45):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough
        m.diffuse_color = rgba
        return m
    skin = fm("Figure_Skin", (0.98, 0.86, 0.78, 1), 0.4)
    hair = fm("Figure_Hair_Brown", (0.36, 0.23, 0.16, 1), 0.35)
    hood = fm("Figure_Hoodie_Sage", (0.55, 0.67, 0.48, 1), 0.55)
    cream = fm("Figure_Cream", (0.96, 0.93, 0.86, 1), 0.5)
    shoe = fm("Figure_Shoes", (0.4, 0.27, 0.19, 1), 0.35)
    denim = fm("Figure_Jeans", (0.27, 0.34, 0.47, 1), 0.6)
    sneaker = fm("Figure_Sneakers_White", (0.95, 0.95, 0.93, 1), 0.4)
    eye = fm("Figure_Eye", (0.16, 0.1, 0.08, 1), 0.15)
    shine = fm("Figure_Eye_Shine", (1, 1, 1, 1), 0.1)
    blush = fm("Figure_Blush", (0.96, 0.62, 0.6, 1), 0.6)
    apple = fm("Figure_Apple", (0.55, 0.76, 0.3, 1), 0.3)
    base_m = fm("Figure_Base_White", (0.95, 0.95, 0.94, 1), 0.15)
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); cl.objects.link(root)
    root.location = (fx, fy, fz); root.rotation_euler = (0, 0, face_rot); root.scale = (scale, scale, scale)

    def ell(bm, c, r, rot=(0, 0, 0), seg=(24, 14)):
        mtx = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((r[0], r[1], r[2], 1))
        bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=mtx)

    def make(oname, bm, m):
        me = bpy.data.meshes.new(oname); bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(oname, me); cl.objects.link(o); o.parent = root
        return o

    HZ, HR = 0.1, 0.034   # 머리 중심 높이, 머리 반지름
    def on_head(y, z, inset):
        x = math.sqrt(max(HR * HR - y * y - (z - HZ) ** 2, 0)) - inset
        return (x, y, z), math.atan2(y, x)

    # 받침
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=0.04, radius2=0.04, depth=0.006, matrix=Matrix.Translation((0, 0, 0.003)))
    make(name + "_Base", bm, base_m)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=0.0405, radius2=0.0405, depth=0.0015, matrix=Matrix.Translation((0, 0, 0.0035)))
    make(name + "_Base_Rim", bm, hood)
    # 청바지 + 흰 운동화
    bm = bmesh.new()
    for sd in (-1, 1):
        ell(bm, (0.0, sd * 0.0095, 0.027), (0.0085, 0.0085, 0.018))
    ell(bm, (0, 0, 0.042), (0.016, 0.019, 0.008))
    make(name + "_Jeans", bm, denim)
    bm = bmesh.new()
    for sd in (-1, 1):
        ell(bm, (0.004, sd * 0.0095, 0.0095), (0.012, 0.0085, 0.0058))
    make(name + "_Sneakers", bm, sneaker)
    # 후드티 + 소매
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.02, radius2=0.016, depth=0.027, matrix=Matrix.Translation((0, 0, 0.0555)))
    ell(bm, (0, 0, 0.067), (0.016, 0.019, 0.007))
    ell(bm, (-0.017, 0, 0.073), (0.012, 0.021, 0.011))   # 등 뒤 후드
    for sd in (-1, 1):
        ell(bm, (0.01, sd * 0.019, 0.057), (0.016, 0.0065, 0.0065), (0, math.radians(25), sd * math.radians(-25)))
    make(name + "_Hoodie", bm, hood)
    bm = bmesh.new()
    for sd in (-1, 1):
        ell(bm, (0.012, sd * 0.004, 0.064), (0.0012, 0.0012, 0.006), (0, math.radians(-10), 0), seg=(8, 6))   # 후드 끈
    ell(bm, (0, 0, 0.0435), (0.0205, 0.0205, 0.0022), seg=(32, 6))   # 후드티 밑단
    make(name + "_Hoodie_Trim", bm, cream)
    # 손 + 청사과
    bm = bmesh.new()
    for sd in (-1, 1):
        ell(bm, (0.023, sd * 0.009, 0.05), (0.0045, 0.0045, 0.0045))
    make(name + "_Hands", bm, skin)
    bm = bmesh.new(); ell(bm, (0.029, 0, 0.051), (0.0085, 0.0085, 0.008)); make(name + "_Apple", bm, apple)
    bm = bmesh.new(); ell(bm, (0.029, 0, 0.0605), (0.0008, 0.0008, 0.0025), seg=(8, 6)); make(name + "_Apple_Stem", bm, shoe)
    # 머리 + 얼굴
    bm = bmesh.new(); ell(bm, (0, 0, HZ), (HR, HR, HR * 0.96), seg=(32, 18)); make(name + "_Head", bm, skin)
    bm = bmesh.new()
    for sd in (-1, 1):
        c, rz = on_head(sd * 0.0125, 0.0975, 0.0025)
        ell(bm, c, (0.003, 0.0052, 0.0072), (0, 0, rz), seg=(16, 10))
    make(name + "_Eyes", bm, eye)
    bm = bmesh.new()
    for sd in (-1, 1):
        c, rz = on_head(sd * 0.0115, 0.1005, 0.0)
        ell(bm, c, (0.0012, 0.0016, 0.0016), (0, 0, rz), seg=(8, 6))
    make(name + "_Eye_Shine", bm, shine)
    bm = bmesh.new()
    for sd in (-1, 1):
        c, rz = on_head(sd * 0.02, 0.087, 0.0016)
        ell(bm, c, (0.0018, 0.0048, 0.0026), (0, 0, rz), seg=(12, 8))
    make(name + "_Blush", bm, blush)
    bm = bmesh.new()
    c, rz = on_head(0.0, 0.0855, 0.0006)
    ell(bm, c, (0.0008, 0.0026, 0.0011), (0, 0, 0), seg=(10, 6))
    make(name + "_Mouth", bm, eye)
    # 짧은 머리: 뒷머리 + 삐죽한 앞머리 3갈래 + 짧은 구레나룻
    bm = bmesh.new()
    ell(bm, (-0.005, 0, HZ + 0.006), (0.036, 0.0365, 0.033), seg=(32, 18))
    for k, yy in enumerate((-0.016, 0.0, 0.016)):
        ell(bm, (0.022, yy, HZ + 0.02 - 0.002 * (k == 1)), (0.013, 0.012, 0.011), (0, math.radians(-25), (k - 1) * math.radians(12)))
    for sd in (-1, 1):
        ell(bm, (0.014, sd * 0.031, HZ + 0.001), (0.008, 0.005, 0.011), (0, math.radians(-10), 0))
    make(name + "_Hair", bm, hair)
    return root
chibi_figure("Shelf_Figure", (SX0 + SX1) / 2, 0.96, shelf_z[1] + 0.025, face_rot=math.pi, scale=1.25)   # 만화책 옆: 오리지널 미니 피규어 (입구 쪽을 바라봄)

def rattan_baskets(name, x0, x1, ys, z0, hgt, coll="Bookshelf"):
    """라탄 수납 바구니: 촘촘한 엮음 무늬 + 진한 테두리 + 양쪽 손잡이 구멍 (ys: 바구니마다 (y0, y1))"""
    def weave_mat(nm, c1, c2, scale):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Roughness"].default_value = 0.75
        tc = nt.nodes.new("ShaderNodeTexCoord")
        ck = nt.nodes.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = scale
        ck.inputs["Color1"].default_value = c1; ck.inputs["Color2"].default_value = c2
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = scale * 0.5
        wv.bands_direction = 'Z'
        mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'MULTIPLY'
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.45; bp.inputs["Distance"].default_value = 0.002
        nt.links.new(tc.outputs["Object"], ck.inputs["Vector"]); nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(ck.outputs["Fac"], mix.inputs[0]); nt.links.new(wv.outputs["Fac"], mix.inputs[1])
        nt.links.new(mix.outputs["Value"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        m.diffuse_color = c1
        return m
    body_m = weave_mat("Rattan_Weave", (0.76, 0.59, 0.38, 1), (0.62, 0.45, 0.28, 1), 140.0)
    rim_m = weave_mat("Rattan_Rim", (0.6, 0.43, 0.26, 1), (0.52, 0.36, 0.21, 1), 260.0)
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    for i, (y0, y1) in enumerate(ys):
        bn = "%s_%d" % (name, i + 1)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, hgt / 2)) @ Matrix.Diagonal((dx * 0.96, dy * 0.96, hgt, 1)))
        top = [f for f in bm.faces if f.normal.z > 0.9]
        for v in top[0].verts:   # 위쪽이 살짝 넓은 바구니 모양
            v.co.x *= 1 / 0.96; v.co.y *= 1 / 0.96
        bmesh.ops.delete(bm, geom=top, context='FACES_ONLY')
        me = bpy.data.meshes.new(bn); bm.to_mesh(me); bm.free(); me.materials.append(body_m)
        o = bpy.data.objects.new(bn, me); cl.objects.link(o); o.location = (cx, cy, z0)
        so = o.modifiers.new("Wall", 'SOLIDIFY'); so.thickness = 0.008; so.offset = -1
        # 손잡이 구멍 (앞뒤 양쪽)
        cut = bpy.data.meshes.new(bn + "_Handle_Cutter")
        bmc = bmesh.new()
        bmesh.ops.create_cone(bmc, cap_ends=True, segments=32, radius1=1.0, radius2=1.0, depth=1.0,
                              matrix=Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Diagonal((0.016, 0.045, dx + 0.1, 1)))
        bmc.to_mesh(cut); bmc.free()
        co = bpy.data.objects.new(bn + "_Handle_Cutter", cut); cl.objects.link(co)
        co.parent = o; co.location = (0, 0, hgt - 0.045)
        co.display_type = 'WIRE'; co.hide_render = True
        bo = o.modifiers.new("Handles", 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = co
        try:
            bo.solver = 'EXACT'
        except Exception:
            pass
        bv = o.modifiers.new("Round", 'BEVEL'); bv.width = 0.004; bv.segments = 2; bv.limit_method = 'ANGLE'
        # 진한 테두리
        rx, ry, t = dx / 2 + 0.003, dy / 2 + 0.003, 0.012
        bm = bmesh.new()
        for a, b_, c, d_ in ((-rx, rx, -ry, -ry + t), (-rx, rx, ry - t, ry), (-rx, -rx + t, -ry, ry), (rx - t, rx, -ry, ry)):
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(((a + b_) / 2, (c + d_) / 2, hgt - 0.006)) @ Matrix.Diagonal((b_ - a, d_ - c, 0.016, 1)))
        rme = bpy.data.meshes.new(bn + "_Rim"); bm.to_mesh(rme); bm.free(); rme.materials.append(rim_m)
        ro = bpy.data.objects.new(bn + "_Rim", rme); cl.objects.link(ro); ro.parent = o
        ro.modifiers.new("Round", 'BEVEL').width = 0.004
rattan_baskets("Shelf_Rattan_Basket", SX0 + 0.015, SX1 - 0.015, [(0.05, 0.37), (0.39, 0.71), (0.73, 1.05)], shelf_z[0] + 0.025, 0.26)   # 맨 아래 칸: 라탄 바구니 3개

def basket_blanket(name, x0, x1, y0, y1, rim_z, coll="Bookshelf"):
    """라탄 바구니 속 접은 니트 담요: 위로 폭신하게 올라옴"""
    nm = "Blanket_Knit_Sage"
    if nm in bpy.data.materials:
        km = bpy.data.materials[nm]
    else:
        km = bpy.data.materials.new(nm); km.use_nodes = True
        nt = km.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (0.6, 0.69, 0.54, 1); b.inputs["Roughness"].default_value = 0.95
        for key in ("Sheen Weight", "Sheen"):
            if key in b.inputs:
                b.inputs[key].default_value = 0.6; break
        tc = nt.nodes.new("ShaderNodeTexCoord")
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 160.0; wv.bands_direction = 'Y'
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.003
        nt.links.new(tc.outputs["Object"], wv.inputs["Vector"]); nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        km.diffuse_color = (0.6, 0.69, 0.54, 1)
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    # 접힌 담요 덩어리 (바구니 안 → 테두리 위로 볼록)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    zc0, zc1 = rim_z - 0.12, rim_z + 0.028
    for v in bm.verts:
        u = v.co.z + 0.5
        bulge = 1.0 + 0.04 * (1 - (2 * v.co.x) ** 2) * u
        v.co.x *= (x1 - x0) * bulge; v.co.y *= (y1 - y0)
        v.co.z = zc0 + (zc1 - zc0) * u
        if u > 0.99:   # 위가 둥글게 부풀어 오름
            v.co.z += 0.012 * (1 - (2 * v.co.x / (x1 - x0)) ** 2) * (1 - (2 * v.co.y / (y1 - y0)) ** 2)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(km)
    o = bpy.data.objects.new(name, me); cl.objects.link(o); o.location = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    o.modifiers.new("Soft", 'SUBSURF').levels = 2
    # 접힌 선 2줄 (살짝 파인 홈 느낌의 얇은 띠)
    bm = bmesh.new()
    for k in (1, 2):
        yy = y0 + (y1 - y0) * k / 3 - (y0 + y1) / 2
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, yy, zc1 + 0.009)) @ Matrix.Diagonal((x1 - x0 - 0.04, 0.004, 0.004, 1)))
    fl = bpy.data.meshes.new(name + "_Folds"); bm.to_mesh(fl); bm.free(); fl.materials.append(km)
    fo = bpy.data.objects.new(name + "_Folds", fl); cl.objects.link(fo); fo.parent = o
    fo.modifiers.new("Soft", 'SUBSURF').levels = 2
    return o
basket_blanket("Shelf_Basket_Blanket", SX0 + 0.025, SX1 - 0.025, 0.745, 1.035, shelf_z[0] + 0.025 + 0.26)   # 입구에서 제일 먼 바구니: 세이지 니트 담요

def basket_yarn(name, balls, needle_ball=None, seed=5, coll="Bookshelf"):
    """털실 뭉치: 공 모양 위에 실을 여러 방향으로 감은 결 + 한 뭉치에 원목 뜨개바늘 2개 (balls: (x, y, z, 반지름, 색이름))"""
    rnd = random.Random(seed)
    cols = {"Cream": (0.94, 0.9, 0.8, 1), "Sage": (0.56, 0.67, 0.49, 1), "Terracotta": (0.76, 0.45, 0.33, 1),
            "Oat": (0.82, 0.74, 0.6, 1), "Pink": (0.9, 0.7, 0.68, 1)}
    def ym(cn):
        nm = "Yarn_" + cn
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = cols[cn]; b.inputs["Roughness"].default_value = 0.95
        for key in ("Sheen Weight", "Sheen"):
            if key in b.inputs:
                b.inputs[key].default_value = 0.7; break
        m.diffuse_color = cols[cn]
        return m
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    per = {}
    for (bx, by, bz, r, cn) in balls:
        bm = per.setdefault(cn, bmesh.new())
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r * 0.97, matrix=Matrix.Translation((bx, by, bz)))
        for _ in range(26):   # 실 감은 결: 여러 방향의 둥근 실 가닥
            nrm = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            u = nrm.orthogonal().normalized(); v = nrm.cross(u)
            R, rr, N, Mn = r * (0.99 + rnd.uniform(0, 0.025)), r * 0.06, 56, 6
            ring = []
            for a in range(N):
                th = 2 * math.pi * a / N
                cdir = u * math.cos(th) + v * math.sin(th)
                row = []
                for b_ in range(Mn):
                    ph = 2 * math.pi * b_ / Mn
                    p = Vector((bx, by, bz)) + cdir * (R + rr * math.cos(ph)) + nrm * (rr * math.sin(ph))
                    row.append(bm.verts.new(p))
                ring.append(row)
            for a in range(N):
                for b_ in range(Mn):
                    bm.faces.new((ring[a][b_], ring[(a + 1) % N][b_], ring[(a + 1) % N][(b_ + 1) % Mn], ring[a][(b_ + 1) % Mn]))
    for cn, bm in per.items():
        me = bpy.data.meshes.new("%s_%s" % (name, cn)); bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(ym(cn))
        o = bpy.data.objects.new(me.name, me); cl.objects.link(o)
    if needle_ball is not None:   # 원목 뜨개바늘 2개 (X자로 꽂힘)
        bx, by, bz, r, _ = balls[needle_ball]
        wood = bpy.data.materials.get("Knitting_Needle_Wood")
        if wood is None:
            wood = bpy.data.materials.new("Knitting_Needle_Wood"); wood.use_nodes = True
            b = wood.node_tree.nodes.get("Principled BSDF")
            b.inputs["Base Color"].default_value = (0.72, 0.53, 0.33, 1); b.inputs["Roughness"].default_value = 0.4
            wood.diffuse_color = (0.72, 0.53, 0.33, 1)
        bm = bmesh.new()
        for sd in (-1, 1):
            rot = Euler((sd * math.radians(22), math.radians(14), 0)).to_matrix().to_4x4()
            base = Matrix.Translation((bx, by, bz - r * 0.3)) @ rot
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0028, radius2=0.0028, depth=0.19, matrix=base @ Matrix.Translation((0, 0, 0.095)))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0012, radius2=0.0028, depth=0.012, matrix=base @ Matrix.Translation((0, 0, -0.006)))
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.0055, matrix=base @ Matrix.Translation((0, 0, 0.19)))
        me = bpy.data.meshes.new(name + "_Needles"); bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(wood)
        o = bpy.data.objects.new(me.name, me); cl.objects.link(o)
RZ = shelf_z[0] + 0.025 + 0.26   # 바구니 테두리 높이
basket_yarn("Shelf_Basket_Yarn", [(1.545, 0.47, RZ - 0.1, 0.044, "Oat"), (1.69, 0.48, RZ - 0.1, 0.044, "Cream"), (1.55, 0.63, RZ - 0.1, 0.044, "Pink"), (1.685, 0.62, RZ - 0.1, 0.044, "Sage"),
                                  (1.54, 0.46, RZ - 0.03, 0.046, "Cream"), (1.69, 0.47, RZ - 0.035, 0.044, "Terracotta"), (1.615, 0.55, RZ - 0.02, 0.048, "Sage"),
                                  (1.54, 0.64, RZ - 0.032, 0.045, "Terracotta"), (1.69, 0.635, RZ - 0.03, 0.046, "Oat")])   # 가운데 바구니: 털실 뭉치

def basket_plushies(name, specs, rim_x, rim_z, coll="Bookshelf"):
    """바구니 속 작은 인형들 (얼굴 빼꼼 + 앞발을 테두리에 걸침): 토끼 / 곰 / 고양이 (specs: (종류, x, y, 머리중심z, 방향))"""
    def pm(nm, rgba, sheen=0.7):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = 0.9
        for key in ("Sheen Weight", "Sheen"):
            if key in b.inputs:
                b.inputs[key].default_value = sheen; break
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 800.0
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.3; bp.inputs["Distance"].default_value = 0.001
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        m.diffuse_color = rgba
        return m
    fur = {"bunny": pm("Plush_Bunny_Cream", (0.95, 0.93, 0.88, 1)), "bear": pm("Plush_Bear_Oat", (0.78, 0.63, 0.47, 1)),
           "cat": pm("Plush_Cat_Gray", (0.74, 0.74, 0.76, 1))}
    light = pm("Plush_Muzzle_Cream", (0.96, 0.92, 0.84, 1))
    pink = pm("Plush_Pink", (0.94, 0.66, 0.66, 1), 0.3)
    dark = pm("Plush_Eye_Dark", (0.1, 0.07, 0.06, 1), 0.0)
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection

    def ell(bm, c, r, rot=(0, 0, 0), seg=(20, 12)):
        mtx = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((r[0], r[1], r[2], 1))
        bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=mtx)

    for i, (kind, px, py, pz, face) in enumerate(specs):
        root = bpy.data.objects.new("%s_%d_%s" % (name, i + 1, kind.capitalize()), None); cl.objects.link(root)
        root.location = (px, py, pz); root.rotation_euler = (0, 0, face)
        R = 0.044
        paw_x, rim_dz = abs(px - rim_x) - 0.004, rim_z - pz   # 머리 중심 기준 테두리까지 거리
        parts = {}
        def bm_of(m):
            return parts.setdefault(m.name, (m, bmesh.new()))[1]
        f = fur[kind]
        ell(bm_of(f), (0, 0, 0), (R * 0.95, R, R * 0.92), seg=(28, 16))          # 머리
        ell(bm_of(f), (-0.008, 0, -0.15), (0.046, 0.05, 0.14))                   # 몸 (바구니 바닥까지)
        for sd in (-1, 1):   # 팔: 앞발을 바구니 테두리 위에 걸침
            sh, pw = Vector((0.0, sd * 0.034, -0.055)), Vector((paw_x, sd * 0.03, rim_dz + 0.008))
            dv = pw - sh
            ell(bm_of(f), tuple((sh + pw) / 2), (dv.length / 2 + 0.006, 0.012, 0.012), tuple(dv.to_track_quat('X', 'Z').to_euler()))
            ell(bm_of(f), tuple(pw), (0.013, 0.012, 0.009))
        def on_face(y, z, inset):
            x = math.sqrt(max((R * 0.95) ** 2 * (1 - (y / R) ** 2 - (z / (R * 0.92)) ** 2), 0)) - inset
            return (x, y, z), math.atan2(y, max(x, 1e-4))
        for sd in (-1, 1):
            c, rz = on_face(sd * 0.015, 0.006, 0.0015)
            ell(bm_of(dark), c, (0.0025, 0.0042, 0.0048), (0, 0, rz), seg=(10, 8))
            c, rz = on_face(sd * 0.026, -0.008, 0.001)
            ell(bm_of(pink), c, (0.0015, 0.006, 0.0035), (0, 0, rz), seg=(10, 6))
        if kind == "bunny":
            for sd in (-1, 1):
                ell(bm_of(f), (-0.006, sd * 0.017, R + 0.03), (0.009, 0.014, 0.04), (sd * math.radians(-12), math.radians(-8), 0))
                ell(bm_of(pink), (0.0025, sd * 0.017, R + 0.03), (0.002, 0.008, 0.03), (sd * math.radians(-12), math.radians(-8), 0), seg=(12, 8))
            c, _ = on_face(0, -0.007, 0.0)
            ell(bm_of(pink), c, (0.0022, 0.0035, 0.0025), seg=(10, 6))
        elif kind == "bear":
            for sd in (-1, 1):
                ell(bm_of(f), (-0.004, sd * 0.031, R * 0.75), (0.009, 0.015, 0.015))
                ell(bm_of(light), (0.002, sd * 0.031, R * 0.75), (0.004, 0.009, 0.009), seg=(12, 8))
            ell(bm_of(light), (R * 0.8, 0, -0.012), (0.014, 0.019, 0.013))
            ell(bm_of(dark), (R * 0.8 + 0.012, 0, -0.008), (0.003, 0.0055, 0.004), seg=(10, 6))
        else:   # cat
            for sd in (-1, 1):
                mtx = Matrix.Translation((-0.002, sd * 0.026, R * 0.82)) @ Euler((sd * math.radians(-20), 0, 0)).to_matrix().to_4x4()
                bmesh.ops.create_cone(bm_of(f), cap_ends=True, segments=16, radius1=0.015, radius2=0.002, depth=0.03,
                                      matrix=mtx @ Matrix.Translation((0, 0, 0.012)) @ Matrix.Diagonal((0.6, 1, 1, 1)))
                bmesh.ops.create_cone(bm_of(pink), cap_ends=True, segments=12, radius1=0.008, radius2=0.001, depth=0.02,
                                      matrix=mtx @ Matrix.Translation((0.006, 0, 0.01)) @ Matrix.Diagonal((0.3, 1, 1, 1)))
            c, _ = on_face(0, -0.008, 0.0)
            ell(bm_of(pink), c, (0.002, 0.004, 0.0025), seg=(10, 6))
        for mname, (m, bm) in parts.items():
            me = bpy.data.meshes.new("%s_%s" % (root.name, mname)); bm.to_mesh(me); bm.free()
            for p in me.polygons:
                p.use_smooth = True
            me.materials.append(m)
            o = bpy.data.objects.new(me.name, me); cl.objects.link(o); o.parent = root
basket_plushies("Shelf_Basket_Plush", [("bunny", 1.535, 0.115, RZ + 0.038, math.pi + 0.12), ("bear", 1.54, 0.21, RZ + 0.042, math.pi), ("cat", 1.535, 0.305, RZ + 0.038, math.pi - 0.12)], SX0 + 0.012, RZ)   # 입구 쪽 바구니: 얼굴만 빼꼼 내민 인형 3개

def mini_cushions(name, specs, coll="Bookshelf"):
    """작은 쿠션: 가운데가 볼록하고 모서리가 뾰족하게 모이는 쿠션 모양 (specs: (x, y, 아래z, 크기, 두께, 뒤로 기울기, 회전, 재질이름))"""
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    for i, (cx, cy, z0, S, T, lean, turn, mname) in enumerate(specs):
        m = bpy.data.materials.get(mname)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=10, use_grid_fill=True)
        for v in bm.verts:
            ny, nz = 2 * v.co.y, 2 * v.co.z
            puff = 0.25 + 0.75 * max(1 - abs(ny) ** 2.5, 0) * max(1 - abs(nz) ** 2.5, 0)
            v.co.x *= T * puff
            v.co.y *= S * (1 - 0.06 * (1 - abs(nz)))   # 옆선이 살짝 안으로 들어감
            v.co.z *= S * (1 - 0.06 * (1 - abs(ny)))
        me = bpy.data.meshes.new("%s_%d" % (name, i + 1)); bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(me.name, me); cl.objects.link(o)
        o.location = (cx, cy, z0 + S / 2); o.rotation_euler = (0, math.radians(lean), math.radians(turn))
        o.modifiers.new("Soft", 'SUBSURF').levels = 2
mini_cushions("Shelf_Basket_Cushion", [(1.7, 0.135, RZ - 0.07, 0.14, 0.055, 14, 8, "Pillow_Plaid_Sage_Deeper"), (1.705, 0.285, RZ - 0.075, 0.14, 0.055, 16, -8, "Pillow_Sage")])   # 인형 뒤 미니 쿠션 2개

def cup_noodles(name, items, tex_dir, seed=3, coll="Bookshelf"):
    """컵라면 (상표 없는 직접 그린 디자인): 흰 종이컵 + 맛별 그림 라벨(글자가 양쪽을 봄) + 그림 뚜껑 + 뜯는 탭
    items: (x, y, 바닥z, 종류 'cup'/'bowl', 맛)"""
    rnd = random.Random(seed)
    def img_mat(nm, path):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Roughness"].default_value = 0.38
        tx = nt.nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.load(path); img.pack(); tx.image = img
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
        return m
    def plain(nm, rgba, rough):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough
        m.diffuse_color = rgba
        return m
    paper = plain("CupNoodle_Paper_White", (0.95, 0.94, 0.9, 1), 0.5)
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    meshes = {}
    def get(m):
        if m.name not in meshes:
            bm = bmesh.new(); meshes[m.name] = (m, bm, bm.loops.layers.uv.new())
        return meshes[m.name][1], meshes[m.name][2]
    def tube(m, x, y, za, zb, ra, rb, N=48, phase=0.0, bottom=False):
        bm, uv = get(m)
        bot = [bm.verts.new((x + ra * math.cos(2 * math.pi * i / N + phase), y + ra * math.sin(2 * math.pi * i / N + phase), za)) for i in range(N + 1)]
        top = [bm.verts.new((x + rb * math.cos(2 * math.pi * i / N + phase), y + rb * math.sin(2 * math.pi * i / N + phase), zb)) for i in range(N + 1)]
        for i in range(N):
            f = bm.faces.new((bot[i], bot[i + 1], top[i + 1], top[i])); f.smooth = True
            for lp, (u, v) in zip(f.loops, ((i / N, 0), ((i + 1) / N, 0), ((i + 1) / N, 1), (i / N, 1))):
                lp[uv].uv = (u, v)
        if bottom:
            bm.faces.new(bot[:N][::-1])
    def disc(m, x, y, z, r, N=48):
        bm, uv = get(m)
        ring = [bm.verts.new((x + r * math.cos(2 * math.pi * i / N), y + r * math.sin(2 * math.pi * i / N), z)) for i in range(N)]
        f = bm.faces.new(ring)
        for lp in f.loops:
            th = math.atan2(lp.vert.co.y - y, lp.vert.co.x - x)
            lp[uv].uv = (0.5 - 0.485 * math.sin(th), 0.5 + 0.485 * math.cos(th))   # 입구 쪽에서 볼 때 글자가 똑바로
    for (x, y, z0, kind, fl) in items:
        H_, rb_, rt_ = (0.095, 0.036, 0.047) if kind == "cup" else (0.07, 0.056, 0.076)
        rr = lambda z: rb_ + (rt_ - rb_) * (z - z0) / H_
        lab = img_mat("CupNoodle_Label_" + fl, os.path.join(tex_dir, "label_%s.png" % fl))
        lid = img_mat("CupNoodle_Lid_" + fl, os.path.join(tex_dir, "lid_%s.png" % fl))
        ph = math.pi / 2 + rnd.uniform(-0.25, 0.25)   # 라벨 글자가 입구 쪽(-x)과 책상 쪽(+x)을 보게
        tube(paper, x, y, z0, z0 + H_, rb_, rt_, bottom=True)
        la, lb = z0 + 0.008, z0 + H_ - 0.007
        tube(lab, x, y, la, lb, rr(la) + 0.0008, rr(lb) + 0.0008, phase=ph)
        tube(paper, x, y, z0 + H_ - 0.004, z0 + H_ + 0.001, rt_ + 0.0022, rt_ + 0.0022)          # 위 테두리 (말린 종이)
        tube(paper, x, y, z0 + H_ + 0.001, z0 + H_ + 0.0028, rt_ + 0.0016, rt_ + 0.0016)
        disc(lid, x, y, z0 + H_ + 0.0028, rt_ + 0.0016)                                           # 그림 뚜껑
        bm, _ = get(paper)
        a = math.pi + rnd.uniform(-0.6, 0.6)   # 뜯는 탭 (입구 쪽)
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((x + math.cos(a) * (rt_ + 0.009), y + math.sin(a) * (rt_ + 0.009), z0 + H_ + 0.002))
                              @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Diagonal((0.018, 0.016, 0.0012, 1)))
    for mname, (m, bm, uv) in meshes.items():
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("%s_%s" % (name, mname)); bm.to_mesh(me); bm.free()
        me.materials.append(m)
        o = bpy.data.objects.new(me.name, me); cl.objects.link(o)
Z4 = shelf_z[3] + 0.025   # 맨 위 칸 바닥
_cups = []
for _x, _fl in ((1.535, "Spicy"), (1.695, "Udon")):   # 큰 사발 2개씩 쌓기
    _cups += [(_x, 0.12, Z4, "bowl", _fl), (_x, 0.12, Z4 + 0.0731, "bowl", _fl)]
_cols = ["Spicy", "Spicy", "Kimchi", "Shrimp", "Jjajang", "Cheese", "Kimchi"]
for _j, _fl in enumerate(_cols):
    for _x in (1.535, 1.695):
        _cups.append((_x, 0.275 + 0.11 * _j, Z4, "cup", _fl))
for _j, _x in ((0, 1.535), (0, 1.695), (1, 1.535), (1, 1.695), (3, 1.695), (5, 1.535)):
    _cups.append((_x, 0.275 + 0.11 * _j, Z4 + 0.0981, "cup", _cols[_j]))
cup_noodles("Shelf_Cup_Noodles", _cups, os.path.join(ART_DIR, "ramen"))   # 맨 위 칸: 컵라면들

def music_merch(name, x_front, y_lp, y_cds, y_stand, z0, tex_dir, coll="Bookshelf"):
    """음반·굿즈 진열 (직접 그린 오리지널 디자인): LP 1장(받침대 + 옆으로 살짝 빼낸 레코드) + CD 2장(세워 둠) + 청사과 캐릭터 아크릴 스탠드
    모두 입구 쪽(-x)을 바라봄"""
    cl = bpy.data.collections.get(coll) or bpy.context.scene.collection
    def img_mat(nm, path, rough=0.4, alpha=False):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
        b.inputs["Roughness"].default_value = rough
        tx = nt.nodes.new("ShaderNodeTexImage"); img = bpy.data.images.load(path); img.pack(); tx.image = img
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
        if alpha:
            nt.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
            for attr, val in (("surface_render_method", "DITHERED"), ("blend_method", "HASHED")):
                try:
                    setattr(m, attr, val)
                except Exception:
                    pass
        return m
    def plain(nm, rgba, rough=0.4, metal=0.0):
        if nm in bpy.data.materials:
            return bpy.data.materials[nm]
        m = bpy.data.materials.new(nm); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = rgba; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        m.diffuse_color = rgba
        return m
    card = plain("Merch_Sleeve_Card", (0.95, 0.94, 0.9, 1), 0.6)
    vinyl = plain("Merch_Vinyl_Black", (0.02, 0.02, 0.025, 1), 0.18)
    case = plain("Merch_CD_Case", (0.85, 0.86, 0.88, 1), 0.08)
    wood = bpy.data.materials.get("Wood_Oak_Light") or plain("Merch_Stand_Wood", (0.72, 0.56, 0.38, 1), 0.5)
    acryl = plain("Merch_Acrylic_Base", (0.96, 0.97, 0.98, 1), 0.05)

    def obj(oname, bm, m, loc=(0, 0, 0), rot=(0, 0, 0), smooth=False):
        me = bpy.data.meshes.new(oname); bm.to_mesh(me); bm.free()
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(oname, me); cl.objects.link(o); o.location = loc; o.rotation_euler = rot
        return o
    def front_plane(oname, w, h, x, zc, m, loc, rot, yc=0.0):
        """-x 쪽을 보는 그림 판 (왼→오른쪽이 보는 사람 기준)"""
        bm = bmesh.new(); uv = bm.loops.layers.uv.new()
        vs = [bm.verts.new((x, yc + w / 2, zc - h / 2)), bm.verts.new((x, yc - w / 2, zc - h / 2)),
              bm.verts.new((x, yc - w / 2, zc + h / 2)), bm.verts.new((x, yc + w / 2, zc + h / 2))]
        f = bm.faces.new(vs)
        for lp, t in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[uv].uv = t
        bmesh.ops.recalc_face_normals(bm, faces=[f])
        if f.normal.x > 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
        return obj(oname, bm, m, loc, rot)
    def boxm(bm, x0, x1, y0, y1, za, zb):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (za + zb) / 2)) @ Matrix.Diagonal((x1 - x0, y1 - y0, zb - za, 1)))
    # LP 받침대 (원목 턱)
    S = 0.315
    bm = bmesh.new(); boxm(bm, x_front, x_front + 0.12, y_lp - 0.17, y_lp + 0.17, z0, z0 + 0.012); boxm(bm, x_front, x_front + 0.012, y_lp - 0.17, y_lp + 0.17, z0, z0 + 0.03)
    st = obj(name + "_LP_Stand", bm, wood); st.modifiers.new("Round", 'BEVEL').width = 0.002
    lp_loc, lp_rot = (x_front + 0.02, y_lp, z0 + 0.012), (0, math.radians(14), 0)
    bm = bmesh.new(); boxm(bm, 0, 0.004, -S / 2, S / 2, 0, S)
    obj(name + "_LP_Sleeve", bm, card, lp_loc, lp_rot)
    front_plane(name + "_LP_Cover", S, S, -0.0004, S / 2, img_mat("Merch_LP_Cover", os.path.join(tex_dir, "lp_cover.png")), lp_loc, lp_rot)
    # 옆으로 살짝 빼낸 레코드
    vy, vz, R_ = S * 0.47, S / 2 + 0.004, 0.15
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=R_, radius2=R_, depth=0.0018,
                          matrix=Matrix.Translation((0.006, vy, vz)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    obj(name + "_LP_Vinyl", bm, vinyl, lp_loc, lp_rot, smooth=False)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    ring = [bm.verts.new((0.0049, vy + 0.05 * math.cos(2 * math.pi * i / 40), vz + 0.05 * math.sin(2 * math.pi * i / 40))) for i in range(40)]
    f = bm.faces.new(ring)
    for lp in f.loops:
        lp[uv].uv = (0.5 - 0.5 * (lp.vert.co.y - vy) / 0.05, 0.5 + 0.5 * (lp.vert.co.z - vz) / 0.05)
    bmesh.ops.recalc_face_normals(bm, faces=[f])
    if f.normal.x > 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    obj(name + "_LP_Label", bm, img_mat("Merch_LP_Label", os.path.join(tex_dir, "lp_label.png")), lp_loc, lp_rot)
    # CD 2장 (살짝 기대어 세움)
    for k, (yc, tex) in enumerate(zip(y_cds, ("cd_cover_a.png", "cd_cover_b.png"))):
        cw, ch = 0.142, 0.125
        loc, rot = (x_front + 0.03, yc, z0), (0, math.radians(16), 0)
        bm = bmesh.new(); boxm(bm, 0, 0.0104, -cw / 2, cw / 2, 0, ch)
        obj(name + "_CD_%d_Case" % (k + 1), bm, case, loc, rot)
        front_plane(name + "_CD_%d_Cover" % (k + 1), cw - 0.008, ch - 0.004, -0.0004, ch / 2, img_mat("Merch_CD_Cover_%d" % (k + 1), os.path.join(tex_dir, tex)), loc, rot, yc=0.003)
        bm = bmesh.new(); boxm(bm, 0.019, 0.045, -0.03, 0.03, 0, 0.03)   # 뒤 받침
        obj(name + "_CD_%d_Rest" % (k + 1), bm, acryl, loc, (0, 0, 0))
    # 청사과 캐릭터 아크릴 스탠드
    A = 0.13
    loc = (x_front + 0.06, y_stand, z0)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=1, radius2=1, depth=0.006, matrix=Matrix.Translation((0, 0, 0.003)) @ Matrix.Diagonal((0.03, 0.05, 1, 1)))
    obj(name + "_Acrylic_Base", bm, acryl, loc, (0, 0, 0), smooth=True)
    front_plane(name + "_Acrylic_Apple", A, A, 0.0, A / 2 + 0.004, img_mat("Merch_Acrylic_Apple", os.path.join(tex_dir, "acrylic_apple.png"), 0.15, alpha=True), loc, (0, 0, 0))
music_merch("Shelf_Merch", SX0 + 0.03, 0.2, (0.6, 0.78), 0.96, shelf_z[2] + 0.025, os.path.join(ART_DIR, "merch"))   # 세 번째 칸: 음반·굿즈 (청사과 테마)


# =============== 의자 ①, ② (베이지 부클레 라운드 체어) ===============
def armchair(name, x, y):
    cyl(name + "_Seat", 0.25, 0.38, 0.47, x, y, M["boucle"], "Study_Zone", 40)
    cyl(name + "_Back_Outer", 0.29, 0.38, 0.75, x, y, M["boucle"], "Study_Zone", 48)
    back = bpy.data.objects[name + "_Back_Outer"]
    inner = cyl(name + "_Cut_Inner", 0.23, 0.3, 0.9, x, y, M["boucle"], "Study_Zone", 48)
    front = box(name + "_Cut_Front", x - 0.4, x + 0.4, y - 0.4, y - 0.02, 0.3, 0.9, M["boucle"], "Study_Zone")
    for cutter in (inner, front):
        b = back.modifiers.new("Cut_" + cutter.name, 'BOOLEAN'); b.operation = 'DIFFERENCE'; b.object = cutter
        cutter.hide_render = True; cutter.hide_viewport = True
    for lx, ly in ((-0.17, -0.17), (0.17, -0.17), (-0.17, 0.17), (0.17, 0.17)):
        cyl(name + "_Leg_%d_%d" % (int(lx > 0), int(ly > 0)), 0.018, 0.0, 0.38, x + lx, y + ly, M["oak"], "Study_Zone", 12, r2=0.014)
def gaming_chair(name, cx, cy, coll="Study_Zone"):
    """게이밍 의자: 높은 등받이(헤드레스트+어깨 날개), 버킷 시트, 팔걸이, 5발 바퀴 다리 (등받이는 +y 쪽)"""
    gc_white = mat("Gaming_Chair_White_Leather", (0.93, 0.93, 0.91, 1), 0.35)
    gc_accent = mat("Gaming_Chair_Sage_Accent", (0.52, 0.64, 0.45, 1), 0.4)
    gc_black = mat("Gaming_Chair_Black", (0.06, 0.06, 0.07, 1), 0.4)
    gc_chrome = mat("Gaming_Chair_Chrome", (0.8, 0.8, 0.82, 1), 0.15, 1.0)
    SEAT_Z = 0.47
    # 5발 다리 + 바퀴
    bm = bmesh.new()
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        mtx = Matrix.Translation((cx + 0.16 * math.cos(a), cy + 0.16 * math.sin(a), 0.085)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(math.radians(-6), 4, 'Y') @ Matrix.Diagonal((0.32, 0.05, 0.035, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)
    base = finish(name + "_Base", bm, gc_black, coll)
    base.modifiers.new("Round", 'BEVEL').width = 0.008
    bw = bmesh.new()
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        for side in (-1, 1):
            p = Matrix.Translation((cx + 0.3 * math.cos(a) + side * 0.012 * -math.sin(a), cy + 0.3 * math.sin(a) + side * 0.012 * math.cos(a), 0.03))
            bmesh.ops.create_uvsphere(bw, u_segments=14, v_segments=8, radius=0.03, matrix=p @ Matrix.Diagonal((1, 1, 1, 1)))
    finish(name + "_Casters", bw, gc_black, coll, smooth=True)
    cyl(name + "_Gas_Lift", 0.024, 0.1, 0.4, cx, cy, gc_chrome, coll, 24)
    cyl(name + "_Lift_Cover", 0.035, 0.1, 0.24, cx, cy, gc_black, coll, 24, r2=0.03)
    box(name + "_Seat_Plate", cx - 0.14, cx + 0.14, cy - 0.12, cy + 0.12, 0.4, 0.42, gc_black, coll)
    # 버킷 시트 (가운데 + 양옆 볼록한 날개)
    seat = box(name + "_Seat", cx - 0.25, cx + 0.25, cy - 0.25, cy + 0.22, 0.42, SEAT_Z + 0.03, gc_white, coll)
    sb = seat.modifiers.new("Round", 'BEVEL'); sb.width = 0.03; sb.segments = 4
    for sd in (-1, 1):
        bol = box(name + "_Seat_Bolster_%s" % ("L" if sd > 0 else "R"), cx + sd * 0.25 - 0.045, cx + sd * 0.25 + 0.045, cy - 0.24, cy + 0.2, 0.45, SEAT_Z + 0.08, gc_accent, coll)
        bb = bol.modifiers.new("Round", 'BEVEL'); bb.width = 0.025; bb.segments = 4
    # 등받이 (윤곽선 → 두께 → 둥근 모서리), 뒤로 살짝 기울임
    H, TH = 0.84, 0.11
    prof = [(0.0, 0.25), (0.2, 0.26), (0.36, 0.27), (0.52, 0.27), (0.6, 0.31), (0.66, 0.29), (0.7, 0.21),
            (0.76, 0.17), (0.8, 0.19), (0.92, 0.19), (0.97, 0.16), (1.0, 0.1)]
    outline = [(hw, v * H) for v, hw in prof] + [(-hw, v * H) for v, hw in reversed(prof)]
    def back_obj(oname, pts, y0, y1, m, bev):
        bmb = bmesh.new()
        f = bmb.faces.new([bmb.verts.new((x, y0, z)) for x, z in pts])
        ext = bmesh.ops.extrude_face_region(bmb, geom=[f])
        bmesh.ops.translate(bmb, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, y1 - y0, 0))
        bmesh.ops.recalc_face_normals(bmb, faces=bmb.faces[:])
        o = finish(oname, bmb, m, coll)
        o.location = (cx, cy + 0.2, SEAT_Z + 0.01)
        o.rotation_euler = (math.radians(-12), 0, 0)
        bv = o.modifiers.new("Round", 'BEVEL'); bv.width = bev; bv.segments = 4; bv.limit_method = 'ANGLE'
        return o
    back_obj(name + "_Backrest", outline, 0.0, TH, gc_white, 0.03)
    # 등받이 앞면 세이지 그린 줄무늬 2개 + 헤드 쿠션 + 허리 쿠션
    for sd in (-1, 1):
        stripe = [(sd * 0.13, 0.02), (sd * 0.2, 0.02), (sd * 0.2, H * 0.6), (sd * 0.15, H * 0.68), (sd * 0.13, H * 0.66)]
        if sd < 0:
            stripe = stripe[::-1]
        back_obj(name + "_Back_Stripe_%s" % ("L" if sd > 0 else "R"), stripe, -0.006, 0.0, gc_accent, 0.002)
    head = [(-0.13, H * 0.8), (0.13, H * 0.8), (0.13, H * 0.9), (-0.13, H * 0.9)]
    back_obj(name + "_Head_Pillow", head, -0.045, 0.0, gc_accent, 0.02)
    lumbar = [(-0.17, H * 0.18), (0.17, H * 0.18), (0.17, H * 0.32), (-0.17, H * 0.32)]
    back_obj(name + "_Lumbar_Pillow", lumbar, -0.05, 0.0, gc_white, 0.025)
    # 뒷면: 앞면과 같은 세이지 줄무늬 + 위쪽 띠 + 가운데 청사과 그림
    for sd in (-1, 1):
        stripe = [(sd * 0.13, 0.02), (sd * 0.2, 0.02), (sd * 0.2, H * 0.6), (sd * 0.15, H * 0.68), (sd * 0.13, H * 0.66)]
        if sd < 0:
            stripe = stripe[::-1]
        back_obj(name + "_Rear_Stripe_%s" % ("L" if sd > 0 else "R"), stripe, TH, TH + 0.006, gc_accent, 0.002)
    # 머리 부분: 머리 모양을 따라 둥근 연두색 무늬 (머리보다 작게)
    def head_loop(a, b, zc, n=48, ex=2.6):
        pts = []
        for k in range(n):
            t = 2 * math.pi * k / n
            c, sn = math.cos(t), math.sin(t)
            x = a * math.copysign(abs(c) ** (2 / ex), c)
            z = b * math.copysign(abs(sn) ** (2 / ex), sn)
            x *= 1 - 0.12 * max(z / b, 0)   # 위쪽은 머리처럼 살짝 좁게
            pts.append((x, zc + z))
        return pts
    back_obj(name + "_Rear_Head_Patch", head_loop(0.14, 0.072, H * 0.875), TH, TH + 0.006, gc_accent, 0.002)   # 안까지 연두색으로 채움
    if "Gaming_Chair_Apple_Decal" in bpy.data.materials:
        am = bpy.data.materials["Gaming_Chair_Apple_Decal"]
    else:
        am = bpy.data.materials.new("Gaming_Chair_Apple_Decal"); am.use_nodes = True
        nt = am.node_tree; bs = nt.nodes.get("Principled BSDF")
        bs.inputs["Roughness"].default_value = 0.45
        tx = nt.nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.load(os.path.join(ART_DIR, "apple_emblem.png")); img.pack(); tx.image = img
        nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"]); nt.links.new(tx.outputs["Alpha"], bs.inputs["Alpha"])
        for attr, val in (("surface_render_method", "DITHERED"), ("blend_method", "HASHED")):
            try:
                setattr(am, attr, val)
            except Exception:
                pass
    AS, AZ, AY = 0.21, H * 0.29, TH + 0.008
    me = bpy.data.meshes.new(name + "_Rear_Apple")
    me.from_pydata([(-AS / 2, AY, AZ), (-AS / 2, AY, AZ + AS), (AS / 2, AY, AZ + AS), (AS / 2, AY, AZ)], [], [(0, 3, 2, 1)])
    uvl = me.uv_layers.new()
    uv_of = {0: (1, 0), 1: (1, 1), 2: (0, 1), 3: (0, 0)}   # 뒤에서 봤을 때 그림이 똑바로 보이게
    for lp in me.loops:
        uvl.data[lp.index].uv = uv_of[lp.vertex_index]
    me.materials.append(am)
    ap = bpy.data.objects.new(name + "_Rear_Apple", me); col(coll).objects.link(ap)
    ap.location = (cx, cy + 0.2, SEAT_Z + 0.01); ap.rotation_euler = (math.radians(-12), 0, 0)
    # 팔걸이 (검정 기둥 + 패드)
    for sd in (-1, 1):
        x = cx + sd * 0.3
        box(name + "_Arm_Post_%s" % ("L" if sd > 0 else "R"), x - 0.02, x + 0.02, cy + 0.0, cy + 0.06, 0.4, 0.66, gc_black, coll)
        bx0, bx1 = (cx + 0.14, x + 0.02) if sd > 0 else (x - 0.02, cx - 0.14)
        box(name + "_Arm_Bracket_%s" % ("L" if sd > 0 else "R"), bx0, bx1, cy - 0.02, cy + 0.08, 0.4, 0.43, gc_black, coll)
        pad = box(name + "_Arm_Pad_%s" % ("L" if sd > 0 else "R"), x - 0.04, x + 0.04, cy - 0.13, cy + 0.13, 0.66, 0.69, gc_black, coll)
        pb = pad.modifiers.new("Round", 'BEVEL'); pb.width = 0.012; pb.segments = 3
def mesh_chair(name, cx, cy, coll="Study_Zone"):
    """인체공학 메쉬 의자: 하얀 프레임 + 회색 메쉬 등판/허리/시트 + 헤드레스트 + S자 등뼈 + 3D 팔걸이 (등받이는 +y 쪽)"""
    mw = mat("Mesh_Chair_White_Frame", (0.9, 0.9, 0.89, 1), 0.35)
    mg = mat("Mesh_Chair_Gray_Pad", (0.55, 0.56, 0.58, 1), 0.5)
    mb = mat("Mesh_Chair_Black", (0.06, 0.06, 0.07, 1), 0.4)
    if "Mesh_Chair_Gray_Mesh" in bpy.data.materials:
        mmesh = bpy.data.materials["Mesh_Chair_Gray_Mesh"]
    else:
        mmesh = bpy.data.materials.new("Mesh_Chair_Gray_Mesh"); mmesh.use_nodes = True
        nt = mmesh.node_tree; bs = nt.nodes.get("Principled BSDF")
        bs.inputs["Roughness"].default_value = 0.8
        tc = nt.nodes.new("ShaderNodeTexCoord"); ck = nt.nodes.new("ShaderNodeTexChecker")
        ck.inputs["Scale"].default_value = 260.0
        ck.inputs["Color1"].default_value = (0.5, 0.51, 0.53, 1); ck.inputs["Color2"].default_value = (0.3, 0.31, 0.33, 1)
        nt.links.new(tc.outputs["Object"], ck.inputs["Vector"]); nt.links.new(ck.outputs["Color"], bs.inputs["Base Color"])
        mmesh.diffuse_color = (0.42, 0.43, 0.45, 1)
    SEAT_Z = 0.48

    def tube(oname, pts, bevel, m, parent=None, closed=False):
        cu = bpy.data.curves.new(oname, 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = bevel; cu.bevel_resolution = 4; cu.use_fill_caps = True
        sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1)
        for p, co in zip(sp.points, pts):
            p.co = (co[0], co[1], co[2], 1)
        sp.use_cyclic_u = closed; sp.use_endpoint_u = not closed; sp.order_u = 3
        o = bpy.data.objects.new(oname, cu); cu.materials.append(m)
        col(coll).objects.link(o)
        if parent is not None:
            o.parent = parent
        return o

    def panel(oname, pts, y0, y1, m, parent, bev=0.01):
        bmp = bmesh.new()
        f = bmp.faces.new([bmp.verts.new((x, y0, z)) for x, z in pts])
        ext = bmesh.ops.extrude_face_region(bmp, geom=[f])
        bmesh.ops.translate(bmp, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, y1 - y0, 0))
        bmesh.ops.recalc_face_normals(bmp, faces=bmp.faces[:])
        o = finish(oname, bmp, m, coll)
        o.parent = parent
        bv = o.modifiers.new("Round", 'BEVEL'); bv.width = bev; bv.segments = 3; bv.limit_method = 'ANGLE'
        return o

    def outline(prof, z0, z1):
        right = [(hw, z0 + (z1 - z0) * t) for t, hw in prof]
        return right + [(-x, z) for x, z in reversed(right)]

    # 다리: 하얀 5발 + 검정 바퀴 + 검정 가스 실린더 + 메커니즘
    bm = bmesh.new()
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        mtx = Matrix.Translation((cx + 0.16 * math.cos(a), cy + 0.16 * math.sin(a), 0.085)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(math.radians(-7), 4, 'Y') @ Matrix.Diagonal((0.33, 0.055, 0.04, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)
    b = finish(name + "_Base", bm, mw, coll); b.modifiers.new("Round", 'BEVEL').width = 0.012
    bw = bmesh.new()
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        for sd in (-1, 1):
            bmesh.ops.create_uvsphere(bw, u_segments=14, v_segments=8, radius=0.03,
                                      matrix=Matrix.Translation((cx + 0.31 * math.cos(a) - sd * 0.012 * math.sin(a), cy + 0.31 * math.sin(a) + sd * 0.012 * math.cos(a), 0.03)))
    finish(name + "_Casters", bw, mb, coll, smooth=True)
    cyl(name + "_Gas_Lift", 0.025, 0.1, 0.42, cx, cy, mb, coll, 24)
    mech = box(name + "_Mechanism", cx - 0.12, cx + 0.12, cy - 0.14, cy + 0.12, 0.38, 0.43, mb, coll)
    mech.modifiers.new("Round", 'BEVEL').width = 0.01
    lever = box(name + "_Height_Lever", cx + 0.12, cx + 0.22, cy - 0.06, cy - 0.03, 0.4, 0.41, mw, coll)
    # 시트: 하얀 프레임 위 회색 메쉬
    sf = box(name + "_Seat_Frame", cx - 0.26, cx + 0.26, cy - 0.25, cy + 0.23, 0.43, 0.46, mw, coll)
    sfv = sf.modifiers.new("Round", 'BEVEL'); sfv.width = 0.03; sfv.segments = 4
    sm = box(name + "_Seat_Mesh", cx - 0.24, cx + 0.24, cy - 0.235, cy + 0.215, 0.455, SEAT_Z + 0.015, mmesh, coll)
    smv = sm.modifiers.new("Round", 'BEVEL'); smv.width = 0.025; smv.segments = 4
    # 등받이 (뒤로 12도 기울어진 축에 붙임)
    hinge = bpy.data.objects.new(name + "_Back_Pivot", None)
    hinge.location = (cx, cy + 0.2, SEAT_Z + 0.02); hinge.rotation_euler = (math.radians(-12), 0, 0)
    col(coll).objects.link(hinge)
    lum_prof = [(0.0, 0.2), (0.5, 0.23), (1.0, 0.21)]
    up_prof = [(0.0, 0.21), (0.25, 0.245), (0.6, 0.24), (0.85, 0.2), (1.0, 0.13)]
    head_prof = [(0.0, 0.14), (0.5, 0.16), (1.0, 0.14)]
    lum = outline(lum_prof, 0.03, 0.2)
    up = outline(up_prof, 0.23, 0.66)
    hd = outline(head_prof, 0.75, 0.88)
    panel(name + "_Lumbar_Mesh", lum, -0.03, -0.012, mmesh, hinge)
    panel(name + "_Back_Mesh", up, 0.0, 0.016, mmesh, hinge)
    panel(name + "_Headrest_Mesh", hd, 0.01, 0.026, mmesh, hinge)
    # 등판 테두리: 조금 더 큰 하얀 판을 메쉬 바로 뒤에 붙여서 얇은 흰 테두리처럼 보이게
    def ring(oname, outer, inner, y0, y1, m, bev=0.004):
        bmr = bmesh.new()
        vo = [bmr.verts.new((x, y0, z)) for x, z in outer]
        vi = [bmr.verts.new((x, y0, z)) for x, z in inner]
        n = len(vo)
        fs = [bmr.faces.new([vo[i], vo[(i + 1) % n], vi[(i + 1) % n], vi[i]]) for i in range(n)]
        ext = bmesh.ops.extrude_face_region(bmr, geom=fs)
        bmesh.ops.translate(bmr, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, y1 - y0, 0))
        bmesh.ops.recalc_face_normals(bmr, faces=bmr.faces[:])
        o = finish(oname, bmr, m, coll); o.parent = hinge
        bv = o.modifiers.new("Round", 'BEVEL'); bv.width = bev; bv.segments = 2; bv.limit_method = 'ANGLE'
        return o
    def offset(pts, dist):
        """닫힌 윤곽선을 일정한 두께로 바깥(+)/안(-)으로 넓힘 (모서리도 같은 두께)"""
        n = len(pts); res = []
        for i in range(n):
            p0, p1, p2 = Vector((*pts[i - 1], 0)), Vector((*pts[i], 0)), Vector((*pts[(i + 1) % n], 0))
            e1, e2 = (p1 - p0).normalized(), (p2 - p1).normalized()
            n1, n2 = Vector((e1.y, -e1.x, 0)), Vector((e2.y, -e2.x, 0))
            mt = (n1 + n2).normalized()
            k = dist / max(mt.dot(n1), 0.3)
            res.append((p1.x + mt.x * k, p1.y + mt.y * k))
        return res
    # 등판 테두리: 같은 두께로 메쉬 가장자리를 앞뒤로 감쌈 (아래쪽은 하얀 연결판과 이어짐)
    ring(name + "_Back_Rim_White", offset(up, 0.012), offset(up, -0.007), -0.005, 0.022, mw, bev=0.003)
    # 허리 받침과 등판 사이 빈 곳을 하얀 판으로 채움
    panel(name + "_Back_Gap_Fill", outline([(0.0, 0.205), (1.0, 0.219)], 0.16, 0.236), -0.005, 0.022, mw, hinge, bev=0.003)
    # 뒤쪽 곧은 지지대 + 헤드레스트 기둥 (등받이 축에 붙음)
    def hbox(oname, x0, x1, y0, y1, z0, z1, m):
        bmx = bmesh.new()
        bmesh.ops.create_cube(bmx, size=1.0, matrix=Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1)))
        o = finish(oname, bmx, m, coll); o.parent = hinge
        o.modifiers.new("Round", 'BEVEL').width = 0.006
        return o
    # 뒤쪽 지지대: 의자 몸통에서 올라와 등판 테두리 아랫부분을 넓게 받쳐 줌 (Y자 모양, 등판 가운데는 비움)
    panel(name + "_Back_Support", [(0.036, -0.1), (0.03, 0.12), (0.1, 0.235), (-0.1, 0.235), (-0.03, 0.12), (-0.036, -0.1)], 0.008, 0.032, mw, hinge, bev=0.008)
    # 헤드레스트 기둥: 등판 테두리 윗부분에서 바로 올라감 (하얀색)
    for sd in (-1, 1):
        hbox(name + "_Head_Post_%d" % (sd + 1), sd * 0.06 - 0.009, sd * 0.06 + 0.009, 0.022, 0.036, 0.6, 0.79, mw)
    conn = box(name + "_Back_Connector", cx - 0.035, cx + 0.035, cy + 0.08, cy + 0.22, 0.37, 0.42, mw, coll)   # 의자 몸통과 지지대 연결
    conn.modifiers.new("Round", 'BEVEL').width = 0.008
    # 3D 팔걸이
    for sd in (-1, 1):
        x = cx + sd * 0.29
        tube(name + "_Arm_Post_%d" % (sd + 1), [(cx + sd * 0.14, cy + 0.03, 0.42), (x, cy + 0.03, 0.44), (x, cy + 0.02, 0.56), (x, cy + 0.0, 0.66)], 0.02, mw)
        pad = box(name + "_Arm_Pad_%d" % (sd + 1), x - 0.04, x + 0.04, cy - 0.14, cy + 0.11, 0.66, 0.685, mg, coll)
        pv = pad.modifiers.new("Round", 'BEVEL'); pv.width = 0.012; pv.segments = 3
mesh_chair("Chair_1_Mesh", 2.4, 0.72)   # 스탠드 책상: 인체공학 메쉬 의자
gaming_chair("Chair_2_Gaming", 3.8, 0.7)   # 컴퓨터 책상: 게이밍 의자

# =============== 조명 & 카메라 & 렌더 ===============
sd = bpy.data.lights.new("Sun_Window", 'SUN'); sd.energy = 3.0; sd.angle = math.radians(8); sd.color = (1.0, 0.93, 0.82)
so = bpy.data.objects.new("Sun_Window", sd); so.rotation_euler = (math.radians(60), 0, math.radians(75)); col("Lights_Cameras").objects.link(so)
ad = bpy.data.lights.new("Window_Fill", 'AREA'); ad.energy = 150; ad.size = 1.2; ad.color = (0.95, 0.97, 1.0)
ao = bpy.data.objects.new("Window_Fill", ad); ao.location = (W - 0.15, (WIN_Y0 + WIN_Y1) / 2, 1.5)
ao.rotation_euler = (0, math.radians(90), 0); col("Lights_Cameras").objects.link(ao)
cd = bpy.data.lights.new("Ceiling_Soft", 'AREA'); cd.energy = 110; cd.size = 2.5; cd.color = (1.0, 0.92, 0.8)
co = bpy.data.objects.new("Ceiling_Soft", cd); co.location = (W / 2, D / 2, H - 0.02); col("Lights_Cameras").objects.link(co)
for nm, loc, e in (("Lamp_Vanity", ((VX0 + VX1) / 2, D - 0.15, 1.1), 15),):
    pd = bpy.data.lights.new(nm, 'POINT'); pd.energy = e; pd.color = (1, 0.85, 0.65); pd.shadow_soft_size = 0.05
    po = bpy.data.objects.new(nm, pd); po.location = loc; col("Lights_Cameras").objects.link(po)

def camera(name, loc, target, lens=24, ortho=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.05
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    c = bpy.data.objects.new(name, cd); c.location = loc
    col("Lights_Cameras").objects.link(c)
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return c
cam_over = camera("Camera_Overview", (0.35, 0.25, 5.2), (2.5, 3.1, 0.0), lens=14)
camera("Camera_Entrance_View", (0.6, 0.3, 1.55), (1.2, 5.0, 1.0), lens=16)
camera("Camera_Top_Plan", (W / 2, D / 2, 8), (W / 2, D / 2 + 0.0001, 0), ortho=5.6)
camera("Camera_Bed_Side", (2.3, 1.5, 1.5), (4.0, 4.0, 0.6), lens=16)
scene.camera = cam_over
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
world = bpy.data.worlds.new("World"); scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.85, 0.82, 0.78, 1); bg.inputs[1].default_value = 0.3
world.color = (0.85, 0.82, 0.78)
try:
    scene.render.engine = 'BLENDER_EEVEE'
except Exception:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -0.4
    scene.eevee.taa_render_samples = 64
except Exception:
    pass

folder = os.path.expanduser('~/Documents/Claude_Room')
os.makedirs(folder, exist_ok=True)
path = os.path.join(folder, "my_room.blend")
bpy.ops.wm.save_as_mainfile(filepath=path)
print("ROOM:" + json.dumps({"path": path, "objects": len(bpy.data.objects), "engine": scene.render.engine,
                            "collections": {k: len(v.objects) for k, v in _cols.items()}}))
