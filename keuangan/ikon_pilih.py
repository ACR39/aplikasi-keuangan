"""Pemilih ikon berbentuk kotak-kotak glyph satu warna, dengan pencarian. Di luar st.form supaya langsung bereaksi."""
import json
import re
from urllib.parse import quote

import streamlit as st

from keuangan.ikon_svg import GLIF
from keuangan.inti import IKON_NAMA, IKON_PILIHAN, ikon_html

KOLOM = 6


def _css(kunci: str, nama: list) -> str:
    aturan = []
    for n in nama:
        uri = "data:image/svg+xml," + quote(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="{GLIF[n][2]}"/></svg>')
        aturan.append(f'.st-key-{kunci}_g_{n.replace("-", "_")} button::after{{-webkit-mask-image:url("{uri}");mask-image:url("{uri}")}}')
    return (f'.st-key-{kunci}_kisi [data-testid="stHorizontalBlock"]{{flex-wrap:nowrap!important;gap:.4rem!important}}'
            f'.st-key-{kunci}_kisi [data-testid="stColumn"]{{min-width:0!important;flex:1 1 0!important;width:auto!important}}'
            f'.st-key-{kunci}_kisi button{{min-height:2.7rem;padding:0;display:flex;justify-content:center;align-items:center}}.st-key-{kunci}_kisi button p{{display:none}}'
            f'.st-key-{kunci}_kisi button::after{{content:"";width:1.7rem;height:1.7rem;background:currentColor;-webkit-mask-size:contain;mask-size:contain;'
            f'-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;mask-position:center}}' + "".join(aturan))


def pilih_ikon(kunci: str, awal: str, label: str = "Ikon") -> str:
    """Kembalikan ikon terpilih ('mdi:nama' atau emoji lama). Nilai awal dipakai sekali; selanjutnya mengikuti pilihan pengguna."""
    sk = f"{kunci}_nilai"
    if st.session_state.get(f"{sk}_awal", None) != awal or sk not in st.session_state:
        st.session_state[sk] = awal if awal else "mdi:home"
        st.session_state[f"{sk}_awal"] = awal
    nilai = st.session_state[sk]
    st.markdown(f'<div class="pil-ik"><span class="pv">{ikon_html(nilai)}</span> <b>{label}</b></div>', unsafe_allow_html=True)
    with st.popover("Ganti ikon"):
        cari = st.text_input("Cari ikon", key=f"{kunci}_cari", placeholder="Ketik: kopi, motor, listrik, gaji…", label_visibility="collapsed").strip().lower()
        ada = [n for n, (l, g, _) in GLIF.items() if not cari or cari in l.lower() or cari in g.lower() or cari in n]
        if not ada:
            st.caption("Tidak ada ikon yang cocok.")
        grup = {}
        for n in ada:
            grup.setdefault(GLIF[n][1], []).append(n)
        with st.container(key=f"{kunci}_kisi"):
            for g, isi in grup.items():
                st.caption(g)
                for i in range(0, len(isi), KOLOM):
                    kol = st.columns(KOLOM)
                    for c, n in zip(kol, isi[i:i + KOLOM]):
                        c.button(" ", key=f"{kunci}_g_{n.replace('-', '_')}", help=GLIF[n][0], use_container_width=True, type="primary" if nilai == f"mdi:{n}" else "secondary",
                                 on_click=st.session_state.__setitem__, args=(sk, f"mdi:{n}"))
        st.markdown(f"<style>{_css(kunci, ada)}</style>", unsafe_allow_html=True)
        def _emoji():
            if st.session_state.get(f"{kunci}_em"):
                st.session_state[sk] = st.session_state[f"{kunci}_em"]
        st.selectbox("Atau pilih emoji", IKON_PILIHAN, index=None, format_func=lambda x: f"{x}  {IKON_NAMA.get(x, '')}", key=f"{kunci}_em",
                     placeholder="Ketik untuk mencari", on_change=_emoji)
    return st.session_state[sk]
