"""Laporan: ringkasan bulanan, tren 12 bulan, dan arus per dompet."""
import pandas as pd
import streamlit as st

from keuangan.bantu import (
    info_diskon, daftar_bulan, transaksi_barang, transaksi_toko,    akar, ikon_kat,    deretan_stat, dompet_aktif, e, geser_bulan, kartu_stat, nama_dompet, nama_kat, per_kategori, pilih_bulan,
    ringkas_bulan, saldo_dompet, transaksi_bulan, ym_ini, batang,
)
from keuangan.inti import D, fmt_iso, nama_bulan, rp


def _tabel_kategori(ym: str, jenis: str):
    """Total per kategori utama (sub kategori dijumlahkan), dengan rincian sub yang bisa dibuka."""
    data = per_kategori(ym, jenis, gabung=True)
    mentah = per_kategori(ym, jenis)
    total = sum(data.values())
    if not data:
        st.caption("Tidak ada data.")
        return
    for k, v in data.items():
        rinci = {i: x for i, x in mentah.items() if akar(i) == k}
        kepala = (f'<div class="ag"><b>{ikon_kat(k)}{e(nama_kat(k))}</b><span>{rp(v)} · {v / total * 100:.0f}%</span></div>'
                  f'{batang(v, total, "bl" if jenis == "masuk" else "w")}')
        if len(rinci) > 1 or (rinci and k not in rinci):
            baris = "".join(f'<div><span>{e(nama_kat(i) if i != k else "Langsung di " + nama_kat(k))}</span><b>{rp(x)}</b></div>'
                            for i, x in sorted(rinci.items(), key=lambda y: -y[1]))
            st.markdown(f'<div class="perhatian"><details class="rinci"><summary>{kepala}</summary><div class="sub-rinci">{baris}</div></details></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="perhatian">{kepala}</div>', unsafe_allow_html=True)
    df = pd.DataFrame({"Kategori": [nama_kat(k) for k in data], "Jumlah": list(data.values())}).set_index("Kategori")
    st.bar_chart(df, color="#34a874" if jenis == "masuk" else "#d64545", horizontal=True)
    st.caption("Ketuk satu kategori untuk melihat rincian sub kategorinya.")


def _bulanan():
    ym = pilih_bulan("lp_bulan")
    masuk, keluar = ringkas_bulan(ym)
    tabung = (masuk - keluar) / masuk * 100 if masuk else 0
    deretan_stat(kartu_stat("Pemasukan", rp(masuk), kelas="g"), kartu_stat("Pengeluaran", rp(keluar), kelas="m"),
                 kartu_stat("Selisih", rp(masuk - keluar), kelas="g" if masuk >= keluar else "m"),
                 kartu_stat("Porsi ditabung", f"{tabung:.0f}%" if masuk else "-", "dari pemasukan"))
    c1, c2 = st.columns(2)
    with c1:
        with st.container(key="kartu_g_lp_keluar"):
            st.markdown("**Pengeluaran per kategori**")
            _tabel_kategori(ym, "keluar")
    with c2:
        with st.container(key="kartu_g_lp_masuk"):
            st.markdown("**Pemasukan per kategori**")
            _tabel_kategori(ym, "masuk")
    with st.container(key="kartu_g_lp_harian"):
        st.markdown("**Pengeluaran harian**")
        per_hari = {}
        for t in transaksi_bulan(ym):
            if t["jenis"] == "keluar":
                per_hari[t["tgl"][8:]] = per_hari.get(t["tgl"][8:], 0) + t["jumlah"]
        if per_hari:
            st.bar_chart(pd.DataFrame({"Hari": sorted(per_hari), "Pengeluaran": [per_hari[k] for k in sorted(per_hari)]}).set_index("Hari"),
                         color="#d64545")
            st.caption(f"Rata-rata {rp(sum(per_hari.values()) / len(per_hari))} per hari yang ada pengeluaran; "
                       f"terbesar {rp(max(per_hari.values()))} pada tanggal {max(per_hari, key=per_hari.get)}.")
        else:
            st.caption("Belum ada pengeluaran bulan ini.")


def _tren():
    bulan = [geser_bulan(ym_ini(), -i) for i in range(11, -1, -1)]
    masuk = [ringkas_bulan(b)[0] for b in bulan]
    keluar = [ringkas_bulan(b)[1] for b in bulan]
    label = [nama_bulan(b)[:3] + " " + b[2:4] for b in bulan]
    with st.container(key="kartu_g_tren1"):
        st.markdown("**Pemasukan dan pengeluaran, 12 bulan terakhir**")
        st.bar_chart(pd.DataFrame({"Bulan": label, "Pemasukan": masuk, "Pengeluaran": keluar}).set_index("Bulan"),
                     color=["#34a874", "#d64545"], stack=False)
    with st.container(key="kartu_g_tren2"):
        st.markdown("**Total saldo di akhir tiap bulan**")
        akhir = []
        for b in bulan:
            batas = geser_bulan(b, 1) + "-01"
            tgl_akhir = (pd.Timestamp(batas) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            akhir.append(sum(saldo_dompet(d["id"], tgl_akhir) for d in D["dompet"] if not d.get("arsip")))
        st.line_chart(pd.DataFrame({"Bulan": label, "Saldo": akhir}).set_index("Bulan"), color="#3b82c4")
    ada = [(m, k) for m, k in zip(masuk, keluar) if m or k]
    if ada:
        st.caption(f"Rata-rata bulanan: pemasukan {rp(sum(m for m, _ in ada) / len(ada))}, pengeluaran {rp(sum(k for _, k in ada) / len(ada))}.")


def _dompet():
    ym = pilih_bulan("lp_bulan_d")
    baris = []
    for d in dompet_aktif():
        m = k = tin = tout = 0
        for t in transaksi_bulan(ym):
            if t["jenis"] == "masuk" and t["dompet"] == d["id"]:
                m += t["jumlah"]
            elif t["jenis"] == "keluar" and t["dompet"] == d["id"]:
                k += t["jumlah"]
            elif t["jenis"] == "transfer":
                if t["dompet"] == d["id"]:
                    tout += t["jumlah"] + int(t.get("biaya", 0) or 0)
                if t.get("ke") == d["id"]:
                    tin += t["jumlah"]
        baris.append({"Dompet": d["nama"], "Pemasukan": m, "Pengeluaran": k, "Transfer masuk": tin, "Transfer keluar": tout,
                      "Saldo sekarang": saldo_dompet(d["id"])})
    if not baris:
        st.info("Belum ada dompet.")
        return
    df = pd.DataFrame(baris).set_index("Dompet")
    st.dataframe(df.style.format("{:,.0f}".format), width="stretch")
    st.caption(f"Arus tiap dompet pada {nama_bulan(ym)}. Satuan rupiah.")


def _barang():
    bulan = st.selectbox("Periode", ["semua"] + daftar_bulan(), key="lp_bulan_b",
                         format_func=lambda b: "Semua waktu" if b == "semua" else nama_bulan(b))
    baris, ada = [], {}
    for b in D["barang"]:
        ts = [t for t in transaksi_barang(b["id"]) if bulan == "semua" or t["tgl"][:7] == bulan]
        if not ts:
            continue
        qty = sum(float(t.get("qty") or 0) for t in ts)
        total = sum(t["jumlah"] for t in ts)
        ada[b["id"]] = b
        disk = [t for t in ts if info_diskon(t)]
        hemat = sum(info_diskon(t)[1] * float(t.get("qty") or 0) for t in disk)
        baris.append({"Barang": b["nama"], "Kategori": nama_kat(b["kategori"]), "Kali dibeli": len(ts), "Saat diskon": f"{len(disk)}/{len(ts)}",
                      "Banyaknya": round(qty, 2), "Total (Rp)": total, "Hemat (Rp)": round(hemat),
                      "Harga rata-rata": round(total / qty) if qty else 0, "Harga terakhir": int(ts[0].get("harga_satuan") or 0)})
    if not baris:
        st.info("Belum ada transaksi yang memakai barang pada periode ini. Pilih barang saat mencatat transaksi.")
        return
    df = pd.DataFrame(baris).sort_values("Total (Rp)", ascending=False).set_index("Barang")
    st.dataframe(df.style.format({"Total (Rp)": "{:,.0f}".format, "Hemat (Rp)": "{:,.0f}".format, "Harga rata-rata": "{:,.0f}".format, "Harga terakhir": "{:,.0f}".format,
                                  "Banyaknya": "{:g}".format}), width="stretch")
    with st.container(key="kartu_g_lp_harga"):
        pilih = st.selectbox("Lihat perubahan harga", list(ada), format_func=lambda i: ada[i]["nama"], key="lp_barang_harga")
        titik = sorted([t for t in transaksi_barang(pilih) if t.get("harga_satuan")], key=lambda t: (t["tgl"], t.get("dibuat", "")))
        if len(titik) >= 2:
            ada_diskon = any(info_diskon(t) for t in titik)
            data_g = {"Tanggal": [t["tgl"] for t in titik], "Harga bayar": [t["harga_satuan"] for t in titik]}
            if ada_diskon:
                data_g["Harga normal"] = [int(t.get("harga_normal") or t["harga_satuan"]) for t in titik]
            st.line_chart(pd.DataFrame(data_g).set_index("Tanggal"), color=["#3b82c4", "#9aa0a6"] if ada_diskon else "#3b82c4")
            naik = titik[-1]["harga_satuan"] - titik[0]["harga_satuan"]
            st.caption(f"Dari {rp(titik[0]['harga_satuan'])} menjadi {rp(titik[-1]['harga_satuan'])} ({'naik' if naik > 0 else 'turun' if naik < 0 else 'tetap'}"
                       f"{' ' + rp(abs(naik)) if naik else ''}).")
        else:
            st.caption("Grafik harga muncul setelah barang ini dibeli minimal dua kali.")
        disk_b = [t for t in transaksi_barang(pilih) if info_diskon(t) and (bulan == "semua" or t["tgl"][:7] == bulan)]
        semua_b = [t for t in transaksi_barang(pilih) if t.get("harga_satuan") and (bulan == "semua" or t["tgl"][:7] == bulan)]
        if semua_b:
            st.markdown("**Beli saat diskon atau tidak**")
            hemat_b = sum(info_diskon(t)[1] * float(t.get("qty") or 0) for t in disk_b)
            rata = round(sum(info_diskon(t)[0] for t in disk_b) / len(disk_b)) if disk_b else 0
            st.markdown(f"Dari **{len(semua_b)}** kali beli, **{len(disk_b)}** kali saat diskon"
                        + (f" (rata-rata diskon {rata}%, total hemat {rp(round(hemat_b))})." if disk_b else ". Belum ada pembelian dengan diskon tercatat."))
            if disk_b:
                from keuangan.bantu import toko_dari
                st.dataframe(pd.DataFrame([{"Tanggal": fmt_iso(t["tgl"]), "Toko": (toko_dari(t.get("toko")) or {}).get("nama", ""),
                                            "Harga normal": int(t["harga_normal"]), "Bayar": int(t["harga_satuan"]),
                                            "Diskon": f"{info_diskon(t)[0]}%", "Banyaknya": float(t.get("qty") or 0)} for t in disk_b]),
                             hide_index=True, width="stretch")
            else:
                st.caption("Isi Harga normal saat mencatat pembelian yang sedang diskon, supaya terlihat di sini.")
        per = {}
        for t in transaksi_barang(pilih):
            if t.get("harga_satuan"):
                per.setdefault(t.get("toko") or "", []).append(t)
        if len(per) >= 1:
            from keuangan.bantu import toko_dari
            baris_t = []
            for k, ts_ in per.items():
                hs_ = [int(x["harga_satuan"]) for x in ts_]
                baris_t.append({"Toko": (toko_dari(k) or {}).get("nama", "(tanpa toko)"), "Dibeli": len(ts_),
                                "Harga terakhir": hs_[0], "Rata-rata": round(sum(hs_) / len(hs_)), "Termurah": min(hs_)})
            dft = pd.DataFrame(baris_t).sort_values("Rata-rata").set_index("Toko")
            st.markdown("**Harga per toko**")
            st.dataframe(dft.style.format("{:,.0f}".format, subset=["Harga terakhir", "Rata-rata", "Termurah"]), width="stretch")
            ada_toko = dft[dft.index != "(tanpa toko)"]
            if len(ada_toko) >= 2:
                st.caption(f"Rata-rata termurah di {ada_toko.index[0]} ({rp(ada_toko.iloc[0]['Rata-rata'])}); "
                           f"termahal di {ada_toko.index[-1]} ({rp(ada_toko.iloc[-1]['Rata-rata'])}).")


def _toko():
    bulan = st.selectbox("Periode", ["semua"] + daftar_bulan(), key="lp_bulan_t",
                         format_func=lambda b: "Semua waktu" if b == "semua" else nama_bulan(b))
    baris = []
    for x in D["toko"]:
        ts = [t for t in transaksi_toko(x["id"]) if t["jenis"] == "keluar" and (bulan == "semua" or t["tgl"][:7] == bulan)]
        if not ts:
            continue
        total = sum(t["jumlah"] for t in ts)
        baris.append({"Toko": x["nama"], "Jenis": x.get("jenis", ""), "Lokasi": x.get("lokasi", ""), "Kunjungan": len(ts),
                      "Total (Rp)": total, "Rata-rata (Rp)": round(total / len(ts)), "Terakhir": ts[0]["tgl"]})
    if not baris:
        st.info("Belum ada pengeluaran dengan toko pada periode ini. Pilih toko saat mencatat transaksi.")
    else:
        df = pd.DataFrame(baris).sort_values("Total (Rp)", ascending=False).set_index("Toko")
        st.dataframe(df.style.format({"Total (Rp)": "{:,.0f}".format, "Rata-rata (Rp)": "{:,.0f}".format}), width="stretch")
        st.bar_chart(df["Total (Rp)"], color="#256b4a")
    jam = {}
    for t in D["transaksi"]:
        if t["jenis"] == "keluar" and t.get("waktu") and (bulan == "semua" or t["tgl"][:7] == bulan):
            h = int(t["waktu"][:2])
            jam[h] = jam.get(h, 0) + t["jumlah"]
    with st.container(key="kartu_g_lp_jam"):
        st.markdown("**Jam belanja**")
        if jam:
            st.bar_chart(pd.Series({f"{h:02d}": jam.get(h, 0) for h in range(24)}, name="Pengeluaran (Rp)"), color="#3b82c4")
            puncak = max(jam, key=jam.get)
            st.caption(f"Pengeluaran terbesar terjadi sekitar pukul {puncak:02d}.00 ({rp(jam[puncak])}). Hanya transaksi yang punya waktu beli.")
        else:
            st.caption("Belum ada transaksi dengan waktu beli pada periode ini.")


def halaman_laporan():
    t1, t2, t3, t4, t5 = st.tabs(["Bulanan", "Tren", "Per dompet", "Barang", "Toko"])
    with t1:
        _bulanan()
    with t2:
        _tren()
    with t3:
        _dompet()
    with t4:
        _barang()
    with t5:
        _toko()
