import bpy, bmesh, os, math, random, json
from mathutils import Matrix, Vector

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

box("Bed_Mattress", BX0 + 0.03, BX1 - 0.08, BY0 + 0.03, BY1 - 0.03, 0.3, 0.52, sheet_sage, "Bed")
# 사계절 이불: 두툼하게 부풀고 구겨진 체크 이불 (침대 옆으로 살짝 흘러내림)
puffy("Bed_Duvet_Plaid", BX0 - 0.05, BX1 - 0.47, BY0 - 0.07, BY1 + 0.03, 0.36, 0.6, plaid, 0.08, 0.012, 0.3, billow=0.08, cuts=20, lift=(BX1 - 0.76, 0.14, 0.06))
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
book_specs = {i: [] for i in range(len(BOOK_COLS))}
for s in range(4):
    y = SY0 + 0.04
    zb = shelf_z[s] + 0.025
    while y < SY1 - 0.08:
        if random.random() < 0.15:
            y += 0.07; continue
        t = random.uniform(0.02, 0.045); hgt = random.uniform(0.2, 0.36); dep = random.uniform(0.18, 0.24)
        xc = (SX0 + SX1) / 2
        book_specs[random.randrange(len(BOOK_COLS))].append((xc - dep / 2, xc + dep / 2, y, y + t, zb, zb + hgt))
        y += t + 0.003
for i, sp in book_specs.items():
    if sp:
        boxes("Books_%d" % i, sp, BOOK_COLS[i], "Bookshelf")
cyl("Shelf_Vase", 0.05, SH, SH + 0.18, (SX0 + SX1) / 2, 0.3, M["pot"], "Bookshelf", 16, r2=0.03)
sphere("Shelf_Plant", 0.09, ((SX0 + SX1) / 2, 0.7, SH + 0.1), M["plant"], "Bookshelf")

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
armchair("Chair_1", 2.4, 0.95)
armchair("Chair_2", 3.8, 0.95)

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
