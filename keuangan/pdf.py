"""Ubah HTML laporan sederhana (judul, daftar, tabel) jadi PDF langsung, tanpa harus dicetak dari peramban."""
import io
import re
from html import escape
from html.parser import HTMLParser

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HIJAU = colors.HexColor("#1f6b49")
S_P = ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#0b1220"))
S_H1 = ParagraphStyle("h1", parent=S_P, fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=HIJAU, spaceAfter=6)
S_H2 = ParagraphStyle("h2", parent=S_P, fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=14, spaceAfter=2)


def _bersih(t: str) -> str:
    t = t.replace("→", "ke").replace("–", "-").replace("≥", ">=")
    return re.sub(r"[^\x00-\xff]", "", t)  # emoji dan simbol di luar huruf latin tidak ada di fon PDF bawaan


class _Penguraian(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blok = []          # elemen reportlab
        self.buf = ""           # teks sebaris yang sedang dikumpulkan
        self.jenis = None       # h1 | h2 | p | li | td
        self.daftar = None      # list item sementara
        self.tabel = None       # baris tabel sementara
        self.baris = None
        self.lewati = 0         # kedalaman elemen yang diabaikan (<style>, <title>, batang <div>)
        self.tumpuk = []

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("style", "title", "head"):
            self.lewati += 1
            self.tumpuk.append(tag)
        elif tag == "div" and self.jenis == "td":
            self.lewati += 1
            self.tumpuk.append("div")
        elif tag in ("h1", "h2", "p"):
            self.jenis, self.buf = tag, ""
        elif tag == "ul":
            self.daftar = []
        elif tag == "li":
            self.jenis, self.buf = "li", ""
        elif tag == "table":
            self.tabel = []
        elif tag == "tr":
            self.baris = []
        elif tag in ("td", "th"):
            self.jenis, self.buf = "td", ""
            self.kepala = tag == "th"
        elif tag in ("b", "strong") and not self.lewati:
            self.buf += "<b>"
        elif tag == "br" and not self.lewati:
            self.buf += "<br/>"

    def handle_endtag(self, tag):
        if self.tumpuk and tag == self.tumpuk[-1]:
            self.tumpuk.pop()
            self.lewati -= 1
            return
        if self.lewati:
            return
        if tag in ("b", "strong"):
            self.buf += "</b>"
        elif tag in ("h1", "h2"):
            self.blok.append(Paragraph(self.buf, S_H1 if tag == "h1" else S_H2))
            if tag == "h2":
                self.blok.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#34a874"), spaceAfter=4))
            self.jenis = None
        elif tag == "p":
            self.blok.append(Paragraph(self.buf, S_P))
            self.blok.append(Spacer(1, 4))
            self.jenis = None
        elif tag == "li":
            if self.daftar is not None:
                self.daftar.append(ListItem(Paragraph(self.buf, S_P), leftIndent=14))
            self.jenis = None
        elif tag == "ul":
            if self.daftar:
                self.blok.append(ListFlowable(self.daftar, bulletType="bullet", start="•", leftIndent=14, bulletFontSize=8))
            self.daftar = None
        elif tag in ("td", "th"):
            gaya = ParagraphStyle("c", parent=S_P, fontName="Helvetica-Bold" if self.kepala else "Helvetica",
                                  alignment=0 if (self.baris is not None and not self.baris) else 2)
            self.baris.append(Paragraph(self.buf, gaya))
            self.jenis = None
        elif tag == "tr":
            if self.baris:
                self.tabel.append(self.baris)
            self.baris = None
        elif tag == "table":
            if self.tabel:
                n = max(len(r) for r in self.tabel)
                for r in self.tabel:
                    r.extend([""] * (n - len(r)))
                t = Table(self.tabel, colWidths=[None] + [28 * mm] * (n - 1), repeatRows=0)
                t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                                       ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                       ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
                self.blok.append(t)
            self.tabel = None

    def handle_data(self, data):
        if self.lewati or self.jenis is None:
            return
        self.buf += escape(_bersih(re.sub(r"\s+", " ", data)))


def html_ke_pdf(isi_html: str, judul: str = "Laporan") -> bytes:
    p = _Penguraian()
    p.feed(isi_html)
    out = io.BytesIO()
    SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                      title=_bersih(judul)).build(p.blok or [Paragraph("Tidak ada data.", S_P)])
    return out.getvalue()
