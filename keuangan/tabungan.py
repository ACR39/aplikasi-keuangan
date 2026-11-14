"""Target tabungan: setor, tarik, dan perkiraan kebutuhan per bulan."""
import streamlit as st

from keuangan.bantu import atur, batang, catat, e, selesai_simpan, versi
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, rp, sisa_hari


def terkumpul(g: dict) -> int:
    return sum(int(s["jumlah"]) for s in g.get("setoran", []))


def _perkiraan(g: dict) -> str:
    sisa = int(g["target"]) - terkumpul(g)
    if sisa <= 0:
        return "Target tercapai "
    h = sisa_hari(g.get("tenggat"))
    if h is None:
        return f"Kurang {rp(sisa)}"
    if h < 0:
        return f"Kurang {rp(sisa)} · tenggat sudah lewat {-h} hari"
    bulan = max(h / 30.4, 1)
    return f"Kurang {rp(sisa)} · sekitar {rp(sisa / bulan)} per bulan sampai {fmt_iso(g['tenggat'])}"


def halaman_tabungan():
    total_t = sum(int(g["target"]) for g in D["tabungan"])
    total_k = sum(terkumpul(g) for g in D["tabungan"])
    if D["tabungan"]:
        st.caption(f"Terkumpul **{rp(total_k)}** dari target gabungan **{rp(total_t)}**. "
                   "Setoran di sini hanya catatan target, tidak mengubah saldo dompet.")
    else:
        st.info("Belum ada target. Buat target tabungan pertama di bawah.")
    for g in D["tabungan"]:
        kum, tgt = terkumpul(g), int(g["target"])
        with st.container(key=f"kartu_g_tab_{g['id']}"):
            st.markdown(
                f'<div class="ag"><b style="font-size:1.05rem">{e(g["nama"])}</b><span>{rp(kum)} dari {rp(tgt)} · '
                f'<b>{min(kum / tgt * 100, 999) if tgt else 0:.0f}%</b></span></div>'
                f'{batang(kum, tgt, "bl" if kum < tgt else "")}<div class="sc-ket">{e(_perkiraan(g))}</div>'
                + (f'<div class="sc-ket">{e(g["catatan"])}</div>' if g.get("catatan") else ""), unsafe_allow_html=True)
            if hanya_lihat():
                continue
            with st.form(f"f_setor_{g['id']}_{versi()}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.6, 1])
                arah = c1.radio("Jenis", ["Setor", "Tarik"], horizontal=True, label_visibility="collapsed")
                jml = c2.number_input("Jumlah (Rp)", min_value=0, step=10000, value=0, label_visibility="collapsed")
                cat = c3.text_input("Catatan", placeholder="Catatan, opsional", label_visibility="collapsed")
                if c4.form_submit_button("Catat", type="primary"):
                    if jml <= 0:
                        st.error("Jumlah harus lebih dari nol.")
                    elif arah == "Tarik" and jml > kum:
                        st.error("Penarikan melebihi dana yang terkumpul.")
                    else:
                        g["setoran"].append({"id": baru_id(), "tgl": hari_ini().isoformat(),
                                             "jumlah": int(jml) if arah == "Setor" else -int(jml), "catatan": cat.strip()})
                        catat("tabungan", f"{arah} {rp(jml)} untuk {g['nama']}")
                        selesai_simpan(f"{arah} {rp(jml)} dicatat.")
            c = st.columns([1, 1, 1, 4])
            c[0].button("Ubah", key=f"kedit_tb_{g['id']}", on_click=atur, args=("edit_tab", g["id"]))
            c[1].button("Hapus", key=f"khapus_tb_{g['id']}", on_click=atur, args=("hapus_tab", g["id"]))
            if st.session_state.get("hapus_tab") == g["id"]:
                st.warning(f"Hapus target {g['nama']} beserta {len(g['setoran'])} catatan setorannya?")
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Ya, hapus", key=f"ya_tab_{g['id']}", type="primary"):
                    D["tabungan"] = [x for x in D["tabungan"] if x["id"] != g["id"]]
                    catat("tabungan", f"Hapus target {g['nama']}")
                    selesai_simpan("Target dihapus.", hapus_tab=None)
                b.button("Batal", key=f"batal_tab_{g['id']}", on_click=atur, args=("hapus_tab", None))
            if g["setoran"]:
                with st.expander(f"Riwayat setoran ({len(g['setoran'])})"):
                    for s in sorted(g["setoran"], key=lambda s: s["tgl"], reverse=True)[:30]:
                        st.markdown(f'<div class="perhatian">{fmt_iso(s["tgl"])} · '
                                    f'<b class="nm-{"masuk" if s["jumlah"] > 0 else "keluar"}">{"+" if s["jumlah"] > 0 else ""}{rp(s["jumlah"])}</b>'
                                    f'{" · " + e(s["catatan"]) if s.get("catatan") else ""}</div>', unsafe_allow_html=True)
    if hanya_lihat():
        return
    edit = next((x for x in D["tabungan"] if x["id"] == st.session_state.get("edit_tab")), None)
    with st.container(key="kartu_g_form_tab"):
        st.markdown(f"**{'Ubah target' if edit else 'Target baru'}**")
        with st.form(f"f_tab_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=not edit):
            c1, c2 = st.columns(2)
            nama = c1.text_input("Nama target", value=edit["nama"] if edit else "", placeholder="Contoh: Dana darurat, Liburan")
            target = c2.number_input("Target (Rp)", min_value=0, step=100000, value=int(edit["target"]) if edit else 0)
            c3, c4 = st.columns(2)
            pakai_tenggat = c3.checkbox("Pakai tenggat", value=bool(edit and edit.get("tenggat")))
            tenggat = c4.date_input("Tenggat", value=iso_ke_date(edit.get("tenggat")) if edit and edit.get("tenggat") else hari_ini(),
                                    min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            catatan = st.text_input("Catatan, opsional", value=edit.get("catatan", "") if edit else "")
            if st.form_submit_button("Simpan perubahan" if edit else "Buat target", type="primary"):
                if not nama.strip() or target <= 0:
                    st.error("Isi nama dan target.")
                else:
                    isi = {"nama": nama.strip(), "target": int(target), "catatan": catatan.strip(),
                           "tenggat": tenggat.isoformat() if pakai_tenggat else ""}
                    if edit:
                        edit.update(isi)
                    else:
                        D["tabungan"].append({"id": baru_id(), "setoran": [], **isi})
                    catat("tabungan", f"{'Ubah' if edit else 'Buat'} target {isi['nama']} {rp(isi['target'])}")
                    selesai_simpan("Target disimpan.", edit_tab=None)
        if edit and st.button("Batal ubah", key="batal_ubah_tab"):
            st.session_state.pop("edit_tab", None)
            st.rerun()
