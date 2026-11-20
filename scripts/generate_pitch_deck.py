#!/usr/bin/env python3
"""
scripts/generate_pitch_deck.py
Builds the official 10-slide executive pitch deck for SuryaGrid (SunNode)
for the Government of Telangana (Department of Energy) Challenge 10 Submission.

Outputs:
1. outputs/SuryaGrid_Telangana_Energy_Innovation_Pitch_Deck.pptx
2. outputs/SuryaGrid_Telangana_Energy_Innovation_Pitch_Deck.pdf
3. reports/pitch_deck_slides/slide_01.png ... slide_10.png (Visual QA Inspection)
"""

import os
import sys
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
SLIDES_PNG_DIR = os.path.join(BASE_DIR, "reports", "pitch_deck_slides")
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "pitch_deck")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(SLIDES_PNG_DIR, exist_ok=True)

# 16:9 Dimensions
WIDTH_IN = 13.333
HEIGHT_IN = 7.5
WIDTH_PT = 1920
HEIGHT_PT = 1080

# Institutional Color Palette
C_DARK_BG    = RGBColor(11, 18, 32)     # #0B1220 Deep Navy Slate
C_DARK_CARD  = RGBColor(19, 30, 50)     # #131E32 Dark Card
C_LIGHT_BG   = RGBColor(248, 250, 252) # #F8FAFC Clean Off-White
C_WHITE      = RGBColor(255, 255, 255) # #FFFFFF
C_AMBER      = RGBColor(245, 158, 11)   # #F59E0B Solar Amber
C_EMERALD    = RGBColor(16, 185, 129)   # #10B981 Emerald
C_CYAN       = RGBColor(14, 165, 233)   # #0EA5E9 Sky Cyan
C_ROSE       = RGBColor(239, 68, 68)    # #EF4444 Alert Rose
C_TEXT_MAIN  = RGBColor(15, 23, 42)     # #0F172A Slate 900
C_TEXT_BODY  = RGBColor(51, 65, 85)     # #334155 Slate 700
C_TEXT_MUTED = RGBColor(100, 116, 139)  # #64748B Slate 500
C_BORDER     = RGBColor(226, 232, 240)  # #E2E8F0 Slate 200
C_BORDER_DRK = RGBColor(51, 65, 85)     # #334155 Dark Border

# Tuple variants for fitz (0-1 float)
F_DARK_BG    = (11/255, 18/255, 32/255)
F_DARK_CARD  = (19/255, 30/255, 50/255)
F_LIGHT_BG   = (248/255, 250/255, 252/255)
F_WHITE      = (1.0, 1.0, 1.0)
F_AMBER      = (245/255, 158/255, 11/255)
F_EMERALD    = (16/255, 185/255, 129/255)
F_CYAN       = (14/255, 165/255, 233/255)
F_ROSE       = (239/255, 68/255, 68/255)
F_TEXT_MAIN  = (15/255, 23/255, 42/255)
F_TEXT_BODY  = (51/255, 65/255, 85/255)
F_TEXT_MUTED = (100/255, 116/255, 139/255)
F_BORDER     = (226/255, 232/255, 240/255)
F_BORDER_DRK = (51/255, 65/255, 85/255)

print("Starting SuryaGrid (SunNode) Stage 6 Pitch Deck Engine...")

# ==============================================================================
# PART 1: NATIVE PPTX GENERATOR (python-pptx)
# ==============================================================================

def build_pptx_deck(pptx_path):
    prs = Presentation()
    prs.slide_width = Inches(WIDTH_IN)
    prs.slide_height = Inches(HEIGHT_IN)
    blank_layout = prs.slide_layouts[6]

    def set_slide_bg(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(WIDTH_IN), Inches(HEIGHT_IN))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, title, category="GOVERNMENT OF TELANGANA · ENERGY DEPARTMENT", dark=False):
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.9))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p0 = tf.paragraphs[0]
        p0.text = category.upper()
        p0.font.size = Pt(9.5)
        p0.font.bold = True
        p0.font.color.rgb = C_AMBER if dark else C_TEXT_MUTED
        
        p1 = tf.add_paragraph()
        p1.text = title
        p1.font.size = Pt(22)
        p1.font.bold = True
        p1.font.color.rgb = C_WHITE if dark else C_TEXT_MAIN
        p1.space_before = Pt(3)

    # --------------------------------------------------------------------------
    # SLIDE 1: Cover (Dark Bookend)
    # --------------------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_DARK_BG)

    # Logo
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(logo_path):
        s1.shapes.add_picture(logo_path, Inches(0.8), Inches(0.9), Inches(1.3), Inches(1.3))

    # Top Tag
    tb = s1.shapes.add_textbox(Inches(2.3), Inches(1.0), Inches(10), Inches(0.4))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "GOVERNMENT OF TELANGANA  •  DEPARTMENT OF ENERGY  •  CHALLENGE 10"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_AMBER

    # Title & Subtitle
    tb = s1.shapes.add_textbox(Inches(0.8), Inches(2.3), Inches(11.7), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "SuryaGrid (SunNode)"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = C_WHITE
    
    p2 = tf.add_paragraph()
    p2.text = "AI-Driven Solar Siting & Grid-Integration Decision Support System (DSS)"
    p2.font.size = Pt(24)
    p2.font.bold = True
    p2.font.color.rgb = C_AMBER
    p2.space_before = Pt(8)

    p3 = tf.add_paragraph()
    p3.text = "Statewide Substation Land, Transformer Headroom & PVGIS Solar Generation Intelligence for PM-KUSUM & Utility-Scale STU Deployment"
    p3.font.size = Pt(13)
    p3.font.color.rgb = RGBColor(203, 213, 225)
    p3.space_before = Pt(8)

    # Live URL Button
    btn = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.7), Inches(4.2), Inches(0.6))
    btn.fill.solid()
    btn.fill.fore_color.rgb = C_EMERALD
    btn.line.fill.background()
    btn.text_frame.text = "🌐  LIVE PRODUCTION APP:  https://sunnode.vercel.app"
    btn.text_frame.paragraphs[0].font.size = Pt(11.5)
    btn.text_frame.paragraphs[0].font.bold = True
    btn.text_frame.paragraphs[0].font.color.rgb = C_DARK_BG

    # 3 Proof Pills Across Bottom
    proof_items = [
        ("391 Substations · 33 Districts", "100% Statewide Geographic Coverage"),
        ("12,602.6 MW True Deployable", "Bottleneck-Matched (Min Land, Grid)"),
        ("Live Deployed Prototype", "Zero-Latency Vercel Edge Architecture")
    ]
    for idx, (title, sub) in enumerate(proof_items):
        bx = Inches(0.8 + idx * 3.95)
        pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(5.6), Inches(3.8), Inches(1.1))
        pill.fill.solid()
        pill.fill.fore_color.rgb = C_DARK_CARD
        pill.line.color.rgb = C_BORDER_DRK
        
        ptf = pill.text_frame
        ptf.margin_top = Inches(0.15)
        ptf.margin_left = Inches(0.2)
        p = ptf.paragraphs[0]
        p.text = title
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = C_WHITE
        
        p_sub = ptf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(10)
        p_sub.font.color.rgb = C_TEXT_MUTED
        p_sub.space_before = Pt(4)

    # --------------------------------------------------------------------------
    # SLIDE 2: The Ground Reality & Siting Crisis
    # --------------------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, C_LIGHT_BG)
    add_header(s2, "The Siting Crisis: Why Solar Rollout Stalls in Telangana")

    # Top Comparison Banner
    banner = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.733), Inches(1.2))
    banner.fill.solid()
    banner.fill.fore_color.rgb = C_TEXT_MAIN
    banner.line.fill.background()
    
    btf = banner.text_frame
    btf.margin_left = Inches(0.3)
    btf.margin_top = Inches(0.18)
    bp0 = btf.paragraphs[0]
    bp0.text = "THE CENTRAL GRID BOTTLENECK DISCOVERED ACROSS 391 TELANGANA SUBSTATIONS"
    bp0.font.size = Pt(10)
    bp0.font.bold = True
    bp0.font.color.rgb = C_AMBER
    
    bp1 = btf.add_paragraph()
    bp1.text = "29,366.4 MW Farmland Identified  ➔  Only 12,602.6 MW Truly Deployable"
    bp1.font.size = Pt(19)
    bp1.font.bold = True
    bp1.font.color.rgb = C_WHITE
    bp1.space_before = Pt(4)
    
    bp2 = btf.add_paragraph()
    bp2.text = "65.2% (255 of 391) of substations are strictly Grid Transformer Constrained. Siting solar without transformer headroom guarantees interconnection failure."
    bp2.font.size = Pt(10.5)
    bp2.font.color.rgb = RGBColor(226, 232, 240)
    bp2.space_before = Pt(3)

    # 3 Bottleneck Cards
    bottlenecks = [
        ("1. Manual Survey Paralysis", C_ROSE, [
            "Traditional manual walk-throughs take 3–6 months per site.",
            "Field scouts frequently miss seasonal water bodies, local slope > 5°, and strict 30 m FTL lake buffer compliance.",
            "High administrative friction delays DISCOM bidding schedules."
        ]),
        ("2. The Land-Grid Disconnect", C_CYAN, [
            "Developers lease massive farmland parcels only to discover the substation transformer MVA has zero spare headroom.",
            "Co-located 132 kV and 220 kV yards share overlapping 1 km radii, causing severe capacity double-counting.",
            "Utilities risk millions in stranded transmission capital."
        ]),
        ("3. Unverified Irradiance Risk", C_AMBER, [
            "Projects rely on generic state-level solar averages rather than location-specific satellite telemetry.",
            "A 5% irradiation deficit can trigger debt service (DSCR) default under tight ₹2.75–₹3.13/kWh regulated tariffs.",
            "Banks demand audited, month-by-month generation telemetry."
        ])
    ]

    for idx, (title, accent_color, bullets) in enumerate(bottlenecks):
        bx = Inches(0.8 + idx * 3.95)
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(2.8), Inches(3.8), Inches(4.1))
        card.fill.solid()
        card.fill.fore_color.rgb = C_WHITE
        card.line.color.rgb = C_BORDER
        
        # Color bar on top of card
        cbar = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, bx, Inches(2.8), Inches(3.8), Inches(0.08))
        cbar.fill.solid()
        cbar.fill.fore_color.rgb = accent_color
        cbar.line.fill.background()
        
        ctf = card.text_frame
        ctf.margin_left = ctf.margin_right = Inches(0.25)
        ctf.margin_top = Inches(0.25)
        
        p = ctf.paragraphs[0]
        p.text = title
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        
        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = "•  " + b
            bp.font.size = Pt(11)
            bp.font.color.rgb = C_TEXT_BODY
            bp.space_before = Pt(10)

    # --------------------------------------------------------------------------
    # SLIDE 3: The 4-Layer Solution Engine
    # --------------------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, C_LIGHT_BG)
    add_header(s3, "The SunNode Solution: 4-Layer AI, GIS & Grid Engine")

    layers = [
        ("Layer 1: AI Land Suitability", C_EMERALD, "Google Earth Engine 10 m", [
            "10 m Sentinel Dynamic World V1 (12-mo mode composite) + USGS SRTM 30 m terrain slope.",
            "1 km Feeder Radius (~776 acres): Focuses strictly on lowest transmission loss zone.",
            "3-Tier Zoning: Green (Farmland/Bare ≤ 5°), Yellow (Canopy/Orchards), Red (Built-up, Water + 30 m FTL).",
            "Contiguous Core ≥ 4 acres: Filters isolated speckles to ensure buildable solar patches.",
            "Deduplication: Spatial union eliminates -617.5 MW co-located overlap across 27 clusters."
        ]),
        ("Layer 2: Grid Load & Headroom", C_CYAN, "DISCOM & TGTRANSCO Physics", [
            "TGRAC Layer 8 PTR MVA + 1-to-1 DISCOM Annexure-D verified spare evacuation capacities.",
            "Strict Bottleneck Rule: Deployable MW = Min(Land MW, Grid Headroom MW).",
            "Full AC Injection Current calculations: I = P / (√3 × V × 0.95).",
            "Dedicated Feeder Bay Sizing: 275 × 33 kV VCB, 85 × 132 kV SF6, 31 × 220 kV SF6.",
            "Safeguards grid stability by preventing reverse-power transformer overloading."
        ]),
        ("Layer 3: Real Solar Telemetry", C_AMBER, "100% EU JRC PVGIS v5.3 API", [
            "Zero synthetic or estimated data: Direct location-specific queries for all 391 substations.",
            "Daily & Annual Irradiance: Mean 5.51 kWh/m²/day (Range: 5.29 to 5.61 kWh/m²/day).",
            "Specific Yield: Mean 1,491.2 kWh/kWp/yr (1.49 MU/MW/yr clean electricity generation).",
            "Capacity Utilization Factor (CUF): Mean 17.02% (Range: 16.27% to 17.30%).",
            "Full 12-month Jan–Dec seasonal generation curves for exact bankable revenue modeling."
        ]),
        ("Layer 4: Bankable ROI Scoring", C_TEXT_MAIN, "Levelized Financial Modeling", [
            "Dual-Tier Tariffs: PM-KUSUM Feeder at ₹3.13/kWh; Utility-Scale STU at ₹2.75/kWh.",
            "Turnkey EPC Benchmark: ₹3.75 Cr/MW turnkey CAPEX.",
            "Financial Metrics: Annual revenue, net EBITDA, simple payback (10.13 yrs statewide average).",
            "Composite Score (0–100): Weighted by deployable capacity (150 MW cap), payback speed, CUF.",
            "Farmer Prosperity: ₹252.05 Cr/yr direct rural land lease income (₹2.0 Lakh/MW/yr)."
        ])
    ]

    for idx, (title, color, tag, bullets) in enumerate(layers):
        col = idx % 2
        row = idx // 2
        bx = Inches(0.8 + col * 5.95)
        by = Inches(1.4 + row * 2.8)
        
        card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, by, Inches(5.78), Inches(2.6))
        card.fill.solid()
        card.fill.fore_color.rgb = C_WHITE
        card.line.color.rgb = C_BORDER
        
        # Accent tab
        tab = s3.shapes.add_shape(MSO_SHAPE.RECTANGLE, bx, by, Inches(0.12), Inches(2.6))
        tab.fill.solid()
        tab.fill.fore_color.rgb = color
        tab.line.fill.background()
        
        ctf = card.text_frame
        ctf.margin_left = Inches(0.3)
        ctf.margin_top = Inches(0.15)
        ctf.margin_right = Inches(0.2)
        
        p = ctf.paragraphs[0]
        p.text = title
        p.font.size = Pt(13.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        
        p_tag = ctf.add_paragraph()
        p_tag.text = tag.upper()
        p_tag.font.size = Pt(9)
        p_tag.font.bold = True
        p_tag.font.color.rgb = color
        p_tag.space_before = Pt(1)
        
        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = "• " + b
            bp.font.size = Pt(9.5)
            bp.font.color.rgb = C_TEXT_BODY
            bp.space_before = Pt(3)

    # --------------------------------------------------------------------------
    # SLIDE 4: Live Product Showcase 1 — Executive Dashboard & KPIs
    # --------------------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, C_LIGHT_BG)
    add_header(s4, "Live Product Showcase 1: Statewide Executive Dashboard & KPIs")

    # Framed Dashboard Screenshot
    img_dash = os.path.join(ASSETS_DIR, "framed_dashboard.jpeg")
    if not os.path.exists(img_dash):
        img_dash = os.path.join(ASSETS_DIR, "framed_dashboard.png")
    if os.path.exists(img_dash):
        s4.shapes.add_picture(img_dash, Inches(0.8), Inches(1.4), Inches(7.4), Inches(5.5))

    # 4 KPI Cards on Right
    kpis = [
        ("12,602.6 MW", "True Deployable Solar", C_EMERALD, "Deduplicated grid-matched solar across 391 substations (after eliminating 617.5 MW co-located overlap)."),
        ("₹47,259.5 Cr", "Turnkey CAPEX Investment", C_CYAN, "Total EPC investment required at Telangana ₹3.75 Cr/MW benchmark for 100% capacity realization."),
        ("₹5,484.1 Cr / yr", "Annual Gross Revenue", C_AMBER, "Combined clean energy generation revenue under regulated ₹2.75 & ₹3.13/kWh feed-in tariffs."),
        ("10.13 Years", "Aggregate Simple Payback", C_TEXT_MAIN, "Statewide average capital recovery period, ensuring commercial bankability and debt service (> 1.20x DSCR).")
    ]

    for idx, (val, label, color, desc) in enumerate(kpis):
        by = Inches(1.4 + idx * 1.38)
        kcard = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.4), by, Inches(4.133), Inches(1.25))
        kcard.fill.solid()
        kcard.fill.fore_color.rgb = C_WHITE
        kcard.line.color.rgb = C_BORDER
        
        ktf = kcard.text_frame
        ktf.margin_left = ktf.margin_right = Inches(0.2)
        ktf.margin_top = Inches(0.12)
        
        p = ktf.paragraphs[0]
        p.text = val
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = color
        
        p_lbl = ktf.add_paragraph()
        p_lbl.text = label.upper()
        p_lbl.font.size = Pt(9.5)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = C_TEXT_MAIN
        
        p_desc = ktf.add_paragraph()
        p_desc.text = desc
        p_desc.font.size = Pt(8.5)
        p_desc.font.color.rgb = C_TEXT_MUTED
        p_desc.space_before = Pt(2)

    # --------------------------------------------------------------------------
    # SLIDE 5: Live Product Showcase 2 — Satellite GIS & Solar Irradiance
    # --------------------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, C_LIGHT_BG)
    add_header(s5, "Live Product Showcase 2: Satellite GIS & Solar Irradiance Explorer")

    # URL Pill on top right
    url_btn = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.2), Inches(0.5), Inches(3.3), Inches(0.4))
    url_btn.fill.solid()
    url_btn.fill.fore_color.rgb = C_TEXT_MAIN
    url_btn.line.fill.background()
    url_btn.text_frame.text = "🌐  https://sunnode.vercel.app"
    url_btn.text_frame.paragraphs[0].font.size = Pt(10)
    url_btn.text_frame.paragraphs[0].font.bold = True
    url_btn.text_frame.paragraphs[0].font.color.rgb = C_AMBER

    # Left: Framed Satellite Map
    img_map = os.path.join(ASSETS_DIR, "framed_map_satellite.jpeg")
    if not os.path.exists(img_map):
        img_map = os.path.join(ASSETS_DIR, "framed_map_satellite.png")
    if os.path.exists(img_map):
        s5.shapes.add_picture(img_map, Inches(0.8), Inches(1.4), Inches(7.2), Inches(4.3))

    # Right: Framed Inspector Card
    img_insp = os.path.join(ASSETS_DIR, "framed_inspector.jpeg")
    if not os.path.exists(img_insp):
        img_insp = os.path.join(ASSETS_DIR, "framed_inspector.png")
    if os.path.exists(img_insp):
        s5.shapes.add_picture(img_insp, Inches(8.2), Inches(1.4), Inches(4.333), Inches(4.3))

    # Bottom 3 Feature Highlights
    feats = [
        ("Dual Verification Map", "Evaluators see both how much sun energy reaches the yard and whether the 1 km terrain + transformer headroom can host it."),
        ("Thermal Irradiance Heatmap", "Color markers by real PVGIS sun energy: Tier-1 (≥ 5.55 kWh/m²/d, #EA580C), Tier-2 (5.45–5.55, #F59E0B), Tier-3 (< 5.45, #EAB308)."),
        ("12-Month PVGIS Curves", "The 4-Layer Inspector plots real Jan–Dec seasonal generation bars (kWh/kWp) alongside bay current & financial metrics.")
    ]
    for idx, (title, desc) in enumerate(feats):
        bx = Inches(0.8 + idx * 3.95)
        fcard = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(5.85), Inches(3.8), Inches(1.15))
        fcard.fill.solid()
        fcard.fill.fore_color.rgb = C_WHITE
        fcard.line.color.rgb = C_BORDER
        
        ftf = fcard.text_frame
        ftf.margin_left = ftf.margin_right = Inches(0.2)
        ftf.margin_top = Inches(0.12)
        p = ftf.paragraphs[0]
        p.text = title
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        
        p_desc = ftf.add_paragraph()
        p_desc.text = desc
        p_desc.font.size = Pt(8.5)
        p_desc.font.color.rgb = C_TEXT_BODY
        p_desc.space_before = Pt(3)

    # --------------------------------------------------------------------------
    # SLIDE 6: Live Product Showcase 3 — Siting Wizard & ROI Simulator
    # --------------------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, C_LIGHT_BG)
    add_header(s6, "Live Product Showcase 3: 30-Second Siting Wizard & Bankable ROI Simulator")

    # Side-by-side screenshots: Wizard & ROI Simulator
    img_wiz = os.path.join(ASSETS_DIR, "framed_wizard.jpeg")
    if not os.path.exists(img_wiz):
        img_wiz = os.path.join(ASSETS_DIR, "framed_wizard.png")
    if os.path.exists(img_wiz):
        s6.shapes.add_picture(img_wiz, Inches(0.8), Inches(1.4), Inches(5.75), Inches(4.3))

    img_roi = os.path.join(ASSETS_DIR, "framed_roi.jpeg")
    if not os.path.exists(img_roi):
        img_roi = os.path.join(ASSETS_DIR, "framed_roi.png")
    if os.path.exists(img_roi):
        s6.shapes.add_picture(img_roi, Inches(6.78), Inches(1.4), Inches(5.75), Inches(4.3))

    # Bottom 3 Workflow Cards
    workflow_items = [
        ("Step 1–2: Criteria Input", "Select Utility EHT vs. PM-KUSUM feeder track, target capacity range, and district constraints in seconds."),
        ("Step 3: Top-3 Automated Matching", "Algorithmic multi-criteria scoring surfaces the top 3 optimal substations with highest spare headroom & lowest land slope."),
        ("Step 4: Bankable DPR Export", "One-click generation of bankable DPR dossiers with 25-yr cash flows, DSCR (> 1.20x), and GEE satellite coordinates.")
    ]
    for idx, (title, desc) in enumerate(workflow_items):
        bx = Inches(0.8 + idx * 3.95)
        wcard = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(5.85), Inches(3.8), Inches(1.15))
        wcard.fill.solid()
        wcard.fill.fore_color.rgb = C_WHITE
        wcard.line.color.rgb = C_BORDER
        
        wtf = wcard.text_frame
        wtf.margin_left = wtf.margin_right = Inches(0.2)
        wtf.margin_top = Inches(0.12)
        p = wtf.paragraphs[0]
        p.text = title
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        
        p_desc = wtf.add_paragraph()
        p_desc.text = desc
        p_desc.font.size = Pt(8.5)
        p_desc.font.color.rgb = C_TEXT_BODY
        p_desc.space_before = Pt(3)

    # --------------------------------------------------------------------------
    # SLIDE 7: Statewide Priority Leaderboards
    # --------------------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, C_LIGHT_BG)
    add_header(s7, "Statewide Priority Leaderboards: Utility EHT vs. PM-KUSUM")

    # Table 1: Top 5 Utility EHT (220/400 kV @ ₹2.75/kWh)
    t1_box = s7.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(5.75), Inches(0.4))
    t1_box.text_frame.text = "⚡ TOP 5 UTILITY-SCALE EHT SUBSTATIONS (220/400 kV @ ₹2.75/kWh STU)"
    t1_box.text_frame.paragraphs[0].font.size = Pt(11)
    t1_box.text_frame.paragraphs[0].font.bold = True
    t1_box.text_frame.paragraphs[0].font.color.rgb = C_TEXT_MAIN

    table1_shape = s7.shapes.add_table(6, 4, Inches(0.8), Inches(1.75), Inches(5.75), Inches(3.8))
    table1 = table1_shape.table
    table1.columns[0].width = Inches(1.9)
    table1.columns[1].width = Inches(1.35)
    table1.columns[2].width = Inches(1.25)
    table1.columns[3].width = Inches(1.25)

    headers1 = ["Substation", "District", "Deployable", "Score / Bay"]
    for i, h in enumerate(headers1):
        cell = table1.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_TEXT_MAIN
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = C_WHITE

    eht_data = [
        ("Kosigi", "Narayanpet", "126.6 MW", "72.1 (3 Bays)"),
        ("Veltoor", "Wanaparthy", "133.2 MW", "71.9 (2 Bays)"),
        ("Kalluru", "Khammam", "135.0 MW", "71.5 (3 Bays)"),
        ("Miryalaguda", "Nalgonda", "134.3 MW", "71.3 (3 Bays)"),
        ("Dichpally 400kV", "Nizamabad", "129.2 MW", "71.3 (2 Bays)")
    ]
    for row_idx, row in enumerate(eht_data):
        for col_idx, val in enumerate(row):
            cell = table1.cell(row_idx + 1, col_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(241, 245, 249) if row_idx % 2 == 1 else C_WHITE
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.bold = (col_idx == 0 or col_idx == 2)
            p.font.color.rgb = C_EMERALD if col_idx == 2 else C_TEXT_MAIN

    # Table 2: Top 5 PM-KUSUM Feeders (132/33 kV @ ₹3.13/kWh)
    t2_box = s7.shapes.add_textbox(Inches(6.78), Inches(1.3), Inches(5.75), Inches(0.4))
    t2_box.text_frame.text = "🌾 TOP 5 PM-KUSUM FEEDER CLUSTERS (132/33 kV @ ₹3.13/kWh REGULATED)"
    t2_box.text_frame.paragraphs[0].font.size = Pt(11)
    t2_box.text_frame.paragraphs[0].font.bold = True
    t2_box.text_frame.paragraphs[0].font.color.rgb = C_TEXT_MAIN

    table2_shape = s7.shapes.add_table(6, 4, Inches(6.78), Inches(1.75), Inches(5.75), Inches(3.8))
    table2 = table2_shape.table
    table2.columns[0].width = Inches(1.9)
    table2.columns[1].width = Inches(1.35)
    table2.columns[2].width = Inches(1.25)
    table2.columns[3].width = Inches(1.25)

    for i, h in enumerate(headers1):
        cell = table2.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_AMBER
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = C_DARK_BG

    kusum_data = [
        ("Sircilla", "Rajanna Sircilla", "81.0 MW", "59.6 (5 Bays)"),
        ("Parigi", "Vikarabad", "67.5 MW", "58.3 (4 Bays)"),
        ("Gajwel", "Siddipet", "72.0 MW", "57.7 (5 Bays)"),
        ("Gangadhara", "Karimnagar", "62.3 MW", "55.0 (4 Bays)"),
        ("Marriguda", "Nalgonda", "59.1 MW", "53.9 (4 Bays)")
    ]
    for row_idx, row in enumerate(kusum_data):
        for col_idx, val in enumerate(row):
            cell = table2.cell(row_idx + 1, col_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(241, 245, 249) if row_idx % 2 == 1 else C_WHITE
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.bold = (col_idx == 0 or col_idx == 2)
            p.font.color.rgb = C_AMBER if col_idx == 2 else C_TEXT_MAIN

    # Bottom summary callout
    bot_callout = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.8), Inches(11.733), Inches(1.15))
    bot_callout.fill.solid()
    bot_callout.fill.fore_color.rgb = C_WHITE
    bot_callout.line.color.rgb = C_BORDER
    ctf = bot_callout.text_frame
    ctf.margin_left = ctf.margin_right = Inches(0.25)
    ctf.margin_top = Inches(0.15)
    p = ctf.paragraphs[0]
    p.text = "STRATEGIC TENDERING RECOMMENDATION FOR TELANGANA ENERGY DEPARTMENT"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN
    
    p2 = ctf.add_paragraph()
    p2.text = "• Phase 1 Tendering (Immediate): Issue 1,500 MW across the Top-10 EHT & PM-KUSUM substations where contiguous flat farmland (≥ 4 ac) and transformer bays are 100% verified."
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = C_TEXT_BODY
    p2.space_before = Pt(3)

    p3 = ctf.add_paragraph()
    p3.text = "• Direct Farmer Benefit: These top 10 sites immediately distribute ₹45.8 Cr/year in direct lease income to rural farming households."
    p3.font.size = Pt(9.5)
    p3.font.color.rgb = C_EMERALD
    p3.font.bold = True
    p3.space_before = Pt(2)

    # --------------------------------------------------------------------------
    # SLIDE 8: Engineering Rigor & Data Audit Proof
    # --------------------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, C_LIGHT_BG)
    add_header(s8, "Engineering Rigor & Data Integrity Audit (Why Evaluators Can Trust This)")

    audits = [
        ("1-to-1 Annexure-D Matching", C_EMERALD, [
            "Resolved co-located substation duplication (e.g. Dichpally 220 kV vs. 400 kV yards).",
            "Enforced strict 1-to-1 voltage-aware matching, ensuring zero double-counted spare capacity.",
            "Deduplicated 27 spatial overlap clusters, removing 617.5 MW phantom capacity."
        ]),
        ("Official 33-District Normalization", C_CYAN, [
            "Rigorous spatial point-in-polygon joins matching official Survey of India boundary.",
            "100% clean revenue district naming (zero legacy fragments like 'Rangareddy' or 'UNKNOWN').",
            "Every single substation mapped with verified 5-decimal GPS coordinates."
        ]),
        ("Strict Grid-Code Bay Sizing", C_AMBER, [
            "Calculated full 3-phase AC injection currents: I = P / (√3 × V × 0.95).",
            "Sized exact switchgear: 275 × 33 kV VCB (630A limit), 85 × 132 kV SF6 (1250A limit), 31 × 220 kV SF6 (1600A limit).",
            "Ensures transformer impedance compliance without busbar fault hazards."
        ]),
        ("100% Automated Test Coverage", C_TEXT_MAIN, [
            "16/16 automated Python unit tests passing in continuous CI test harness.",
            "Zero nulls, zero NaNs across all 391 substation rows in master CSV & JSON datasets.",
            "Fully verified 23-sheet Master Excel, 3D KMZ, and cartographic PDF atlas."
        ])
    ]

    for idx, (title, color, bullets) in enumerate(audits):
        bx = Inches(0.8 + idx * 2.95)
        card = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(1.4), Inches(2.82), Inches(4.2))
        card.fill.solid()
        card.fill.fore_color.rgb = C_WHITE
        card.line.color.rgb = C_BORDER
        
        cbar = s8.shapes.add_shape(MSO_SHAPE.RECTANGLE, bx, Inches(1.4), Inches(2.82), Inches(0.08))
        cbar.fill.solid()
        cbar.fill.fore_color.rgb = color
        cbar.line.fill.background()
        
        ctf = card.text_frame
        ctf.margin_left = ctf.margin_right = Inches(0.18)
        ctf.margin_top = Inches(0.2)
        
        p = ctf.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        
        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = "• " + b
            bp.font.size = Pt(9.5)
            bp.font.color.rgb = C_TEXT_BODY
            bp.space_before = Pt(8)

    # Bottom Audit Badge
    bb = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.85), Inches(11.733), Inches(1.1))
    bb.fill.solid()
    bb.fill.fore_color.rgb = C_TEXT_MAIN
    bb.line.fill.background()
    bbtf = bb.text_frame
    bbtf.margin_left = Inches(0.25)
    bbtf.margin_top = Inches(0.15)
    p = bbtf.paragraphs[0]
    p.text = "VERIFICATION RESULT: 100% REPRODUCIBLE OFF-LINE & ON-LINE DSS ENGINE"
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = C_AMBER
    
    p2 = bbtf.add_paragraph()
    p2.text = "Every number in SunNode is programmatically linked to raw DISCOM Annexure-D data, Google Earth Engine 10 m tiles, and EU JRC PVGIS v5.3 satellite APIs. Zero synthetic data or manual guesstimates."
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = RGBColor(226, 232, 240)
    p2.space_before = Pt(3)

    # --------------------------------------------------------------------------
    # SLIDE 9: Statewide Socio-Economic & Climate Impact
    # --------------------------------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9, C_LIGHT_BG)
    add_header(s9, "Statewide Economic, Rural & Climate Impact for Telangana")

    impacts = [
        ("₹252.05 Cr / yr", "Rural Landowner Income", C_EMERALD, [
            "Paid directly to rural agricultural landowners at ₹2.0 Lakh/MW/yr.",
            "Aggregates 56,700 contiguous farmland acres across 33 districts.",
            "Guarantees 25-year stable recurring revenue for farming families."
        ]),
        ("18,771.6 MU / yr", "Clean Solar Generation", C_AMBER, [
            "18.77 Billion kWh of zero-carbon power produced annually.",
            "Directly energizes agricultural solar feeder pumps under PM-KUSUM.",
            "Significantly reduces daytime transmission & distribution losses."
        ]),
        ("13.65 Million tCO₂", "Annual Emissions Abated", C_CYAN, [
            "Displaces 13.65 Million Tonnes of coal-fired thermal carbon emissions yearly.",
            "Accelerates Telangana's Renewable Purchase Obligation (RPO) compliance.",
            "Directly advances Government of India's 500 GW non-fossil target."
        ]),
        ("₹58,857.9 Cr", "25-Yr Cumulative Profit", C_TEXT_MAIN, [
            "Generates ₹58,858 Cr net profit after debt service & OPEX over 25 years.",
            "Safeguards ₹62,864 Cr from stranded capital by eliminating overloaded sites.",
            "Creates 14,000+ local green jobs in construction, O&M, and robotics cleaning."
        ])
    ]

    for idx, (val, title, color, bullets) in enumerate(impacts):
        bx = Inches(0.8 + idx * 2.95)
        card = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(1.4), Inches(2.82), Inches(4.2))
        card.fill.solid()
        card.fill.fore_color.rgb = C_WHITE
        card.line.color.rgb = C_BORDER
        
        ctf = card.text_frame
        ctf.margin_left = ctf.margin_right = Inches(0.18)
        ctf.margin_top = Inches(0.2)
        
        p = ctf.paragraphs[0]
        p.text = val
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = color
        
        p_title = ctf.add_paragraph()
        p_title.text = title.upper()
        p_title.font.size = Pt(10)
        p_title.font.bold = True
        p_title.font.color.rgb = C_TEXT_MAIN
        p_title.space_before = Pt(2)
        
        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = "• " + b
            bp.font.size = Pt(9.5)
            bp.font.color.rgb = C_TEXT_BODY
            bp.space_before = Pt(8)

    # Bottom Impact Banner
    ib = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.85), Inches(11.733), Inches(1.1))
    ib.fill.solid()
    ib.fill.fore_color.rgb = C_EMERALD
    ib.line.fill.background()
    ibtf = ib.text_frame
    ibtf.margin_left = Inches(0.25)
    ibtf.margin_top = Inches(0.15)
    p = ibtf.paragraphs[0]
    p.text = "INCLUSIVE CLEAN TRANSITION FOR TELANGANA"
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = C_DARK_BG
    
    p2 = ibtf.add_paragraph()
    p2.text = "SunNode transforms Telangana's transmission & distribution grid into an engine of rural prosperity, converting marginal agrarian land into high-yield, 25-year solar wealth while solving agricultural feeder power deficits."
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = C_DARK_BG
    p2.space_before = Pt(2)

    # --------------------------------------------------------------------------
    # SLIDE 10: Deployment Readiness & 90-Day Pilot Roadmap (Dark Bookend)
    # --------------------------------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10, C_DARK_BG)

    # Header
    tb = s10.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.9))
    tf = tb.text_frame
    p0 = tf.paragraphs[0]
    p0.text = "PRODUCTION READINESS & IMPLEMENTATION ROADMAP"
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = C_AMBER
    
    p1 = tf.add_paragraph()
    p1.text = "Deployed Today · 90-Day Rollout for Telangana Energy Department"
    p1.font.size = Pt(22)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.space_before = Pt(3)

    # Current Stage Card
    stage_card = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.733), Inches(1.3))
    stage_card.fill.solid()
    stage_card.fill.fore_color.rgb = C_DARK_CARD
    stage_card.line.color.rgb = C_BORDER_DRK
    stf = stage_card.text_frame
    stf.margin_left = Inches(0.25)
    stf.margin_top = Inches(0.15)
    
    p = stf.paragraphs[0]
    p.text = "CURRENT STAGE: DEPLOYED WORKING PROTOTYPE (VERCEL PRODUCTION EDGE CDN)"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    
    p2 = stf.add_paragraph()
    p2.text = "Live Web Application: https://sunnode.vercel.app  •  Evaluated all 391 substations across 33 districts."
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = C_WHITE
    p2.space_before = Pt(4)

    p3 = stf.add_paragraph()
    p3.text = "Deliverables Ready for Evaluators Today: 23-Sheet Master Excel Inventory (.xlsx), Google Earth 3D Package (.kmz), and 300 DPI Cartographic Map Atlas (.pdf)."
    p3.font.size = Pt(9.5)
    p3.font.color.rgb = RGBColor(203, 213, 225)
    p3.space_before = Pt(3)

    # 3-Phase 90-Day Roadmap Cards
    phases = [
        ("Phase 1: Days 1–30", C_CYAN, "Departmental Onboarding & SCADA Bridge", [
            "Integrate live TGTRANSCO & DISCOM SCADA load telemetry.",
            "Field ground-truth top 10 golden substations with local revenue officials.",
            "Establish secure single sign-on (SSO) for Energy Department engineers."
        ]),
        ("Phase 2: Days 31–60", C_AMBER, "Tender Packaging & DPR Generation", [
            "Auto-generate bankable DPR dossiers for priority PM-KUSUM feeder tenders.",
            "Overlay digital revenue survey numbers for instant farmer lease agreements.",
            "Release competitive reverse-auction bidding packages for 1,500 MW."
        ]),
        ("Phase 3: Days 61–90", C_EMERALD, "Statewide Rollout & Continuous Monitoring", [
            "Deploy SunNode portal across all DISCOM circle headquarters.",
            "Automate quarterly satellite farmland updates via Sentinel Dynamic World.",
            "Real-time grid headroom monitoring as new distributed solar comes online."
        ])
    ]

    for idx, (phase, color, subtitle, bullets) in enumerate(phases):
        bx = Inches(0.8 + idx * 3.95)
        pcard = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(2.95), Inches(3.8), Inches(3.1))
        pcard.fill.solid()
        pcard.fill.fore_color.rgb = C_DARK_CARD
        pcard.line.color.rgb = C_BORDER_DRK
        
        cbar = s10.shapes.add_shape(MSO_SHAPE.RECTANGLE, bx, Inches(2.95), Inches(3.8), Inches(0.06))
        cbar.fill.solid()
        cbar.fill.fore_color.rgb = color
        cbar.line.fill.background()
        
        ptf = pcard.text_frame
        ptf.margin_left = ptf.margin_right = Inches(0.2)
        ptf.margin_top = Inches(0.18)
        
        p = ptf.paragraphs[0]
        p.text = phase.upper()
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = color
        
        p_sub = ptf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(10)
        p_sub.font.bold = True
        p_sub.font.color.rgb = C_WHITE
        p_sub.space_before = Pt(2)
        
        for b in bullets:
            bp = ptf.add_paragraph()
            bp.text = "• " + b
            bp.font.size = Pt(9.5)
            bp.font.color.rgb = RGBColor(203, 213, 225)
            bp.space_before = Pt(6)

    # Bottom Contact & Link Bar
    bb = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.25), Inches(11.733), Inches(0.75))
    bb.fill.solid()
    bb.fill.fore_color.rgb = C_AMBER
    bb.line.fill.background()
    bbtf = bb.text_frame
    bbtf.margin_left = Inches(0.25)
    bbtf.margin_top = Inches(0.12)
    p = bbtf.paragraphs[0]
    p.text = "SUBMISSION CONTACT & LIVE EVALUATION PORTAL"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_DARK_BG
    
    p2 = bbtf.add_paragraph()
    p2.text = "Live WebApp: https://sunnode.vercel.app  •  GitHub: https://github.com/bhanu964/SunNode  •  Telangana Energy Department Challenge 10"
    p2.font.size = Pt(10)
    p2.font.bold = True
    p2.font.color.rgb = C_DARK_BG
    p2.space_before = Pt(2)

    prs.save(pptx_path)
    print(f"✅ Generated PPTX: {pptx_path} ({os.path.getsize(pptx_path) / 1024:.1f} KB)")


# ==============================================================================
# PART 2: NATIVE HIGH-RES PDF & PNG GENERATOR (PyMuPDF / fitz)
# ==============================================================================

def build_pdf_and_pngs(pdf_path, png_dir):
    doc = fitz.open()

    def new_canvas(dark=False):
        page = doc.new_page(width=WIDTH_PT, height=HEIGHT_PT)
        bg = F_DARK_BG if dark else F_LIGHT_BG
        page.draw_rect(fitz.Rect(0, 0, WIDTH_PT, HEIGHT_PT), color=bg, fill=bg)
        return page

    def draw_card(page, x, y, w, h, fill=F_WHITE, stroke=F_BORDER, radius=0.03):
        r = fitz.Rect(x, y, x + w, y + h)
        rad = min(0.08, radius) if (radius is not None and radius < 1.0) else 0.03
        page.draw_rect(r, color=stroke, fill=fill, radius=rad, width=1.2)

    def draw_header(page, title, cat="GOVERNMENT OF TELANGANA · ENERGY DEPARTMENT", dark=False):
        page.insert_text(fitz.Point(115, 75), cat.upper(), fontsize=13, color=F_AMBER if dark else F_TEXT_MUTED, fontname="helv")
        page.insert_text(fitz.Point(115, 115), title, fontsize=32, color=F_WHITE if dark else F_TEXT_MAIN, fontname="hebo")

    # --------------------------------------------------------------------------
    # SLIDE 1: Cover
    # --------------------------------------------------------------------------
    p1 = new_canvas(dark=True)
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(logo_path):
        p1.insert_image(fitz.Rect(115, 120, 305, 310), filename=logo_path)

    p1.insert_text(fitz.Point(340, 160), "GOVERNMENT OF TELANGANA  •  DEPARTMENT OF ENERGY  •  CHALLENGE 10", fontsize=16, color=F_AMBER, fontname="hebo")
    p1.insert_text(fitz.Point(115, 390), "SuryaGrid (SunNode)", fontsize=56, color=F_WHITE, fontname="hebo")
    p1.insert_text(fitz.Point(115, 460), "AI-Driven Solar Siting & Grid-Integration Decision Support System (DSS)", fontsize=32, color=F_AMBER, fontname="hebo")
    p1.insert_text(fitz.Point(115, 520), "Statewide Substation Land, Transformer Headroom & PVGIS Solar Generation Intelligence for PM-KUSUM & Utility-Scale STU Deployment", fontsize=18, color=(203/255, 213/255, 225/255), fontname="helv")

    # Live URL Button
    draw_card(p1, 115, 610, 600, 75, fill=F_EMERALD, stroke=F_EMERALD, radius=16)
    p1.insert_text(fitz.Point(145, 655), "🌐  LIVE PRODUCTION APP:  https://sunnode.vercel.app", fontsize=17, color=F_DARK_BG, fontname="hebo")

    # 3 Proof Pills
    pills = [
        ("391 Substations · 33 Districts", "100% Statewide Geographic Coverage"),
        ("12,602.6 MW True Deployable", "Bottleneck-Matched (Min Land, Grid)"),
        ("Live Deployed Prototype", "Zero-Latency Vercel Edge Architecture")
    ]
    for idx, (title, sub) in enumerate(pills):
        px = 115 + idx * 568
        draw_card(p1, px, 760, 546, 160, fill=F_DARK_CARD, stroke=F_BORDER_DRK, radius=16)
        p1.insert_text(fitz.Point(px + 28, 825), title, fontsize=20, color=F_WHITE, fontname="hebo")
        p1.insert_text(fitz.Point(px + 28, 875), sub, fontsize=14, color=F_TEXT_MUTED, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 2: Siting Crisis
    # --------------------------------------------------------------------------
    p2 = new_canvas(dark=False)
    draw_header(p2, "The Siting Crisis: Why Solar Rollout Stalls in Telangana")
    
    # Top Banner
    draw_card(p2, 115, 170, 1690, 180, fill=F_TEXT_MAIN, stroke=F_TEXT_MAIN, radius=16)
    p2.insert_text(fitz.Point(155, 220), "THE CENTRAL GRID BOTTLENECK DISCOVERED ACROSS 391 TELANGANA SUBSTATIONS", fontsize=14, color=F_AMBER, fontname="hebo")
    p2.insert_text(fitz.Point(155, 275), "29,366.4 MW Farmland Identified  ➔  Only 12,602.6 MW Truly Deployable", fontsize=27, color=F_WHITE, fontname="hebo")
    p2.insert_text(fitz.Point(155, 320), "65.2% (255 of 391) of substations are strictly Grid Transformer Constrained. Siting solar without transformer headroom guarantees interconnection failure.", fontsize=15, color=(226/255, 232/255, 240/255), fontname="helv")

    cards_s2 = [
        ("1. Manual Survey Paralysis", F_ROSE, [
            "Traditional manual walk-throughs take 3–6 months per site.",
            "Field scouts frequently miss seasonal water bodies, local slope > 5°, and strict 30 m FTL lake buffer compliance.",
            "High administrative friction delays DISCOM bidding schedules."
        ]),
        ("2. The Land-Grid Disconnect", F_CYAN, [
            "Developers lease massive farmland parcels only to discover the substation transformer MVA has zero spare headroom.",
            "Co-located 132 kV and 220 kV yards share overlapping 1 km radii, causing severe capacity double-counting.",
            "Utilities risk millions in stranded transmission capital."
        ]),
        ("3. Unverified Irradiance Risk", F_AMBER, [
            "Projects rely on generic state-level solar averages rather than location-specific satellite telemetry.",
            "A 5% irradiation deficit can trigger debt service (DSCR) default under tight ₹2.75–₹3.13/kWh regulated tariffs.",
            "Banks demand audited, month-by-month generation telemetry."
        ])
    ]
    for idx, (title, accent, bullets) in enumerate(cards_s2):
        cx = 115 + idx * 568
        draw_card(p2, cx, 390, 546, 590, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p2.draw_rect(fitz.Rect(cx, 390, cx + 546, 402), color=accent, fill=accent)
        p2.insert_text(fitz.Point(cx + 35, 455), title, fontsize=20, color=F_TEXT_MAIN, fontname="hebo")
        for b_idx, b in enumerate(bullets):
            r = fitz.Rect(cx + 35, 500 + b_idx * 135, cx + 510, 500 + (b_idx + 1) * 135)
            p2.insert_textbox(r, "•  " + b, fontsize=15.5, color=F_TEXT_BODY, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 3: 4-Layer Solution Engine
    # --------------------------------------------------------------------------
    p3 = new_canvas(dark=False)
    draw_header(p3, "The SunNode Solution: 4-Layer AI, GIS & Grid Engine")

    layers_s3 = [
        ("Layer 1: AI Land Suitability", F_EMERALD, "Google Earth Engine 10 m", [
            "10 m Sentinel Dynamic World V1 (12-mo mode composite) + USGS SRTM 30 m terrain slope.",
            "1 km Feeder Radius (~776 acres): Focuses strictly on lowest transmission loss zone.",
            "3-Tier Zoning: Green (Farmland/Bare ≤ 5°), Yellow (Canopy/Orchards), Red (Built-up, Water + 30 m FTL).",
            "Contiguous Core ≥ 4 acres: Filters isolated speckles to ensure buildable solar patches.",
            "Deduplication: Spatial union eliminates -617.5 MW co-located overlap across 27 clusters."
        ]),
        ("Layer 2: Grid Load & Headroom", F_CYAN, "DISCOM & TGTRANSCO Physics", [
            "TGRAC Layer 8 PTR MVA + 1-to-1 DISCOM Annexure-D verified spare evacuation capacities.",
            "Strict Bottleneck Rule: Deployable MW = Min(Land MW, Grid Headroom MW).",
            "Full AC Injection Current calculations: I = P / (√3 × V × 0.95).",
            "Dedicated Feeder Bay Sizing: 275 × 33 kV VCB, 85 × 132 kV SF6, 31 × 220 kV SF6.",
            "Safeguards grid stability by preventing reverse-power transformer overloading."
        ]),
        ("Layer 3: Real Solar Telemetry", F_AMBER, "100% EU JRC PVGIS v5.3 API", [
            "Zero synthetic or estimated data: Direct location-specific queries for all 391 substations.",
            "Daily & Annual Irradiance: Mean 5.51 kWh/m²/day (Range: 5.29 to 5.61 kWh/m²/day).",
            "Specific Yield: Mean 1,491.2 kWh/kWp/yr (1.49 MU/MW/yr clean electricity generation).",
            "Capacity Utilization Factor (CUF): Mean 17.02% (Range: 16.27% to 17.30%).",
            "Full 12-month Jan–Dec seasonal generation curves for exact bankable revenue modeling."
        ]),
        ("Layer 4: Bankable ROI Scoring", F_TEXT_MAIN, "Levelized Financial Modeling", [
            "Dual-Tier Tariffs: PM-KUSUM Feeder at ₹3.13/kWh; Utility-Scale STU at ₹2.75/kWh.",
            "Turnkey EPC Benchmark: ₹3.75 Cr/MW turnkey CAPEX.",
            "Financial Metrics: Annual revenue, net EBITDA, simple payback (10.13 yrs statewide average).",
            "Composite Score (0–100): Weighted by deployable capacity (150 MW cap), payback speed, CUF.",
            "Farmer Prosperity: ₹252.05 Cr/yr direct rural land lease income (₹2.0 Lakh/MW/yr)."
        ])
    ]
    for idx, (title, color, tag, bullets) in enumerate(layers_s3):
        col = idx % 2
        row = idx // 2
        lx = 115 + col * 860
        ly = 170 + row * 410
        draw_card(p3, lx, ly, 830, 375, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p3.draw_rect(fitz.Rect(lx, ly, lx + 16, ly + 375), color=color, fill=color)
        p3.insert_text(fitz.Point(lx + 40, ly + 50), title, fontsize=20, color=F_TEXT_MAIN, fontname="hebo")
        p3.insert_text(fitz.Point(lx + 40, ly + 78), tag.upper(), fontsize=12, color=color, fontname="hebo")
        for b_idx, b in enumerate(bullets):
            r = fitz.Rect(lx + 40, ly + 100 + b_idx * 52, lx + 800, ly + 100 + (b_idx + 1) * 52)
            p3.insert_textbox(r, "• " + b, fontsize=13.5, color=F_TEXT_BODY, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 4: Live Product Showcase 1 — Dashboard
    # --------------------------------------------------------------------------
    p4 = new_canvas(dark=False)
    draw_header(p4, "Live Product Showcase 1: Statewide Executive Dashboard & KPIs")
    
    img_dash = os.path.join(ASSETS_DIR, "framed_dashboard.jpeg")
    if not os.path.exists(img_dash):
        img_dash = os.path.join(ASSETS_DIR, "framed_dashboard.png")
    if os.path.exists(img_dash):
        p4.insert_image(fitz.Rect(115, 170, 1175, 960), filename=img_dash)

    kpis_s4 = [
        ("12,602.6 MW", "True Deployable Solar", F_EMERALD, "Deduplicated grid-matched solar across 391 substations (after eliminating 617.5 MW co-located overlap)."),
        ("₹47,259.5 Cr", "Turnkey CAPEX Investment", F_CYAN, "Total EPC investment required at Telangana ₹3.75 Cr/MW benchmark for 100% capacity realization."),
        ("₹5,484.1 Cr / yr", "Annual Gross Revenue", F_AMBER, "Combined clean energy generation revenue under regulated ₹2.75 & ₹3.13/kWh feed-in tariffs."),
        ("10.13 Years", "Aggregate Simple Payback", F_TEXT_MAIN, "Statewide average capital recovery period, ensuring commercial bankability and debt service (> 1.20x DSCR).")
    ]
    for idx, (val, label, color, desc) in enumerate(kpis_s4):
        ky = 170 + idx * 200
        draw_card(p4, 1215, ky, 590, 180, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p4.insert_text(fitz.Point(1245, ky + 52), val, fontsize=28, color=color, fontname="hebo")
        p4.insert_text(fitz.Point(1245, ky + 85), label.upper(), fontsize=13.5, color=F_TEXT_MAIN, fontname="hebo")
        r = fitz.Rect(1245, ky + 100, 1775, ky + 165)
        p4.insert_textbox(r, desc, fontsize=12.5, color=F_TEXT_MUTED, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 5: Live Product Showcase 2 — GIS & Solar Irradiance
    # --------------------------------------------------------------------------
    p5 = new_canvas(dark=False)
    draw_header(p5, "Live Product Showcase 2: Satellite GIS & Solar Irradiance Explorer")
    
    # URL Pill
    draw_card(p5, 1325, 60, 480, 55, fill=F_TEXT_MAIN, stroke=F_TEXT_MAIN, radius=12)
    p5.insert_text(fitz.Point(1355, 97), "🌐  https://sunnode.vercel.app", fontsize=15, color=F_AMBER, fontname="hebo")

    img_map = os.path.join(ASSETS_DIR, "framed_map_satellite.jpeg")
    if not os.path.exists(img_map):
        img_map = os.path.join(ASSETS_DIR, "framed_map_satellite.png")
    if os.path.exists(img_map):
        p5.insert_image(fitz.Rect(115, 170, 1150, 780), filename=img_map)

    img_insp = os.path.join(ASSETS_DIR, "framed_inspector.jpeg")
    if not os.path.exists(img_insp):
        img_insp = os.path.join(ASSETS_DIR, "framed_inspector.png")
    if os.path.exists(img_insp):
        p5.insert_image(fitz.Rect(1185, 170, 1805, 780), filename=img_insp)

    feats_s5 = [
        ("Dual Verification Map", "Evaluators see both how much sun energy reaches the yard and whether the 1 km terrain + transformer headroom can host it."),
        ("Thermal Irradiance Heatmap", "Color markers by real PVGIS sun energy: Tier-1 (≥ 5.55 kWh/m²/d, #EA580C), Tier-2 (5.45–5.55, #F59E0B), Tier-3 (< 5.45, #EAB308)."),
        ("12-Month PVGIS Curves", "The 4-Layer Inspector plots real Jan–Dec seasonal generation bars (kWh/kWp) alongside bay current & financial metrics.")
    ]
    for idx, (title, desc) in enumerate(feats_s5):
        fx = 115 + idx * 568
        draw_card(p5, fx, 810, 546, 170, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p5.insert_text(fitz.Point(fx + 25, 855), title, fontsize=17, color=F_TEXT_MAIN, fontname="hebo")
        r = fitz.Rect(fx + 25, 875, fx + 520, 960)
        p5.insert_textbox(r, desc, fontsize=13, color=F_TEXT_BODY, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 6: Live Product Showcase 3 — Wizard & ROI
    # --------------------------------------------------------------------------
    p6 = new_canvas(dark=False)
    draw_header(p6, "Live Product Showcase 3: 30-Second Siting Wizard & Bankable ROI Simulator")

    img_wiz = os.path.join(ASSETS_DIR, "framed_wizard.jpeg")
    if not os.path.exists(img_wiz):
        img_wiz = os.path.join(ASSETS_DIR, "framed_wizard.png")
    if os.path.exists(img_wiz):
        p6.insert_image(fitz.Rect(115, 170, 940, 780), filename=img_wiz)

    img_roi = os.path.join(ASSETS_DIR, "framed_roi.jpeg")
    if not os.path.exists(img_roi):
        img_roi = os.path.join(ASSETS_DIR, "framed_roi.png")
    if os.path.exists(img_roi):
        p6.insert_image(fitz.Rect(975, 170, 1805, 780), filename=img_roi)

    workflow_s6 = [
        ("Step 1–2: Criteria Input", "Select Utility EHT vs. PM-KUSUM feeder track, target capacity range, and district constraints in seconds."),
        ("Step 3: Top-3 Automated Matching", "Algorithmic multi-criteria scoring surfaces the top 3 optimal substations with highest spare headroom & lowest land slope."),
        ("Step 4: Bankable DPR Export", "One-click generation of bankable DPR dossiers with 25-yr cash flows, DSCR (> 1.20x), and GEE satellite coordinates.")
    ]
    for idx, (title, desc) in enumerate(workflow_s6):
        wx = 115 + idx * 568
        draw_card(p6, wx, 810, 546, 170, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p6.insert_text(fitz.Point(wx + 25, 855), title, fontsize=17, color=F_TEXT_MAIN, fontname="hebo")
        r = fitz.Rect(wx + 25, 875, wx + 520, 960)
        p6.insert_textbox(r, desc, fontsize=13, color=F_TEXT_BODY, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 7: Statewide Priority Leaderboards
    # --------------------------------------------------------------------------
    p7 = new_canvas(dark=False)
    draw_header(p7, "Statewide Priority Leaderboards: Utility EHT vs. PM-KUSUM")

    # Table 1 Header
    draw_card(p7, 115, 170, 825, 55, fill=F_TEXT_MAIN, stroke=F_TEXT_MAIN, radius=10)
    p7.insert_text(fitz.Point(145, 205), "⚡ TOP 5 UTILITY-SCALE EHT SUBSTATIONS (220/400 kV @ ₹2.75/kWh STU)", fontsize=14, color=F_WHITE, fontname="hebo")

    # Table 1 Rows
    eht_rows = [
        ("Kosigi", "Narayanpet", "126.6 MW", "72.1 (3 Bays)"),
        ("Veltoor", "Wanaparthy", "133.2 MW", "71.9 (2 Bays)"),
        ("Kalluru", "Khammam", "135.0 MW", "71.5 (3 Bays)"),
        ("Miryalaguda", "Nalgonda", "134.3 MW", "71.3 (3 Bays)"),
        ("Dichpally 400kV", "Nizamabad", "129.2 MW", "71.3 (2 Bays)")
    ]
    for idx, (name, dist, mw, score) in enumerate(eht_rows):
        ry = 235 + idx * 65
        bg = (241/255, 245/255, 249/255) if idx % 2 == 1 else F_WHITE
        draw_card(p7, 115, ry, 825, 60, fill=bg, stroke=F_BORDER, radius=6)
        p7.insert_text(fitz.Point(140, ry + 38), name, fontsize=15, color=F_TEXT_MAIN, fontname="hebo")
        p7.insert_text(fitz.Point(380, ry + 38), dist, fontsize=14, color=F_TEXT_BODY, fontname="helv")
        p7.insert_text(fitz.Point(580, ry + 38), mw, fontsize=15, color=F_EMERALD, fontname="hebo")
        p7.insert_text(fitz.Point(740, ry + 38), score, fontsize=13.5, color=F_TEXT_MUTED, fontname="helv")

    # Table 2 Header
    draw_card(p7, 980, 170, 825, 55, fill=F_AMBER, stroke=F_AMBER, radius=10)
    p7.insert_text(fitz.Point(1010, 205), "🌾 TOP 5 PM-KUSUM FEEDER CLUSTERS (132/33 kV @ ₹3.13/kWh REGULATED)", fontsize=14, color=F_DARK_BG, fontname="hebo")

    kusum_rows = [
        ("Sircilla", "Rajanna Sircilla", "81.0 MW", "59.6 (5 Bays)"),
        ("Parigi", "Vikarabad", "67.5 MW", "58.3 (4 Bays)"),
        ("Gajwel", "Siddipet", "72.0 MW", "57.7 (5 Bays)"),
        ("Gangadhara", "Karimnagar", "62.3 MW", "55.0 (4 Bays)"),
        ("Marriguda", "Nalgonda", "59.1 MW", "53.9 (4 Bays)")
    ]
    for idx, (name, dist, mw, score) in enumerate(kusum_rows):
        ry = 235 + idx * 65
        bg = (241/255, 245/255, 249/255) if idx % 2 == 1 else F_WHITE
        draw_card(p7, 980, ry, 825, 60, fill=bg, stroke=F_BORDER, radius=6)
        p7.insert_text(fitz.Point(1005, ry + 38), name, fontsize=15, color=F_TEXT_MAIN, fontname="hebo")
        p7.insert_text(fitz.Point(1250, ry + 38), dist, fontsize=14, color=F_TEXT_BODY, fontname="helv")
        p7.insert_text(fitz.Point(1450, ry + 38), mw, fontsize=15, color=F_AMBER, fontname="hebo")
        p7.insert_text(fitz.Point(1610, ry + 38), score, fontsize=13.5, color=F_TEXT_MUTED, fontname="helv")

    # Bottom Recommendation Box
    draw_card(p7, 115, 660, 1690, 170, fill=F_WHITE, stroke=F_BORDER, radius=16)
    p7.insert_text(fitz.Point(155, 710), "STRATEGIC TENDERING RECOMMENDATION FOR TELANGANA ENERGY DEPARTMENT", fontsize=15, color=F_TEXT_MAIN, fontname="hebo")
    r1 = fitz.Rect(155, 725, 1750, 770)
    p7.insert_textbox(r1, "• Phase 1 Tendering (Immediate): Issue 1,500 MW across the Top-10 EHT & PM-KUSUM substations where contiguous flat farmland (≥ 4 ac) and transformer bays are 100% verified.", fontsize=14, color=F_TEXT_BODY, fontname="helv")
    r2 = fitz.Rect(155, 775, 1750, 815)
    p7.insert_textbox(r2, "• Direct Farmer Benefit: These top 10 sites immediately distribute ₹45.8 Cr/year in direct lease income to rural farming households.", fontsize=14, color=F_EMERALD, fontname="hebo")

    # --------------------------------------------------------------------------
    # SLIDE 8: Engineering Rigor & Data Integrity Audit
    # --------------------------------------------------------------------------
    p8 = new_canvas(dark=False)
    draw_header(p8, "Engineering Rigor & Data Integrity Audit (Why Evaluators Can Trust This)")

    audits_s8 = [
        ("1-to-1 Annexure-D Matching", F_EMERALD, [
            "Resolved co-located substation duplication (e.g. Dichpally 220 kV vs. 400 kV yards).",
            "Enforced strict 1-to-1 voltage-aware matching, ensuring zero double-counted spare capacity.",
            "Deduplicated 27 spatial overlap clusters, removing 617.5 MW phantom capacity."
        ]),
        ("Official 33-District Normalization", F_CYAN, [
            "Rigorous spatial point-in-polygon joins matching official Survey of India boundary.",
            "100% clean revenue district naming (zero legacy fragments like 'Rangareddy' or 'UNKNOWN').",
            "Every single substation mapped with verified 5-decimal GPS coordinates."
        ]),
        ("Strict Grid-Code Bay Sizing", F_AMBER, [
            "Calculated full 3-phase AC injection currents: I = P / (√3 × V × 0.95).",
            "Sized exact switchgear: 275 × 33 kV VCB (630A limit), 85 × 132 kV SF6 (1250A limit), 31 × 220 kV SF6 (1600A limit).",
            "Ensures transformer impedance compliance without busbar fault hazards."
        ]),
        ("100% Automated Test Coverage", F_TEXT_MAIN, [
            "16/16 automated Python unit tests passing in continuous CI test harness.",
            "Zero nulls, zero NaNs across all 391 substation rows in master CSV & JSON datasets.",
            "Fully verified 23-sheet Master Excel, 3D KMZ, and cartographic PDF atlas."
        ])
    ]
    for idx, (title, color, bullets) in enumerate(audits_s8):
        ax = 115 + idx * 424
        draw_card(p8, ax, 170, 404, 600, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p8.draw_rect(fitz.Rect(ax, 170, ax + 404, 182), color=color, fill=color)
        p8.insert_text(fitz.Point(ax + 24, 230), title, fontsize=17, color=F_TEXT_MAIN, fontname="hebo")
        for b_idx, b in enumerate(bullets):
            r = fitz.Rect(ax + 24, 270 + b_idx * 130, ax + 380, 270 + (b_idx + 1) * 130)
            p8.insert_textbox(r, "• " + b, fontsize=13.5, color=F_TEXT_BODY, fontname="helv")

    # Bottom Audit Box
    draw_card(p8, 115, 810, 1690, 155, fill=F_TEXT_MAIN, stroke=F_TEXT_MAIN, radius=16)
    p8.insert_text(fitz.Point(155, 855), "VERIFICATION RESULT: 100% REPRODUCIBLE OFF-LINE & ON-LINE DSS ENGINE", fontsize=15, color=F_AMBER, fontname="hebo")
    r_audit = fitz.Rect(155, 875, 1750, 945)
    p8.insert_textbox(r_audit, "Every number in SunNode is programmatically linked to raw DISCOM Annexure-D data, Google Earth Engine 10 m tiles, and EU JRC PVGIS v5.3 satellite APIs. Zero synthetic data or manual guesstimates.", fontsize=14, color=(226/255, 232/255, 240/255), fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 9: Statewide Socio-Economic & Climate Impact
    # --------------------------------------------------------------------------
    p9 = new_canvas(dark=False)
    draw_header(p9, "Statewide Economic, Rural & Climate Impact for Telangana")

    impacts_s9 = [
        ("₹252.05 Cr / yr", "Rural Landowner Income", F_EMERALD, [
            "Paid directly to rural agricultural landowners at ₹2.0 Lakh/MW/yr.",
            "Aggregates 56,700 contiguous farmland acres across 33 districts.",
            "Guarantees 25-year stable recurring revenue for farming families."
        ]),
        ("18,771.6 MU / yr", "Clean Solar Generation", F_AMBER, [
            "18.77 Billion kWh of zero-carbon power produced annually.",
            "Directly energizes agricultural solar feeder pumps under PM-KUSUM.",
            "Significantly reduces daytime transmission & distribution losses."
        ]),
        ("13.65 Million tCO₂", "Annual Emissions Abated", F_CYAN, [
            "Displaces 13.65 Million Tonnes of coal-fired thermal carbon emissions yearly.",
            "Accelerates Telangana's Renewable Purchase Obligation (RPO) compliance.",
            "Directly advances Government of India's 500 GW non-fossil target."
        ]),
        ("₹58,857.9 Cr", "25-Yr Cumulative Profit", F_TEXT_MAIN, [
            "Generates ₹58,858 Cr net profit after debt service & OPEX over 25 years.",
            "Safeguards ₹62,864 Cr from stranded capital by eliminating overloaded sites.",
            "Creates 14,000+ local green jobs in construction, O&M, and robotics cleaning."
        ])
    ]
    for idx, (val, title, color, bullets) in enumerate(impacts_s9):
        ix = 115 + idx * 424
        draw_card(p9, ix, 170, 404, 600, fill=F_WHITE, stroke=F_BORDER, radius=16)
        p9.insert_text(fitz.Point(ix + 24, 235), val, fontsize=27, color=color, fontname="hebo")
        p9.insert_text(fitz.Point(ix + 24, 275), title.upper(), fontsize=13, color=F_TEXT_MAIN, fontname="hebo")
        for b_idx, b in enumerate(bullets):
            r = fitz.Rect(ix + 24, 310 + b_idx * 115, ix + 380, 310 + (b_idx + 1) * 115)
            p9.insert_textbox(r, "• " + b, fontsize=13.5, color=F_TEXT_BODY, fontname="helv")

    # Bottom Impact Banner
    draw_card(p9, 115, 810, 1690, 155, fill=F_EMERALD, stroke=F_EMERALD, radius=16)
    p9.insert_text(fitz.Point(155, 855), "INCLUSIVE CLEAN TRANSITION FOR TELANGANA", fontsize=15, color=F_DARK_BG, fontname="hebo")
    r_imp = fitz.Rect(155, 875, 1750, 945)
    p9.insert_textbox(r_imp, "SunNode transforms Telangana's transmission & distribution grid into an engine of rural prosperity, converting marginal agrarian land into high-yield, 25-year solar wealth while solving agricultural feeder power deficits.", fontsize=14, color=F_DARK_BG, fontname="helv")

    # --------------------------------------------------------------------------
    # SLIDE 10: Deployment Readiness & 90-Day Roadmap (Dark Bookend)
    # --------------------------------------------------------------------------
    p10 = new_canvas(dark=True)
    draw_header(p10, "Deployment Readiness & 90-Day Implementation Roadmap", "PRODUCTION-READY DSS · READY FOR IMMEDIATE DEPARTMENTAL INTEGRATION", dark=True)

    # Current Stage Box
    draw_card(p10, 115, 170, 1690, 190, fill=F_DARK_CARD, stroke=F_BORDER_DRK, radius=16)
    p10.insert_text(fitz.Point(155, 220), "CURRENT STAGE: DEPLOYED WORKING PROTOTYPE (VERCEL PRODUCTION EDGE CDN)", fontsize=15, color=F_EMERALD, fontname="hebo")
    p10.insert_text(fitz.Point(155, 270), "Live Web Application: https://sunnode.vercel.app  •  Evaluated all 391 substations across 33 districts.", fontsize=18, color=F_WHITE, fontname="hebo")
    p10.insert_text(fitz.Point(155, 320), "Deliverables Ready for Evaluators Today: 23-Sheet Master Excel Inventory (.xlsx), Google Earth 3D Package (.kmz), and 300 DPI Cartographic Map Atlas (.pdf).", fontsize=14, color=(203/255, 213/255, 225/255), fontname="helv")

    phases_s10 = [
        ("Phase 1: Days 1–30", F_CYAN, "Departmental Onboarding & SCADA Bridge", [
            "Integrate live TGTRANSCO & DISCOM SCADA load telemetry.",
            "Field ground-truth top 10 golden substations with local revenue officials.",
            "Establish secure single sign-on (SSO) for Energy Department engineers."
        ]),
        ("Phase 2: Days 31–60", F_AMBER, "Tender Packaging & DPR Generation", [
            "Auto-generate bankable DPR dossiers for priority PM-KUSUM feeder tenders.",
            "Overlay digital revenue survey numbers for instant farmer lease agreements.",
            "Release competitive reverse-auction bidding packages for 1,500 MW."
        ]),
        ("Phase 3: Days 61–90", F_EMERALD, "Statewide Rollout & Continuous Monitoring", [
            "Deploy SunNode portal across all DISCOM circle headquarters.",
            "Automate quarterly satellite farmland updates via Sentinel Dynamic World.",
            "Real-time grid headroom monitoring as new distributed solar comes online."
        ])
    ]
    for idx, (phase, color, subtitle, bullets) in enumerate(phases_s10):
        px = 115 + idx * 568
        draw_card(p10, px, 400, 546, 420, fill=F_DARK_CARD, stroke=F_BORDER_DRK, radius=16)
        p10.draw_rect(fitz.Rect(px, 400, px + 546, 412), color=color, fill=color)
        p10.insert_text(fitz.Point(px + 28, 455), phase.upper(), fontsize=18, color=color, fontname="hebo")
        p10.insert_text(fitz.Point(px + 28, 495), subtitle, fontsize=14, color=F_WHITE, fontname="hebo")
        for b_idx, b in enumerate(bullets):
            r = fitz.Rect(px + 28, 525 + b_idx * 90, px + 518, 525 + (b_idx + 1) * 90)
            p10.insert_textbox(r, "• " + b, fontsize=13.5, color=(203/255, 213/255, 225/255), fontname="helv")

    # Bottom Contact Bar
    draw_card(p10, 115, 860, 1690, 100, fill=F_AMBER, stroke=F_AMBER, radius=16)
    p10.insert_text(fitz.Point(155, 905), "SUBMISSION CONTACT & LIVE EVALUATION PORTAL", fontsize=13.5, color=F_DARK_BG, fontname="hebo")
    p10.insert_text(fitz.Point(155, 938), "Live WebApp: https://sunnode.vercel.app  •  GitHub: https://github.com/bhanu964/SunNode  •  Telangana Energy Department Challenge 10", fontsize=15, color=F_DARK_BG, fontname="hebo")

    doc.save(pdf_path, deflate=True, garbage=4)
    print(f"✅ Generated PDF: {pdf_path} ({os.path.getsize(pdf_path) / (1024*1024):.2f} MB)")

    # Export PNGs for visual inspection
    print("Rendering slides to high-resolution PNGs for Visual QA...")
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        png_name = f"slide_{page_idx+1:02d}.png"
        png_path = os.path.join(png_dir, png_name)
        pix.save(png_path)
        print(f"  Slide {page_idx+1}: {png_path} ({pix.width}x{pix.height})")


if __name__ == "__main__":
    pptx_out = os.path.join(OUTPUTS_DIR, "SuryaGrid_Telangana_Energy_Innovation_Pitch_Deck.pptx")
    pdf_out = os.path.join(OUTPUTS_DIR, "SuryaGrid_Telangana_Energy_Innovation_Pitch_Deck.pdf")
    
    print("\n--- 1. Building PowerPoint Presentation (.pptx) ---")
    build_pptx_deck(pptx_out)
    
    print("\n--- 2. Building High-Resolution Executive PDF (.pdf) & PNG Inspection Slides ---")
    build_pdf_and_pngs(pdf_out, SLIDES_PNG_DIR)
    
    print("\n🎉 Pitch Deck Generation Completed Successfully!")
