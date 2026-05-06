from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# --- Palette ---
BG = RGBColor(0x0F, 0x11, 0x1A)
CARD_BG = RGBColor(0x1A, 0x1D, 0x2E)
ORCHESTRATOR_BG = RGBColor(0x2A, 0x1A, 0x3D)
ORCHESTRATOR_BORDER = RGBColor(0x9B, 0x59, 0xB6)
TOPIC_BG = RGBColor(0x0D, 0x2B, 0x45)
TOPIC_BORDER = RGBColor(0x4E, 0x9A, 0xF5)
TOPIC_ACCENT = RGBColor(0x4E, 0x9A, 0xF5)
FLOW_BG = RGBColor(0x0D, 0x3B, 0x2A)
FLOW_BORDER = RGBColor(0x2E, 0xCC, 0x71)
FLOW_ACCENT = RGBColor(0x2E, 0xCC, 0x71)
PT_BG = RGBColor(0x3D, 0x2A, 0x0D)
PT_BORDER = RGBColor(0xF5, 0xA6, 0x23)
PT_ACCENT = RGBColor(0xF5, 0xA6, 0x23)
ROUTER_BG = RGBColor(0x2D, 0x1A, 0x1A)
ROUTER_BORDER = RGBColor(0xE8, 0x5D, 0x75)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xCC, 0xCC, 0xDD)
DIM = RGBColor(0x77, 0x77, 0x99)
ARROW_COLOR = RGBColor(0x55, 0x55, 0x77)
STAGE_LABEL = RGBColor(0xAA, 0xAA, 0xCC)


def set_slide_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_box(slide, left, top, width, height, fill_color, border_color, border_width=Pt(1.5), radius=Inches(0.08)):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = border_color
    shape.line.width = border_width
    # Set corner radius via XML
    sp = shape._element
    prstGeom = sp.find(qn('a:prstGeom'), sp.nsmap) if hasattr(sp, 'nsmap') else None
    if prstGeom is None:
        for child in sp.iter():
            if child.tag.endswith('prstGeom'):
                prstGeom = child
                break
    if prstGeom is not None:
        avLst = prstGeom.find(qn('a:avLst'), prstGeom.nsmap) if hasattr(prstGeom, 'nsmap') else None
        if avLst is None:
            for child in prstGeom:
                if child.tag.endswith('avLst'):
                    avLst = child
                    break
    return shape


def add_label(slide, left, top, width, height, text, size=10, bold=False, color=WHITE, align=PP_ALIGN.CENTER, font="Calibri"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(4)
    tf.margin_right = Pt(4)
    tf.margin_top = Pt(2)
    tf.margin_bottom = Pt(2)
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font
    p.alignment = align
    return tb


def add_type_badge(slide, left, top, text, bg_color, text_color=WHITE, width=Inches(0.7), height=Inches(0.22), font_size=7):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.fill.background()
    tf = shape.text_frame
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = True
    p.font.color.rgb = text_color
    p.font.name = "Calibri"
    p.alignment = PP_ALIGN.CENTER
    return shape


def add_arrow_down(slide, cx, top, length, color=ARROW_COLOR, width=Pt(2)):
    """Vertical connector arrow."""
    connector = slide.shapes.add_connector(1, cx, top, cx, top + length)  # type 1 = straight
    connector.line.color.rgb = color
    connector.line.width = width
    # Add arrowhead
    line = connector.line
    line.fill.solid()
    line.color.rgb = color
    # Tail arrowhead via XML
    ln = connector._element.find('.//' + qn('a:ln'))
    if ln is not None:
        tail = ln.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'})
        ln.append(tail)
    return connector


def add_arrow_right(slide, left, cy, length, color=ARROW_COLOR, width=Pt(2)):
    """Horizontal connector arrow (no arrowhead, just a line)."""
    connector = slide.shapes.add_connector(1, left, cy, left + length, cy)
    connector.line.color.rgb = color
    connector.line.width = width
    return connector


# ============================================================
# BUILD THE SLIDE
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, BG)

# ---- Title ----
add_label(slide, Inches(0.6), Inches(0.25), Inches(8), Inches(0.5),
          "LNA Nova — Target Architecture", size=26, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
add_label(slide, Inches(0.6), Inches(0.7), Inches(10), Inches(0.35),
          "Topic → Flow → Prompt Template pattern for all four cadence stages", size=13, color=DIM, align=PP_ALIGN.LEFT)

# ============================================================
# ROW 0: ORCHESTRATOR (top center)
# ============================================================
orch_w = Inches(4.0)
orch_h = Inches(0.65)
orch_x = Inches(4.65)
orch_y = Inches(1.15)
add_box(slide, orch_x, orch_y, orch_w, orch_h, ORCHESTRATOR_BG, ORCHESTRATOR_BORDER)
add_type_badge(slide, orch_x + Inches(0.12), orch_y + Inches(0.06), "ORCHESTRATOR", ORCHESTRATOR_BORDER, width=Inches(1.0), font_size=7)
add_label(slide, orch_x, orch_y + Inches(0.25), orch_w, Inches(0.38),
          "Sales Cadence Orchestrator", size=12, bold=True, color=WHITE)

# ============================================================
# STAGE LABELS + arrows from orchestrator
# ============================================================
col_centers = [Inches(2.2), Inches(5.35), Inches(8.5), Inches(11.3)]
stage_labels = ["Stage = Intro", "Stage = Nudge", "Stage = Reply", "Stage = Reply"]
stage_colors = [TOPIC_ACCENT, TOPIC_ACCENT, ROUTER_BORDER, ROUTER_BORDER]

# Vertical arrows from orchestrator
orch_bot = orch_y + orch_h
for i, cx in enumerate(col_centers):
    # Horizontal line from orchestrator center to column
    if i < 2:
        add_arrow_down(slide, cx + Inches(0.8), orch_bot, Inches(0.4), color=ARROW_COLOR)
    elif i == 2:
        add_arrow_down(slide, cx + Inches(0.45), orch_bot, Inches(0.4), color=ARROW_COLOR)
    else:
        pass  # reply splits later

# Stage labels
stage_y = orch_bot + Inches(0.08)
for i in range(3):
    cx = col_centers[i]
    offset = Inches(0.8) if i < 2 else Inches(0.45)
    add_label(slide, cx + offset - Inches(0.55), stage_y, Inches(1.1), Inches(0.25),
              stage_labels[i], size=9, bold=True, color=stage_colors[i], font="Consolas")

# ============================================================
# ROW 1: TOPICS
# ============================================================
topic_y = Inches(2.2)
topic_h = Inches(0.9)
topic_w = Inches(2.4)

# Column definitions: (x, name, subtitle, is_router)
topics = [
    (Inches(1.0), "Initial Outreach", "Topic  ·  2 instructions", False),
    (Inches(4.15), "Follow-up Outreach", "Topic  ·  2 instructions", False),
    (Inches(7.3), "Reply Router", "Planner selects topic", True),
]

for (tx, name, sub, is_router) in topics:
    bg = ROUTER_BG if is_router else TOPIC_BG
    border = ROUTER_BORDER if is_router else TOPIC_BORDER
    badge_text = "ROUTER" if is_router else "TOPIC"
    badge_color = ROUTER_BORDER if is_router else TOPIC_ACCENT

    add_box(slide, tx, topic_y, topic_w, topic_h, bg, border)
    add_type_badge(slide, tx + Inches(0.1), topic_y + Inches(0.08), badge_text, badge_color)
    add_label(slide, tx, topic_y + Inches(0.3), topic_w, Inches(0.3),
              name, size=12, bold=True, color=WHITE)
    add_label(slide, tx, topic_y + Inches(0.58), topic_w, Inches(0.25),
              sub, size=9, color=DIM)

# Reply router splits into Meeting Response and Manage Opt-Out
# Two smaller topic cards under the router
split_y = Inches(3.35)
split_h = Inches(0.85)
split_w = Inches(2.1)

split_topics = [
    (Inches(7.05), "Meeting Response", "Topic  ·  2 instr."),
    (Inches(9.7), "Manage Opt-Out", "Topic  ·  2 instr."),
]

# Arrows from router to split topics
router_bot = topic_y + topic_h
add_arrow_down(slide, Inches(8.0), router_bot, Inches(0.2), color=ROUTER_BORDER)
add_arrow_down(slide, Inches(10.6), router_bot, Inches(0.2), color=ROUTER_BORDER)
# Horizontal bar
add_arrow_right(slide, Inches(8.0), router_bot + Inches(0.2), Inches(2.6), color=ROUTER_BORDER)

for (tx, name, sub) in split_topics:
    add_box(slide, tx, split_y, split_w, split_h, TOPIC_BG, TOPIC_BORDER)
    add_type_badge(slide, tx + Inches(0.08), split_y + Inches(0.06), "TOPIC", TOPIC_ACCENT)
    add_label(slide, tx, split_y + Inches(0.28), split_w, Inches(0.28),
              name, size=11, bold=True, color=WHITE)
    add_label(slide, tx, split_y + Inches(0.55), split_w, Inches(0.22),
              sub, size=9, color=DIM)

# ============================================================
# ARROWS: Topics → Flows
# ============================================================
flow_y = Inches(4.55)

# Arrow from Initial Outreach topic to flow
add_arrow_down(slide, Inches(2.2), topic_y + topic_h, flow_y - (topic_y + topic_h), color=TOPIC_ACCENT)
# Arrow from Follow-up topic to flow
add_arrow_down(slide, Inches(5.35), topic_y + topic_h, flow_y - (topic_y + topic_h), color=TOPIC_ACCENT)
# Arrows from split topics to flows
add_arrow_down(slide, Inches(8.1), split_y + split_h, flow_y - (split_y + split_h), color=TOPIC_ACCENT)
add_arrow_down(slide, Inches(10.75), split_y + split_h, flow_y - (split_y + split_h), color=TOPIC_ACCENT)

# ============================================================
# ROW 2: FLOWS
# ============================================================
flow_h = Inches(0.85)
flow_w = Inches(2.4)

flows = [
    (Inches(1.0), "LNA_Nova_\nInitial_Outreach"),
    (Inches(4.15), "LNA_Nova_\nFollow_Up_Nudge"),
    (Inches(7.0), "LNA_Nova_\nMeeting_Response"),
    (Inches(9.55), "LNA_Nova_\nOpt_Out_Response"),
]

for (fx, name) in flows:
    add_box(slide, fx, flow_y, flow_w, flow_h, FLOW_BG, FLOW_BORDER)
    add_type_badge(slide, fx + Inches(0.1), flow_y + Inches(0.06), "FLOW", FLOW_ACCENT)
    add_label(slide, fx, flow_y + Inches(0.28), flow_w, Inches(0.52),
              name, size=10, bold=True, color=WHITE, font="Consolas")

# ============================================================
# ARROWS: Flows → PTs
# ============================================================
pt_y = Inches(5.75)

# Initial Outreach flow splits into 2 PTs
add_arrow_down(slide, Inches(1.6), flow_y + flow_h, pt_y - (flow_y + flow_h), color=FLOW_ACCENT)
add_arrow_down(slide, Inches(2.8), flow_y + flow_h, pt_y - (flow_y + flow_h), color=FLOW_ACCENT)
# Follow-up flow → 1 PT
add_arrow_down(slide, Inches(5.35), flow_y + flow_h, pt_y - (flow_y + flow_h), color=FLOW_ACCENT)
# Meeting Response flow → 1 PT
add_arrow_down(slide, Inches(8.2), flow_y + flow_h, pt_y - (flow_y + flow_h), color=FLOW_ACCENT)
# Opt-Out flow → 1 PT
add_arrow_down(slide, Inches(10.75), flow_y + flow_h, pt_y - (flow_y + flow_h), color=FLOW_ACCENT)

# ============================================================
# ROW 3: PROMPT TEMPLATES
# ============================================================
pt_h = Inches(0.85)
pt_w_sm = Inches(1.7)
pt_w = Inches(2.1)

pts = [
    (Inches(0.5), pt_w_sm, "Persona\nDetection", "GPT-4o Mini"),
    (Inches(2.3), pt_w_sm, "Outreach\nEmail", "Gemini 2.5 Flash"),
    (Inches(4.3), pt_w, "Follow-Up\nNudge", "Gemini 2.5 Flash"),
    (Inches(7.15), pt_w, "Meeting\nResponse", "Gemini 2.5 Flash"),
    (Inches(9.7), pt_w, "Opt-Out\nResponse", "Gemini 2.5 Flash"),
]

for (px, pw, name, model) in pts:
    add_box(slide, px, pt_y, pw, pt_h, PT_BG, PT_BORDER)
    add_type_badge(slide, px + Inches(0.08), pt_y + Inches(0.06), "PROMPT TEMPLATE", PT_ACCENT, width=Inches(1.15), font_size=6)
    add_label(slide, px, pt_y + Inches(0.28), pw, Inches(0.3),
              name, size=10, bold=True, color=WHITE, font="Consolas")
    add_label(slide, px, pt_y + Inches(0.6), pw, Inches(0.2),
              model, size=8, color=DIM)

# ============================================================
# LEGEND
# ============================================================
legend_y = Inches(6.85)
legend_items = [
    ("TOPIC", TOPIC_ACCENT, "GenAiPlugin — scope & guardrails"),
    ("FLOW", FLOW_ACCENT, "AutoLaunchedFlow — orchestration & updates"),
    ("PROMPT TEMPLATE", PT_ACCENT, "GenAiPromptTemplate — LLM generation"),
    ("ROUTER", ROUTER_BORDER, "Planner selects based on reply content"),
]

add_label(slide, Inches(0.6), legend_y, Inches(0.8), Inches(0.25),
          "Legend:", size=10, bold=True, color=DIM, align=PP_ALIGN.LEFT)

for i, (badge, color, desc) in enumerate(legend_items):
    lx = Inches(1.5 + i * 3.0)
    add_type_badge(slide, lx, legend_y + Inches(0.02), badge, color, width=Inches(1.2) if badge == "PROMPT TEMPLATE" else Inches(0.8), font_size=7)
    bw = Inches(1.3) if badge == "PROMPT TEMPLATE" else Inches(0.9)
    add_label(slide, lx + bw, legend_y, Inches(1.8), Inches(0.25),
              desc, size=8, color=DIM, align=PP_ALIGN.LEFT)

# ============================================================
# SAVE
# ============================================================
output_path = "/Users/tabdeen/Documents/Projects/FDE/Statista-SDRAgentDev/prompt/reEngineering/LNA_Nova_Architecture_Diagram.pptx"
prs.save(output_path)
print(f"Saved: {output_path}")
