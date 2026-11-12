"""Shared figure style for the ORCHID paper (Digital Discovery) (main text, SI and the ESPEI-demo figures).

Import before plotting:  from style import *   (or: import style; style.apply())
Nature art direction: Arial 6-7 pt (minimum 5 pt), bold lowercase 8 pt panel labels at the top-left outside the axes,
widths exactly 89 mm (single column) or 183 mm (double), height <= 170 mm, saved at final size; 0.5 pt left/bottom
spines, outward 2 pt ticks, no grid, no titles inside panels, sentence-case axis labels with units in parentheses.
Palette: Okabe-Ito, fixed meanings across every figure.
"""
import os
import matplotlib
from matplotlib import font_manager

MM = 1 / 25.4
W1, W2, HMAX = 89 * MM, 183 * MM, 170 * MM

# fixed meanings (do not reuse these colours for anything else)
C_EXP = "#0072B2"        # experimental
C_MODEL = "#D55E00"      # model (CALPHAD or other thermodynamic model)
C_MP = "#009E73"         # DFT, Materials Project
C_OQMD = "#56B4E9"       # DFT, OQMD
C_LITDFT = "#CC79A7"     # DFT printed in the literature
C_ASSESSED = "#E69F00"   # assessed phase diagram (handbook)
C_UNSPEC = "#999999"     # unspecified
ACCENT = "#7B3FA0"       # ORCHID accent: highlights / refined model only
MONO = "Courier New"     # monospace for JSON / code excerpts only
INK = "#000000"
INK2 = "#4D4D4D"         # neutral ink
GREY_L, GREY_M = "#E8E8E8", "#BDBDBD"
C_DFT = C_MP             # generic DFT class colour when the source is not distinguished

EVC = {"experimental": C_EXP, "model": C_MODEL, "dft": C_MP, "unspecified": C_UNSPEC,
       "assessed_phase_diagram": C_ASSESSED}
EVL = {"experimental": "Experimental", "model": "Model", "dft": "DFT", "unspecified": "Unspecified",
       "assessed_phase_diagram": "Assessed diagram"}
SRC = {"mp": C_MP, "oqmd": C_OQMD, "literature": C_LITDFT}
SRCL = {"mp": "Materials Project", "oqmd": "OQMD", "literature": "Literature DFT"}
# light fills for schematics (same hues, ~15 % strength)
FILL = {"experimental": "#E0EDF6", "model": "#FAE7DC", "mp": "#DDF2EC", "oqmd": "#E7F4FC", "literature": "#F8EBF3",
        "assessed": "#FCF0DA", "neutral": "#F2F2F2", "accent": "#EFE7F4"}

UNIT_KJA = r"kJ (mol of atoms)$^{-1}$"


def _register_arial():
    for f in ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf", "Courier New.ttf",
              "Courier New Bold.ttf"):
        p = os.path.join("/System/Library/Fonts/Supplemental", f)
        if os.path.exists(p):
            font_manager.fontManager.addfont(p)


# Sub- and superscripts (mathtext) are drawn at SHRINK x the base size; matplotlib's default 0.7 puts the subscripts
# of 6-7 pt labels below the 5 pt minimum (audit A5 F10). 0.85 keeps them >= 5.1 pt for a 6 pt base;
# tests/test_figure_fonts.py checks every figure PDF.
MATHTEXT_SHRINK = 0.85


def apply():
    _register_arial()
    import matplotlib._mathtext as _mt
    _mt.SHRINK_FACTOR = MATHTEXT_SHRINK
    matplotlib.rcParams.update({
        "font.family": "Arial", "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "legend.frameon": False,
        "axes.linewidth": 0.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "xtick.direction": "out", "ytick.direction": "out", "xtick.major.size": 2, "ytick.major.size": 2,
        "xtick.minor.size": 1.2, "ytick.minor.size": 1.2, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
        "xtick.minor.width": 0.4, "ytick.minor.width": 0.4, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
        "axes.labelpad": 2, "lines.linewidth": 0.8, "patch.linewidth": 0.5, "hatch.linewidth": 0.4,
        "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 600, "mathtext.default": "regular",
        "mathtext.fontset": "custom", "mathtext.rm": "Arial", "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold",
        "figure.constrained_layout.h_pad": 0.02, "figure.constrained_layout.w_pad": 0.02})


def panel_label(ax, s, pad_mm=1.0):
    """Bold lowercase 8 pt panel label at the top-left, outside the axes, aligned with the left edge of the axes'
    tick labels / y label. Implemented as a left-aligned axes title so constrained layout reserves its space."""
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    tb = ax.get_tightbbox(r, for_layout_only=True)
    ab = ax.get_window_extent(r)
    x = (tb.x0 - ab.x0) / max(ab.width, 1) - pad_mm * MM * fig.dpi / max(ab.width, 1) * 0
    ax.set_title(s, loc="left", fontsize=8, fontweight="bold", x=x, pad=3)


apply()
