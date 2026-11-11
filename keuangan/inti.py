"""Dasar bersama: gaya tampilan (CSS), konstanta, data kosong, format tanggal dan rupiah, serta objek D (data sesi)."""
import os
import uuid
from collections.abc import MutableMapping
from datetime import date, datetime, timedelta, timezone

import streamlit as st


CSS_GELAP = """
<style>
:root{color-scheme:dark}
[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#0f1722 !important}
[data-testid="stApp"]{color:#e5e7eb}
[data-testid="stHeader"]{background:transparent !important}
[data-testid="stSidebarCollapsedControl"] *,[data-testid="stExpandSidebarButton"] *{color:#e5e7eb !important}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,[data-testid="stMain"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] h4,
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] [data-testid="stCaptionContainer"] p,[data-testid="stMain"] [data-testid="stExpander"] summary p,
[data-testid="stMain"] [data-testid="stRadio"] label p,[data-testid="stMain"] [data-testid="stCheckbox"] label p,
[data-testid="stMain"] [data-testid="stToggle"] label p,[data-testid="stMain"] [data-testid="stTab"] p{color:#e5e7eb !important}
[data-testid="stMain"] [data-testid="stCaptionContainer"],[data-testid="stMain"] [data-testid="stCaptionContainer"] p{color:#94a3b8 !important}
.eyebrow{color:#5ccf9c !important}
.judul-hal{color:#f1f5f9 !important}
.kepala{background:#172131 !important;border-color:#2a3547 !important;border-left-color:#34a874 !important;box-shadow:none !important;color:#e5e7eb !important}
.kepala .desk,.sc-ket,.sc-lab{color:#94a3b8 !important}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"],
.statcard,[data-testid="stForm"],[data-testid="stExpander"],[data-testid="stMetric"],[class*="st-key-item_"]{
  background:#172131 !important;border-color:#2a3547 !important;box-shadow:none !important;color:#e5e7eb !important}
[data-testid="stExpander"] details{border-color:#2a3547 !important}
.dh .dt{color:#f1f5f9 !important}.dh .dn{background:#1b2d27 !important;color:#5ccf9c !important}.dd{color:#94a3b8 !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stHorizontalBlock"]{background:#1c2738 !important;border-color:#2a3547 !important;border-left-color:#34a874 !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stForm"] [data-testid="stHorizontalBlock"]{background:transparent !important;border:0 !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stForm"]{background:#1a2333 !important;border:1px dashed #3a4760 !important}
[class*="st-key-ub_"] button{border-color:#34a874 !important;color:#5ccf9c !important}
[class*="st-key-hp_"] button{border-color:#7a3a36 !important;color:#fca5a5 !important}
[class*="st-key-item_b_"] [data-testid="stHorizontalBlock"]{border-top-color:#2a3547 !important}
.dgrup{color:#5ccf9c !important;border-bottom-color:#2a3547 !important}.dgrup span{color:#94a3b8 !important}
.dpt{background:#1c2738 !important;border-color:#2a3547 !important;border-top-color:#34a874 !important}
.dpt.kosong{background:#172131 !important;border-top-color:#3a4760 !important}.dpt.lain{background:#2a2416 !important;border-top-color:#c79330 !important}
.dpt .dh1,.dpt .db{color:#f1f5f9 !important}.dpt .dh1 span{background:#1b2d27 !important;color:#5ccf9c !important}
.dpt .db{border-bottom-color:#2a3547 !important}.dpt .db b{color:#5ccf9c !important}.dpt .db small,.dpt .dk{color:#94a3b8 !important}
.sc-judul,.sc-val,.itm .jd,.itm .qt b,.perhatian,.brg{color:#f1f5f9 !important}
.sc-val.m,.itm .qt b.merah{color:#f87171 !important}
.sc-val.g{color:#4ade80 !important}
.sc-stat{border-left-color:#2a3547 !important}
.sub,.itm .mt,.itm .cat,.itm .qt span{color:#9aa7b8 !important}
.perhatian{border-bottom-color:#2a3547 !important}
.itm a,.perhatian a,.akt a{color:#93c5fd !important}
.garis{border-top-color:#2a3547 !important}
.itm .ic{background:#1f3a2f !important;color:#5ccf9c !important}
.tag{background:#1f3a2f;color:#5ccf9c}
.tag-m{background:#3b3010;color:#fcd34d}
.bidang{background:#1b2d27 !important;color:#5ccf9c !important;border-left-color:#34a874 !important}
.st-ok{color:#4ade80 !important}.st-warn{color:#fbbf24 !important}.st-bad{color:#f87171 !important}
.lc-m{background:#3b3010 !important;color:#fcd34d !important}
.lc-r{background:#431a17 !important;color:#fca5a5 !important}
.lc-b{background:#14284a !important;color:#93c5fd !important}
.lc-h{background:#12301f !important;color:#86efac !important}
.akt{background:#172131 !important;border-color:#2a3547 !important}
.akt .ah{color:#f1f5f9 !important}.akt .ar{color:#cbd5e1 !important}.akt .am{color:#94a3b8 !important}
.pohon details{background:#172131 !important;border-color:#2a3547 !important}
.pohon details.pl{background:transparent !important;border-left-color:#2f5d4a !important}
.pohon summary{color:#f1f5f9 !important}
.pohon .pc{background:#1f3a2f !important;color:#5ccf9c !important}
.pohon .pi{border-bottom-color:#2a3547 !important}
.pohon .pn,.pohon .pj{color:#e5e7eb !important}
.pohon .pk{color:#94a3b8 !important}
[class*="st-key-kedit_"] button,[class*="st-key-khapus_"] button,[class*="st-key-kpakai_"] button,[class*="st-key-ksalin_"] button{background:#1e293b !important}
[class*="st-key-ksalin_"] button{border-color:#94a3b8 !important;color:#cbd5e1 !important}
[class*="st-key-kedit_"] button{border-color:#34a874 !important;color:#5ccf9c !important}
[class*="st-key-khapus_"] button{border-color:#f87171 !important;color:#f87171 !important}
[class*="st-key-kpakai_"] button{border-color:#60a5fa !important;color:#93c5fd !important}
[data-testid="stMain"] button[kind="secondary"],[data-testid="stMain"] button[kind="secondaryFormSubmit"],[data-testid="stMain"] [data-testid="stDownloadButton"] button{
  background:#1e293b;border-color:#334155;color:#e5e7eb}
[data-testid="stMain"] button[kind="secondary"] p,[data-testid="stMain"] button[kind="secondaryFormSubmit"] p,[data-testid="stMain"] [data-testid="stDownloadButton"] button p{color:inherit !important}
[data-testid="stMain"] button[kind="primary"] p,[data-testid="stMain"] button[kind="primaryFormSubmit"] p{color:#fff !important}
[data-testid="stSelectbox"] [role="group"],[data-testid="stMultiSelect"] [role="group"],[data-testid="stDateInput"] [role="group"],
[data-testid="stDateInputField"],[data-testid="stNumberInputContainer"],[data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],
[data-testid="stFileUploaderDropzone"],[data-testid="stCameraInput"]{background:#0f1722 !important;border-color:#334155 !important}
[data-testid="stSelectbox"] [role="group"] *,[data-testid="stMultiSelect"] [role="group"] *,[data-testid="stDateInput"] [role="group"] *,
[data-testid="stNumberInputContainer"] *,[data-testid="stTextInputRootElement"] input,[data-testid="stTextAreaRootElement"] textarea,
[data-testid="stTextInputField"],[data-testid="stFileUploaderDropzone"] *{color:#e5e7eb !important;-webkit-text-fill-color:#e5e7eb !important}
[data-testid="stSelectbox"] [role="group"] svg,[data-testid="stMultiSelect"] [role="group"] svg,[data-testid="stDateInput"] svg,
[data-testid="stTextInputIcon"] svg,[data-testid="stFileUploaderDropzone"] svg{fill:#94a3b8 !important;color:#94a3b8 !important}
input::placeholder,textarea::placeholder{color:#94a3b8 !important;-webkit-text-fill-color:#94a3b8 !important;opacity:1 !important}
[data-testid="stNumberInputContainer"] button{background:#1e293b !important}
/* daftar pilihan (dropdown) tampil di luar halaman utama, lewat portal */
[data-testid="stSelectboxVirtualDropdown"],[data-testid="stSelectboxVirtualDropdown"] [role="listbox"],
[data-testid="portal"] [role="listbox"],[data-testid="portal"] ul{background:#172131 !important}
[role="listbox"] [role="option"],[role="listbox"] [role="option"] *,[data-testid="portal"] li,[data-testid="portal"] li *{color:#e5e7eb !important;-webkit-text-fill-color:#e5e7eb !important}
[role="listbox"] [role="option"]:hover,[role="listbox"] [role="option"][aria-selected="true"],[role="listbox"] [role="option"][data-focused="true"]{background:#24324a !important}
[data-testid="stMultiSelect"] [data-testid="stTag"],[data-testid="stMultiSelect"] [role="row"] > div{background:#24324a !important}
[data-testid="stButtonGroup"] button[aria-checked="false"]{background:#0f1722 !important;color:#e5e7eb !important;border-color:#334155 !important}
[data-testid="stButtonGroup"] button p{color:inherit !important}
[data-testid="stAlertContainer"]{background:rgba(148,163,184,.14) !important;color:#e5e7eb !important}
[data-testid="stAlertContainer"] p,[data-testid="stAlertContainer"] li{color:#e5e7eb !important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{border-bottom-color:#2a3547}
[data-testid="stArrowVegaLiteChart"],[data-testid="stVegaLiteChart"]{filter:invert(1) hue-rotate(180deg)}
[data-testid="stImage"] img{border-radius:8px}
[data-testid="stProgress"] p{color:#e5e7eb !important}
</style>
"""


CSS_TERANG = """
<style>
.block-container{padding:1rem 2rem 4rem;max-width:1600px}
[data-testid="stToolbarActions"],[data-testid="stMainMenu"],[data-testid="stAppDeployButton"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none !important}
[data-testid="stHeader"]{background:transparent}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.09em;color:#2b7a57}
.judul-hal{font-size:1.6rem;font-weight:700;color:#111827;margin:.1rem 0 .15rem;letter-spacing:-.01em}
.kepala{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;
  background:#fff;border:1px solid #e5e7eb;border-left:4px solid #2b7a57;border-radius:12px;
  padding:1rem 1.3rem;margin:0 0 1.4rem;box-shadow:0 1px 3px rgba(15,23,42,.05)}
.kepala .desk{font-size:.86rem;color:#64748b;max-width:62ch}
.pengguna{display:flex;align-items:center;gap:.6rem;background:#f1f5f9;border-radius:999px;padding:.35rem .9rem .35rem .4rem}
.pengguna .av{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#34a874,#1f6b49);
  color:#fff;font-weight:700;font-size:.85rem;display:flex;align-items:center;justify-content:center}
.pengguna .nm{font-size:.84rem;font-weight:600;color:#0f172a;line-height:1.15}
.pengguna .pr{font-size:.7rem;color:#64748b;text-transform:capitalize}
.pengguna.sb{background:transparent;margin:.9rem 0 .5rem;border-radius:0;border-top:1px solid rgba(255,255,255,.08);padding:.9rem .2rem 0}
[data-testid="stSidebar"] .pengguna.sb .nm{color:#fff;font-size:.88rem}
[data-testid="stSidebar"] .pengguna.sb .pr{color:#94a3b8}
[data-testid="stSidebar"]{background:#0b1220}
[data-testid="stSidebarHeader"]{position:absolute;top:.5rem;right:.5rem;width:auto;height:auto;padding:0;margin:0;z-index:5}
[data-testid="stSidebarUserContent"]{padding-top:1.1rem}
[data-testid="stSidebar"] *{color:#e5e7eb}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#94a3b8}
.brand{display:flex;align-items:center;gap:.7rem;padding:.3rem .2rem 1.1rem;border-bottom:1px solid rgba(255,255,255,.08);margin-bottom:.4rem}
.brand .b1{font-weight:700;font-size:1.05rem;color:#fff;line-height:1.2}
.brand .b2{font-size:.76rem;color:#94a3b8;margin-top:.1rem}
.sp{height:1.2rem}
[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child){display:none}
.grup{font-size:.66rem;font-weight:700;letter-spacing:.12em;color:#64748b;margin:1rem 0 .35rem .3rem}
[data-testid="stSidebar"] [data-testid="stExpander"]{background:transparent;border:0;box-shadow:none;margin-bottom:.2rem}
[data-testid="stSidebar"] [data-testid="stExpander"] details{border:0}
[data-testid="stSidebar"] [data-testid="stExpander"] summary{font-weight:600;font-size:.92rem;padding:.55rem .5rem;border-radius:8px;background:transparent !important;color:#e5e7eb !important}
[data-testid="stSidebar"] [data-testid="stExpander"] details[open] > summary,[data-testid="stSidebar"] [data-testid="stExpander"] summary:focus,[data-testid="stSidebar"] [data-testid="stExpander"] summary:active{background:transparent !important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover{background:rgba(255,255,255,.06) !important}
[data-testid="stSidebar"] [data-testid="stExpanderDetails"]{padding:.1rem 0 .3rem .5rem;border-left:1px solid rgba(255,255,255,.1);margin-left:1rem}
[class*="st-key-nav_"] button{justify-content:flex-start !important;text-align:left !important;border:0 !important;
  border-radius:8px;min-height:2.4rem;background:transparent !important;color:#cbd5e1 !important;
  font-weight:500;font-size:.9rem;box-shadow:inset 3px 0 0 transparent}
[class*="st-key-nav_"] button:hover{background:rgba(255,255,255,.06) !important;color:#fff !important}
[class*="st-key-nav_"] button[kind="primary"]{background:rgba(52,168,116,.18) !important;color:#fff !important;
  font-weight:600;box-shadow:inset 3px 0 0 #34d399}
[class*="st-key-nav_"] button > div,[class*="st-key-nav_"] button [data-testid="stMarkdownContainer"],
[class*="st-key-nav_"] button p{text-align:left !important;justify-content:flex-start !important}
[class*="st-key-nav_muat"] button{border:1px solid rgba(255,255,255,.12) !important;justify-content:center !important}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"]{background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  padding:1.1rem 1.2rem;box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:.9rem}
[data-testid="stExpander"]{background:#fff;border-radius:14px !important;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.statcard{display:flex;flex-wrap:wrap;background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin:.2rem 0 .6rem;overflow:hidden}
.sc-kiri{flex:2 1 280px;padding:1rem 1.2rem}
.sc-judul{font-size:1.35rem;font-weight:800;color:#111827;margin-top:.5rem}
.sc-ket{font-size:.85rem;color:#6b7280;margin-top:.15rem}
.tag{display:inline-block;background:#e8f3ec;color:#1f6b49;font-size:.72rem;font-weight:700;border-radius:999px;
  padding:.15rem .65rem;margin-right:.4rem}
.tag-m{background:#fff4d6;color:#8a5a00}
.sc-stat{flex:1 1 90px;border-left:1px solid #eef0f4;text-align:center;padding:1rem .4rem}
.sc-lab{font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#6b7280}
.sc-val{font-size:1.7rem;font-weight:800;color:#111827;margin-top:.2rem}
.sc-val.g{color:#166534}.sc-val.m{color:#b42318}
[data-testid="stMetric"]{border:1px solid #d9dee7;border-radius:8px;padding:.8rem 1rem;background:#fff}
[data-testid="stForm"]{border-radius:8px;border-color:#d9dee7;background:#fff}
[data-testid="InputInstructions"]{display:none}
.thead-s{background:#256b4a;color:#fff;font-weight:650;font-size:.7rem;letter-spacing:.03em;text-transform:uppercase;text-align:center;padding:.3rem .25rem;border-radius:4px;height:3rem;min-height:3rem;box-sizing:border-box;line-height:1.15;display:flex;align-items:center;justify-content:center}
[class*="st-key-bredit_"] button,[class*="st-key-brhapus_"] button{min-height:2rem;padding:.1rem .5rem;border:0 !important;color:#fff !important}
[class*="st-key-bredit_"] button{background:#2f5d9e !important}
[class*="st-key-brhapus_"] button{background:#b42318 !important}
.garis{border-top:1px solid #e3e7ee;margin:.3rem 0}
.brg{font-weight:650}
.sub{font-size:.85rem;color:#5b6573}
.bidang{font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:#256b4a;background:#e8f3ec;border-left:3px solid #256b4a;padding:.35rem .7rem;border-radius:4px;margin:.4rem 0 -.3rem}
.st-ok{color:#166534;font-weight:600}.st-warn{color:#8a5a00;font-weight:600}.st-bad{color:#b42318;font-weight:600}
.lencana{display:inline-block;font-size:.66rem;font-weight:700;border-radius:999px;padding:.05rem .5rem;margin-left:.4rem;vertical-align:middle}
.lc-m{background:#fff4d6;color:#8a5a00}.lc-r{background:#fde8e6;color:#b42318}.lc-b{background:#e6eefb;color:#2f5d9e}.lc-h{background:#e3f3ea;color:#166534}
.akt{border:1px solid #e3e7ee;border-radius:10px;padding:.55rem .8rem;margin:.45rem 0;background:#fff}
.akt .ah{font-weight:650;line-height:1.5}.akt .ar{font-size:.86rem;color:#3d4655;margin-top:.15rem;line-height:1.5;word-break:break-word}.akt .am{font-size:.76rem;color:#6b7280;margin-top:.25rem}
.pohon details{border:1px solid #e3e7ee;border-radius:10px;margin:.4rem 0;background:#fff}
.pohon details.pl{border:0;border-left:2px solid #cfe3d6;border-radius:0;margin:.3rem 0 .3rem .3rem;background:transparent}
.pohon summary{cursor:pointer;padding:.55rem .7rem;font-weight:650;list-style:none;display:flex;align-items:center;gap:.5rem}
.pohon summary::-webkit-details-marker{display:none}
.pohon summary::before{content:"▸";color:#256b4a;flex:0 0 auto;transition:transform .15s}
.pohon details[open] > summary::before{transform:rotate(90deg)}
.pohon details.pl > summary{font-weight:600;padding:.4rem .5rem}
.pohon .pc{margin-left:auto;font-weight:600;font-size:.72rem;background:#e8f3ec;color:#256b4a;border-radius:999px;padding:.05rem .55rem;white-space:nowrap}
.pohon .pb{padding:0 .7rem .5rem 1.1rem}
.pohon .pi{display:flex;align-items:center;gap:.4rem;padding:.3rem 0;border-bottom:1px dashed #e8ebf0;font-size:.92rem;flex-wrap:wrap}
.pohon .pn{font-weight:550;word-break:break-word}
.pohon .pj{margin-left:auto;font-weight:700}
.pohon .pk{color:#6b7280;font-size:.82rem;padding:.3rem 0}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"],.statcard,.kepala,[data-testid="stForm"]{color:#111827 !important}
.kepala .desk,.sc-ket,.sc-lab,.eyebrow{color:#475569 !important}
.perhatian{padding:.45rem 0;border-bottom:1px solid #eef0f4;font-size:.92rem;color:#1f2937}
.perhatian:last-child{border-bottom:0}
.itm a,.perhatian a,.akt a{color:#2f5d9e;text-decoration:underline;word-break:break-all}
@media (max-width:768px){
  .block-container{padding:2.7rem 1rem 4rem}
  [data-testid="stHeader"]{height:2.4rem;min-height:0}
  [data-testid="stSidebarCollapsedControl"]{top:.35rem;left:.5rem}
  .kepala{padding:.9rem 1rem}
  .judul-hal{font-size:1.35rem}
}
/* Di HP tabel tidak ditumpuk ke bawah, tapi dilebarkan dan bisa digeser ke samping (hanya di kartu yang boleh digeser) */
@media (max-width:640px){
  .st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]{overflow-x:auto;-webkit-overflow-scrolling:touch}
  :is(.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]) [data-testid="stHorizontalBlock"]:has(.brg),:is(.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]) [data-testid="stHorizontalBlock"]:has(.thead-s){flex-wrap:nowrap !important;min-width:780px}
  :is(.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]) [data-testid="stHorizontalBlock"]:has(.brg) > [data-testid="stColumn"],:is(.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]) [data-testid="stHorizontalBlock"]:has(.thead-s) > [data-testid="stColumn"]{min-width:0 !important;width:auto !important}
  :is(.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]) [data-testid="stHorizontalBlock"]:has(.brg) [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;min-width:0 !important}
  :is(.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]) [data-testid="stHorizontalBlock"]:has(.brg) [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{min-width:0 !important;width:auto !important}
  .st-key-kartu_tabel .garis,.st-key-kartu_barang .garis,.st-key-kartu_g_rencana .garis,[class*="st-key-kartu_tgl"] .garis{min-width:780px}
}
/* Tampilan kartu barang */
[class*="st-key-item_"]{background:#fff;border:1px solid #e3e7ee;border-radius:14px;padding:.8rem 1rem;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:-.35rem;color:#111827 !important;gap:.45rem !important}
[class*="st-key-item_"] [data-testid="stMarkdown"],[class*="st-key-item_"] [data-testid="stMarkdownContainer"]{margin-bottom:0 !important}
/* Daftar pengaturan (tempat, lokasi, kategori, pemilik, label) */
.dh{display:flex;align-items:center;gap:.55rem;margin:.1rem 0 .15rem}
.dh .dt{font-size:1.08rem;font-weight:800;color:#111827;letter-spacing:-.01em}
.dh .dn{background:#e8f3ec;color:#256b4a;font-size:.72rem;font-weight:700;border-radius:999px;padding:.08rem .6rem}
.dd{color:#6b7280;font-size:.84rem;line-height:1.45;margin-bottom:.35rem}
[class*="st-key-kartu_g_daftar"]{gap:.4rem !important}
.dgrup{display:flex;align-items:center;justify-content:space-between;font-size:.74rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:#256b4a;margin:.8rem 0 .55rem;padding:0 .2rem .35rem;border-bottom:1px solid #dbe7df}
.dgrup span{font-weight:600;letter-spacing:0;text-transform:none;color:#6b7280;font-size:.76rem}
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]:first-child [data-testid="stMarkdown"],
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"],
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]:first-child p{margin:0 !important;padding:0 !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]:first-child .itm{padding:0}
[class*="st-key-kartu_g_daftar"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;align-items:center;gap:.5rem !important;
  background:#f7f9fb;border:1px solid #e6eaf0;border-left:3px solid #34a874;border-radius:12px;padding:.4rem .6rem .4rem .8rem;margin-bottom:.1rem}
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]{min-width:0 !important;flex:0 0 auto !important;width:auto !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]:first-child{flex:1 1 auto !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stColumn"]:first-child p{font-weight:600;overflow-wrap:anywhere}
[class*="st-key-kartu_g_daftar"] [data-testid="stForm"] [data-testid="stHorizontalBlock"]{background:transparent;border:0;padding:0;flex-wrap:wrap !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stForm"] [data-testid="stColumn"]{flex:1 1 140px !important;min-width:140px !important}
[class*="st-key-kartu_g_daftar"] [data-testid="stCaptionContainer"]{margin:.1rem 0 .35rem}
[class*="st-key-kartu_g_daftar"] .dd{margin-bottom:.5rem}
[class*="st-key-kartu_g_daftar"] button{min-height:2.05rem;padding:.15rem .7rem;border-radius:9px;font-size:.82rem;white-space:nowrap}
[class*="st-key-kartu_g_daftar"] button p{white-space:nowrap;font-size:.82rem}
[class*="st-key-ub_"] button{border:1px solid #256b4a;color:#256b4a}
[class*="st-key-hp_"] button{border:1px solid #e9b5b0;color:#b42318}
[class*="st-key-kartu_g_daftar"] [data-testid="stForm"]{border:1px dashed #cfd6e0;background:#fafbfc;border-radius:14px;margin-top:.5rem}
@media (max-width:640px){
  [class*="st-key-item_"]{padding:.7rem .85rem}
  .itm{gap:.7rem}
  .itm .ic{flex-basis:44px;width:44px;height:44px;font-size:1.1rem}
  .itm .jd{font-size:.98rem;line-height:1.25}
  .itm .mt,.itm .cat{font-size:.78rem;line-height:1.35}
  .itm .qt{min-width:40px}
  .itm .qt b{font-size:1.45rem}
}
.itm{display:flex;align-items:center;gap:.85rem}
.itm .ic{flex:0 0 52px;width:52px;height:52px;border-radius:50%;background:#e8f3ec;color:#256b4a;font-weight:800;
  font-size:1.25rem;display:flex;align-items:center;justify-content:center;overflow:hidden}
.itm .ic img{width:100%;height:100%;object-fit:cover}
.itm .isi{flex:1 1 auto;min-width:0}
.itm .jd{font-weight:700;font-size:1.02rem;color:#111827;word-break:break-word}
.itm .mt{font-size:.82rem;color:#5b6573;margin-top:.1rem;word-break:break-word}
.itm .cat{font-size:.82rem;color:#374151;margin-top:.15rem;word-break:break-word}
.itm .qt{flex:0 0 auto;text-align:right;min-width:48px}
.itm .qt b{display:block;font-size:1.7rem;font-weight:800;line-height:1.1;color:#111827}
.itm .qt b.merah{color:#b42318}
.itm .qt span{display:block;font-size:.72rem;color:#6b7280;white-space:nowrap}
.itm .qt .st-ok,.itm .qt .st-warn,.itm .qt .st-bad{font-size:.78rem}
.lencana{white-space:nowrap}
.itm.pj{flex-wrap:wrap}
.itm.pj .isi{flex:1 1 180px}
.itm.pj .qt{text-align:right}
@media (max-width:640px){
  .itm.pj .qt{flex:1 1 100%;text-align:left;padding-left:calc(44px + .7rem);display:flex;flex-wrap:wrap;gap:.1rem .5rem;align-items:baseline}
}
[class*="st-key-kedit_"] button,[class*="st-key-khapus_"] button,[class*="st-key-kpakai_"] button,[class*="st-key-ksalin_"] button{min-height:2rem;padding:.1rem .6rem;background:#fff !important;font-weight:600}
[class*="st-key-ksalin_"] button{border:1px solid #6b7280 !important;color:#374151 !important}
[class*="st-key-kpakai_"] button{border:1px solid #2f5d9e !important;color:#2f5d9e !important}
[class*="st-key-kedit_"] button{border:1px solid #256b4a !important;color:#256b4a !important}
[class*="st-key-khapus_"] button{border:1px solid #b42318 !important;color:#b42318 !important}
.st-key-baris_cari [data-testid="stHorizontalBlock"],[class*="st-key-item_"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;align-items:center}
.st-key-baris_cari [data-testid="stColumn"]:first-child{min-width:0 !important;flex:1 1 auto !important;width:auto !important}
.st-key-baris_cari [data-testid="stColumn"]:last-child,[class*="st-key-item_"] [data-testid="stColumn"]{min-width:0 !important;flex:0 0 auto !important;width:auto !important}
.st-key-baris_cari button,[class*="st-key-item_"] button{white-space:nowrap}
.st-key-baris_cari button p,[class*="st-key-item_"] button p{white-space:nowrap}
[class*="st-key-item_b_"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;gap:.6rem !important;align-items:flex-end;margin-top:.55rem;padding-top:.65rem;border-top:1px dashed #dfe5ec}
[class*="st-key-item_b_"] [data-testid="stColumn"]{flex:1 1 150px !important;width:auto !important;min-width:130px !important}
[class*="st-key-item_b_"] [data-testid="stColumn"]:first-child{flex:0 1 150px !important}
[class*="st-key-kpakai_bl_"] button{background:#256b4a !important;border-color:#256b4a !important;color:#fff !important;font-weight:600}
[class*="st-key-kpakai_bl_"] button p{color:#fff !important}
/* Denah petak */
.denah{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.7rem;margin:.4rem 0}
.dpt{background:#f7f9fb;border:1px solid #e3e7ee;border-top:3px solid #34a874;border-radius:12px;padding:.6rem .75rem;min-height:92px}
.dpt.kosong{border-top-color:#cfd6e0;background:#fbfcfd}.dpt.lain{border-top-color:#e0a63a;background:#fffaf0}
.dpt .dh1{display:flex;justify-content:space-between;align-items:center;font-weight:800;font-size:.9rem;color:#111827;margin-bottom:.3rem}
.dpt .dh1 span{background:#e8f3ec;color:#256b4a;border-radius:999px;font-size:.7rem;font-weight:700;padding:.05rem .5rem}
.dpt .db{display:flex;justify-content:space-between;gap:.5rem;font-size:.82rem;padding:.2rem 0;border-bottom:1px solid #eef1f5;color:#1f2937}
.dpt .db:last-child{border-bottom:0}.dpt .db b{color:#256b4a;font-weight:700}.dpt .db small{color:#6b7280}
.dpt .dk{font-size:.78rem;color:#9aa3b2}
</style>
"""


# Tambahan khusus keuangan (nominal berwarna, batang anggaran, baris transaksi).
CSS_TAMBAH_TERANG = """
<style>
.rt{display:flex;align-items:center;gap:.85rem}
.rt .ic{flex:0 0 44px;width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.25rem;font-weight:800}
.rt .ic.masuk{background:#e3f3ea;color:#166534}.rt .ic.keluar{background:#fde8e6;color:#b42318}.rt .ic.transfer{background:#e6eefb;color:#2f5d9e}
.rt .isi{flex:1 1 auto;min-width:0}
.rt .jd{font-weight:700;color:#111827;word-break:break-word}
.rt .mt{font-size:.8rem;color:#5b6573;margin-top:.1rem;word-break:break-word}
.rt .nom{flex:0 0 auto;text-align:right;font-weight:800;font-size:1.05rem;white-space:nowrap}
.nom.masuk,.nm-masuk{color:#166534}.nom.keluar,.nm-keluar{color:#b42318}.nom.transfer,.nm-transfer{color:#2f5d9e}
.rt .ic.kat{color:#fff;font-size:1.2rem}
.kc{display:inline-flex;width:1.7rem;height:1.7rem;border-radius:50%;align-items:center;justify-content:center;font-size:.95rem;margin-right:.5rem;vertical-align:middle;color:#fff}
.sub-rinci{margin:.25rem 0 .3rem 2.2rem;font-size:.82rem;color:#475569}
.sub-rinci div{display:flex;justify-content:space-between;gap:.6rem;padding:.12rem 0;border-bottom:1px dashed #e8ebf0}
details.rinci > summary{cursor:pointer;list-style:none}details.rinci > summary::-webkit-details-marker{display:none}
.bar{height:10px;background:#e8ecf1;border-radius:999px;overflow:hidden;margin:.35rem 0 .2rem}
.bar > i{display:block;height:100%;background:#34a874;border-radius:999px}
.bar.w > i{background:#e0a63a}.bar.b > i{background:#d64545}
.bar.bl > i{background:#3b82c4}
.top-h{font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#6b7280;margin:.2rem 0 .5rem}
.top-r{display:flex;align-items:center;gap:.65rem;padding:.5rem 0;border-bottom:1px solid #eef0f4}.top-r:last-child{border-bottom:0}
.top-r .no{flex:0 0 26px;height:26px;border-radius:50%;background:#eef2f6;color:#475467;font-size:.8rem;font-weight:800;display:flex;align-items:center;justify-content:center}
.top-r:nth-child(-n+3) .no{background:#e3f3ea;color:#166534}
.top-r .tm{flex:1 1 auto;min-width:0}
.top-r .tn{font-weight:700;font-size:.93rem;color:#111827;line-height:1.25;word-break:break-word}
.top-r .ts{font-size:.76rem;color:#6b7280;margin-top:.05rem}
.top-r .bar{height:6px;margin:.3rem 0 0}
.top-r .tj{flex:0 0 auto;font-weight:700;font-size:.9rem;color:#111827;white-space:nowrap;text-align:right}
.ag{display:flex;justify-content:space-between;gap:.6rem;flex-wrap:wrap;font-size:.84rem;color:#475569}
.ag b{color:#111827}
.dompet-k{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.7rem;margin:.3rem 0 .8rem}
.dk1{background:#fff;border:1px solid #e3e7ee;border-top:3px solid #34a874;border-radius:12px;padding:.7rem .9rem;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.dk1 .n{font-size:.8rem;color:#6b7280;font-weight:600}.dk1 .s{font-size:1.2rem;font-weight:800;color:#111827;margin-top:.15rem}
.dk1 .s.neg{color:#b42318}
.dk2{background:#fff;border:1px solid #e3e7ee;border-radius:14px;padding:.8rem .95rem;box-shadow:0 1px 3px rgba(16,24,40,.06);position:relative;overflow:hidden}
.dk2:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--aksen,#34a874)}
.dk2 .h{display:flex;align-items:center;gap:.55rem}
.dk2 .i{flex:0 0 34px;height:34px;border-radius:10px;background:var(--aksen-lemah,#e3f3ea);display:flex;align-items:center;justify-content:center;font-size:1.1rem}
.dk2 .n{font-weight:700;font-size:.92rem;color:#111827;line-height:1.2}.dk2 .j{font-size:.72rem;color:#6b7280}
.dk2 .s{font-size:1.3rem;font-weight:800;color:#111827;margin-top:.55rem}.dk2 .s.neg{color:#b42318}
.dk2 .p{font-size:.72rem;color:#6b7280;margin-top:.1rem}
.kem{padding:.55rem 0;border-bottom:1px solid #eef0f4}.kem:last-of-type{border-bottom:0}
.kem .a{display:flex;align-items:center;gap:.5rem}.kem .a .kc{margin-right:0;flex:0 0 1.7rem}
.kem .nm{flex:1 1 auto;min-width:0;font-weight:700;font-size:.92rem;color:#111827;word-break:break-word}
.kem .pc{flex:0 0 auto;font-size:.75rem;font-weight:800;padding:.12rem .5rem;border-radius:999px;background:#e3f3ea;color:#166534}
.kem .pc.w{background:#fdf1d6;color:#8a5a00}.kem .pc.b{background:#fde8e6;color:#b42318}.kem .pc.bl{background:#e3eefb;color:#1f4f8f}
.kem .bar{height:8px;margin:.4rem 0 .25rem}
.kem .kt{font-size:.78rem;color:#6b7280}
.dk1 .j{font-size:.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em}
[class*="st-key-tx_"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;align-items:center}
[class*="st-key-tx_"] [data-testid="stColumn"]{min-width:0 !important;flex:0 0 auto !important;width:auto !important}
[class*="st-key-tx_"] [data-testid="stColumn"]:first-child{flex:1 1 auto !important}
[class*="st-key-tx_"]{background:#fff;border:1px solid #e3e7ee;border-radius:14px;padding:.7rem .9rem .85rem;margin-bottom:.35rem;box-shadow:0 1px 3px rgba(16,24,40,.06);gap:.3rem !important}
[class*="st-key-tx_"] button{white-space:nowrap}
[class*="st-key-tx_"] .rt{align-items:flex-start;padding-bottom:.9rem}
[class*="st-key-aksi_"]{margin-top:.2rem}
[class*="st-key-tx_"] .rt .mt{line-height:1.35}
[class*="st-key-tx_"] .rt .nom{font-size:1rem;padding-top:.1rem}
[class*="st-key-aksi_"] [data-testid="stHorizontalBlock"]{gap:.5rem !important;justify-content:flex-start}
[class*="st-key-aksi_"] [data-testid="stColumn"]:first-child,[class*="st-key-aksi_"] [data-testid="stColumn"]{flex:0 0 auto !important;width:auto !important}
[class*="st-key-bayar_"] button{background:#256b4a !important;border-color:#256b4a !important;color:#fff !important;font-weight:600}
[class*="st-key-bayar_"] button p{color:#fff !important}
[class*="st-key-lewat_"] button,[class*="st-key-batal_"] button{border:1px solid #6b7280 !important;color:#374151 !important;background:#fff !important}
</style>
"""

CSS_TAMBAH_GELAP = """
<style>
.rt .jd,.dk1 .s{color:#f1f5f9 !important}.rt .mt,.dk1 .n,.ag{color:#94a3b8 !important}.ag b{color:#f1f5f9 !important}
.rt .ic.masuk{background:#12301f !important;color:#86efac !important}.rt .ic.keluar{background:#431a17 !important;color:#fca5a5 !important}
.rt .ic.transfer{background:#14284a !important;color:#93c5fd !important}
.nom.masuk,.nm-masuk{color:#4ade80 !important}.nom.keluar,.nm-keluar{color:#f87171 !important}.nom.transfer,.nm-transfer{color:#93c5fd !important}
.top-h,.top-r .ts{color:#94a3b8 !important}.top-r{border-bottom-color:#2a3547 !important}
.top-r .no{background:#2a3547 !important;color:#cbd5e1 !important}.top-r:nth-child(-n+3) .no{background:#14532d !important;color:#bbf7d0 !important}
.top-r .tn,.top-r .tj{color:#f1f5f9 !important}
.bar{background:#2a3547 !important}.sub-rinci{color:#94a3b8 !important}.sub-rinci div{border-bottom-color:#2a3547 !important}
.dk1{background:#172131 !important;border-color:#2a3547 !important;border-top-color:#34a874 !important;box-shadow:none !important}
.dk1 .s.neg{color:#f87171 !important}
.dk2{background:#172131 !important;border-color:#2a3547 !important;box-shadow:none !important}.dk2 .n,.dk2 .s,.kem .nm{color:#f1f5f9 !important}
.dk2 .s.neg{color:#f87171 !important}.dk2 .j,.dk2 .p,.kem .kt{color:#94a3b8 !important}.dk2 .i{background:#243246 !important}
.kem{border-bottom-color:#2a3547 !important}.kem .pc{background:#14532d !important;color:#bbf7d0 !important}
.kem .pc.w{background:#5a3d00 !important;color:#fde68a !important}.kem .pc.b{background:#5c1a14 !important;color:#fecaca !important}.kem .pc.bl{background:#17365f !important;color:#bfdbfe !important}
[class*="st-key-tx_"]{background:#172131 !important;border-color:#2a3547 !important;box-shadow:none !important}
[class*="st-key-lewat_"] button,[class*="st-key-batal_"] button{background:#1e293b !important;color:#cbd5e1 !important;border-color:#94a3b8 !important}
</style>
"""


TANPA_KAT = "Tanpa kategori"
FILE_LOKAL = os.environ.get("KEUANGAN_DATA_FILE", "data_lokal.json")
TGL_MIN, TGL_MAX = date(2000, 1, 1), date(2100, 12, 31)
MAKS_AKTIVITAS = 1500
HARI_SAMPAH = 30
WIB = timezone(timedelta(hours=7))
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]
JENIS = {"masuk": "Pemasukan", "keluar": "Pengeluaran", "transfer": "Transfer"}
TOKO_IKON = {"Minimarket": "🏪", "Supermarket": "🛒", "Pasar": "🧺", "Warung": "🏠", "Toko online": "📦", "Restoran / kafe": "🍽️",
             "SPBU": "⛽", "Apotek": "💊", "Lainnya": "📍"}
JENIS_DOMPET = ["Tunai", "Rekening bank", "Dompet digital", "Kartu kredit", "Investasi", "Lainnya"]


def sekarang() -> datetime:
    return datetime.now(WIB)


def hari_ini() -> date:
    return sekarang().date()


def fmt_iso(s: str) -> str:
    try:
        return date.fromisoformat(s).strftime("%d/%m/%Y")
    except Exception:
        return s or ""


def fmt_waktu(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s or ""


def iso_ke_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def sisa_hari(s):
    """Selisih hari dari hari ini ke tanggal s (negatif = sudah lewat), None kalau kosong."""
    d = iso_ke_date(s)
    return (d - hari_ini()).days if d else None


def rp(n) -> str:
    n = int(round(n or 0))
    teks = "Rp " + f"{abs(n):,}".replace(",", ".")
    return "-" + teks if n < 0 else teks


def nama_bulan(ym: str) -> str:
    """'2026-03' -> 'Maret 2026'."""
    try:
        t, b = ym.split("-")
        return f"{BULAN[int(b) - 1]} {t}"
    except Exception:
        return ym


def baru_id() -> str:
    return uuid.uuid4().hex[:8]


SEP = " › "
IKON_PILIHAN = ["🍽️", "🛒", "🛍️", "🏠", "💡", "🚌", "🚗", "🏥", "🎬", "🎓", "💻", "📱", "🎁", "🏦", "🤝", "📦", "💼", "🪙", "📈", "💸",
                "🧾", "🔧", "👕", "🧴", "🍼", "🐾", "✈️", "☕", "⚽", "📚", "🔑", "❤️", "🏷️"]
PALET = ["#e8502a", "#f2a43a", "#f5c542", "#7ed348", "#34a874", "#4dbba3", "#6ebcf0", "#3b82c4", "#5b6cf0", "#8a2be2",
         "#d97aa0", "#e8527a", "#e05a5a", "#7a8c9b", "#9aa0a6"]

# (id, nama, jenis, ikon, warna, [sub kategori])
KATEGORI_SEED = [
    ("k_makan", "Makan dan minum", "keluar", "🍽️", "#e8502a", ["Belanja bahan makanan", "Restoran dan kafe", "Jajan dan kopi"]),
    ("k_belanja", "Belanja", "keluar", "🛍️", "#6ebcf0", ["Pakaian", "Elektronik", "Kebutuhan rumah", "Perawatan diri"]),
    ("k_rumah", "Rumah", "keluar", "🏠", "#f2a43a", ["Sewa atau cicilan", "Perbaikan", "Perabot", "Asuransi rumah"]),
    ("k_tagihan", "Tagihan dan utilitas", "keluar", "💡", "#f5c542", ["Listrik", "Air", "Internet", "Gas"]),
    ("k_transport", "Transportasi", "keluar", "🚌", "#7a8c9b", ["Transportasi umum", "Ojek dan taksi online", "Parkir dan tol"]),
    ("k_kendaraan", "Kendaraan", "keluar", "🚗", "#8a2be2", ["Bensin", "Servis", "Pajak dan STNK", "Asuransi kendaraan"]),
    ("k_kesehatan", "Kesehatan", "keluar", "🏥", "#e05a5a", ["Dokter dan obat", "Asuransi kesehatan"]),
    ("k_hiburan", "Hiburan", "keluar", "🎬", "#7ed348", ["Langganan", "Wisata", "Hobi"]),
    ("k_pendidikan", "Pendidikan", "keluar", "🎓", "#3b82c4", ["Biaya sekolah", "Kursus dan buku"]),
    ("k_komunikasi", "Komunikasi dan gawai", "keluar", "💻", "#5b6cf0", ["Pulsa dan paket data", "Perangkat"]),
    ("k_sosial", "Sosial dan donasi", "keluar", "🎁", "#d97aa0", []),
    ("k_keuangan", "Biaya keuangan", "keluar", "🏦", "#4dbba3", ["Biaya admin", "Pajak"]),
    ("k_bayar_utang", "Bayar utang / pinjamkan", "keluar", "🤝", "#f0884a", []),
    ("k_lain_k", "Lainnya", "keluar", "📦", "#9aa0a6", []),
    ("k_gaji", "Gaji", "masuk", "💼", "#34a874", ["Gaji pokok", "Bonus dan tunjangan"]),
    ("k_usaha", "Usaha dan sampingan", "masuk", "🪙", "#f0c040", []),
    ("k_investasi_m", "Hasil investasi", "masuk", "📈", "#e8527a", ["Bunga", "Dividen"]),
    ("k_hadiah", "Hadiah", "masuk", "🎁", "#d97aa0", []),
    ("k_terima_utang", "Terima piutang / pinjaman", "masuk", "🤝", "#f0884a", []),
    ("k_lain_m", "Lainnya", "masuk", "📦", "#9aa0a6", []),
]


def _slug(t: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in t.lower())


def kategori_awal() -> list:
    """Kategori bawaan: kategori utama beserta sub kategorinya (sub memakai ikon dan warna induknya)."""
    hasil = []
    for i, n, j, ik, w, anak in KATEGORI_SEED:
        hasil.append({"id": i, "nama": n, "jenis": j, "induk": "", "ikon": ik, "warna": w})
        hasil += [{"id": f"{i}__{_slug(x)}", "nama": x, "jenis": j, "induk": i, "ikon": ik, "warna": w} for x in anak]
    return hasil


_SEED_IKON = {i: (ik, w) for i, _, _, ik, w, _ in KATEGORI_SEED}


def lengkapi_kategori(daftar: list) -> list:
    """Data dari versi lama (tanpa sub kategori, ikon, warna) dilengkapi tanpa mengubah id."""
    for n, k in enumerate(daftar):
        k.setdefault("induk", "")
        ik, w = _SEED_IKON.get(k["id"], ("🏷️", PALET[n % len(PALET)]))
        k.setdefault("ikon", ik)
        k.setdefault("warna", w)
    return daftar


def data_kosong() -> dict:
    return {
        "dompet": [{"id": "d_tunai", "nama": "Tunai", "jenis": "Tunai", "saldo_awal": 0, "arsip": False}],
        # [{"id","nama","jenis","saldo_awal","arsip"}]  saldo sekarang dihitung dari saldo awal + transaksi
        "kategori": kategori_awal(),  # [{"id","nama","jenis"(masuk|keluar),"induk"(id kategori utama, kosong = utama),"ikon","warna"}]
        "transaksi": [],  # [{"id","jenis"(masuk|keluar|transfer),"tgl","jumlah","dompet","ke","biaya","kategori","catatan",
                          #   "barang","qty","harga_satuan","toko","lokasi","waktu"(HH:MM),"tagihan","utang","dibuat","oleh"}]
        "templat": [],    # templat transaksi: [{"id","nama","jenis","dompet","kategori","jumlah","catatan","barang","qty","harga_satuan","toko","lokasi"}]
        "belanja": [],    # daftar belanja: [{"id","nama","toko","dibuat","selesai","item":[],"riwayat":[]}]
        "toko": [],       # [{"id","nama","jenis","lokasi"}]  tempat beli / toko
        "barang": [],     # [{"id","nama","kategori"(id kategori atau sub kategori),"harga"(harga satuan terakhir),"satuan"}]
        "anggaran": [],   # [{"id","kategori","batas"}]  batas per bulan, berlaku tiap bulan
        "tagihan": [],    # [{"id","nama","jumlah","kategori","dompet","tiap","berikut","catatan","aktif"}]
        "tabungan": [],   # [{"id","nama","target","tenggat","catatan","setoran":[{"id","tgl","jumlah","catatan"}]}]
        "utang": [],      # [{"id","arah"("utang"|"piutang"),"orang","jumlah","tgl","tenggat","catatan","bayar":[{"id","tgl","jumlah"}]}]
        "aktivitas": [],  # [{"id","waktu","oleh","jenis","rincian"}]
        "sampah": [],     # [{"id","transaksi":{...},"dihapus"}]
        "pengaturan": {},  # {"beranda":[bagian yang disembunyikan]}
    }


def pasang_css():
    st.markdown(CSS_TERANG + CSS_TAMBAH_TERANG, unsafe_allow_html=True)


class _Data(MutableMapping):
    """Data aplikasi milik sesi yang sedang berjalan.

    Modul dipakai bersama oleh semua sesi, jadi data tidak boleh disimpan sebagai
    variabel modul. Objek ini selalu membaca st.session_state.data milik sesi yang aktif.
    """

    @property
    def data(self) -> dict:
        return st.session_state.data

    def __getitem__(self, k):
        return st.session_state.data[k]

    def __setitem__(self, k, v):
        st.session_state.data[k] = v

    def __delitem__(self, k):
        del st.session_state.data[k]

    def __iter__(self):
        return iter(st.session_state.data)

    def __len__(self):
        return len(st.session_state.data)

    def get(self, k, default=None):
        return st.session_state.data.get(k, default)

    def setdefault(self, k, default=None):
        return st.session_state.data.setdefault(k, default)


D = _Data()


def cfg_github():
    try:
        g = st.secrets["github"]
        return {"token": g["token"], "repo": g["repo"],
                "path": g.get("path", "data.json"), "branch": g.get("branch", "main")}
    except Exception:
        return None


def pengguna_nama() -> str:
    u = st.session_state.get("user")
    return u["username"] if u else "tamu"


def hanya_lihat() -> bool:
    u = st.session_state.get("user")
    return bool(u) and u.get("peran") == "lihat"


def adalah_admin() -> bool:
    """Tanpa login (uji coba) atau kata sandi tunggal dianggap admin."""
    u = st.session_state.get("user")
    return True if not u else u.get("peran") == "admin"
