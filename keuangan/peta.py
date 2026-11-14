"""Peta toko: tandai titik lokasi (ketuk peta atau pakai lokasi saat ini) dan lihat semua toko di satu peta.

Memakai OpenStreetMap lewat folium, gratis dan tanpa kunci API. Paket dipanggil saat dibutuhkan,
jadi aplikasi tetap jalan (tanpa fitur peta) kalau paketnya belum terpasang.
"""
import streamlit as st

PUSAT_BAWAAN = [-2.5, 118.0]  # tengah Indonesia
BUTUH = "Fitur peta butuh paket `folium`, `streamlit-folium`, dan `streamlit-js-eval` (lihat requirements.txt)."


def titik_dari(x: dict | None):
    """(lat, lon) dari data toko, atau None."""
    try:
        if x and x.get("lat") not in (None, "") and x.get("lon") not in (None, ""):
            return float(x["lat"]), float(x["lon"])
    except (TypeError, ValueError):
        pass
    return None


def url_peta(x: dict) -> str:
    """Tautan Google Maps untuk toko: dari titik kalau ada, kalau tidak dari tautan yang ditempel."""
    t = titik_dari(x)
    if t:
        return f"https://www.google.com/maps/search/?api=1&query={t[0]:.6f},{t[1]:.6f}"
    u = (x.get("peta") or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else ""


def pilih_titik(kunci: str, awal):
    """Peta untuk menandai satu titik. Kembalikan (lat, lon) yang berlaku sekarang atau None.

    Keadaan disimpan di session_state[f'titik_{kunci}']; hapus kunci itu setelah menyimpan.
    """
    sk = f"titik_{kunci}"
    if sk not in st.session_state:
        st.session_state[sk] = awal
    cur = st.session_state[sk]
    try:
        import folium
        from streamlit_folium import st_folium
        from streamlit_js_eval import get_geolocation
    except ImportError:
        st.caption(BUTUH)
        return cur
    ver = st.session_state.setdefault(f"{sk}_ver", 0)
    c1, c2 = st.columns(2)
    if c1.button("Pakai lokasi saya sekarang", key=f"{sk}_gps", help="Browser akan meminta izin lokasi."):
        st.session_state[f"{sk}_minta"] = True
    if cur and c2.button("Hapus titik", key=f"{sk}_hapus"):
        st.session_state[sk] = None
        st.session_state[f"{sk}_ver"] = ver + 1
        st.rerun()
    if st.session_state.get(f"{sk}_minta"):
        loc = get_geolocation(component_key=f"{sk}_geo")
        if loc and loc.get("coords"):
            st.session_state[sk] = (round(float(loc["coords"]["latitude"]), 6), round(float(loc["coords"]["longitude"]), 6))
            st.session_state[f"{sk}_minta"] = False
            st.session_state[f"{sk}_ver"] = ver + 1
            st.rerun()
        elif loc and loc.get("error"):
            st.session_state[f"{sk}_minta"] = False
            st.warning("Lokasi tidak bisa dibaca. Izinkan akses lokasi di browser, atau ketuk peta untuk memasang titik.")
        else:
            st.caption("Menunggu izin lokasi dari browser…")
    m = folium.Map(location=list(cur) if cur else PUSAT_BAWAAN, zoom_start=17 if cur else 5, control_scale=True)
    if cur:
        folium.Marker(list(cur)).add_to(m)
    r = st_folium(m, height=300, width=700, key=f"{sk}_peta_{ver}", returned_objects=["last_clicked"])
    k = (r or {}).get("last_clicked")
    if k and st.session_state.get(f"{sk}_klik") != (k["lat"], k["lng"]):
        st.session_state[f"{sk}_klik"] = (k["lat"], k["lng"])
        st.session_state[sk] = (round(k["lat"], 6), round(k["lng"], 6))
        st.session_state[f"{sk}_ver"] = ver + 1
        st.rerun()
    st.caption(f"Titik: {cur[0]:.6f}, {cur[1]:.6f}" if cur else "Ketuk peta untuk memasang titik toko.")
    return st.session_state[sk]


def peta_semua(daftar: list):
    """Satu peta berisi pin semua toko yang punya titik."""
    try:
        import folium
        from streamlit_folium import st_folium
    except ImportError:
        st.caption(BUTUH)
        return
    ada = [(x, titik_dari(x)) for x in daftar if titik_dari(x)]
    if not ada:
        st.caption("Belum ada toko yang punya titik lokasi. Tandai titik saat menambah atau mengubah toko.")
        return
    m = folium.Map(location=list(ada[0][1]), zoom_start=14, control_scale=True)
    for x, t in ada:
        folium.Marker(list(t), tooltip=x["nama"], popup=x["nama"]).add_to(m)
    if len(ada) > 1:
        m.fit_bounds([list(t) for _, t in ada], padding=(30, 30))
    st_folium(m, height=320, width=700, key="peta_semua_toko", returned_objects=[])


# ---------------------------------------------------------------- toko terdekat
def jarak_km(a, b) -> float:
    """Jarak garis lurus (km) antara dua titik (lat, lon), rumus haversine."""
    from math import asin, cos, radians, sin, sqrt
    la1, lo1, la2, lo2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def teks_jarak(km: float) -> str:
    return f"{round(km * 1000 / 10) * 10:.0f} m" if km < 1 else f"{km:.1f} km".replace(".", ",")


def terdekat(pos, daftar: list, n: int = 5) -> list:
    """[(toko, km)] toko yang punya titik, dari yang paling dekat ke posisi (lat, lon)."""
    hasil = [(x, jarak_km(pos, t)) for x in daftar if (t := titik_dari(x))]
    return sorted(hasil, key=lambda z: z[1])[:n]


def proses_gps(sk: str):
    """Panggil SEBELUM widget yang nilainya mau diisi dari lokasi. Bila tombol lokasi (tombol_gps) sudah ditekan,
    minta lokasi ke browser dan kembalikan (lat, lon) begitu tersedia, kalau belum None."""
    if not st.session_state.get(f"{sk}_minta"):
        return None
    try:
        from streamlit_js_eval import get_geolocation
    except ImportError:
        st.session_state[f"{sk}_minta"] = False
        st.caption(BUTUH)
        return None
    loc = get_geolocation(component_key=f"{sk}_geo")
    if loc and loc.get("coords"):
        st.session_state[f"{sk}_minta"] = False
        return float(loc["coords"]["latitude"]), float(loc["coords"]["longitude"])
    if loc and loc.get("error"):
        st.session_state[f"{sk}_minta"] = False
        st.warning("Lokasi tidak bisa dibaca. Izinkan akses lokasi di browser lalu coba lagi.")
    else:
        st.caption("Menunggu izin lokasi dari browser…")
    return None


def tombol_gps(sk: str, label: str = "Toko terdekat dari saya"):
    st.button(label, key=f"{sk}_btn", on_click=lambda: st.session_state.update({f"{sk}_minta": True}),
              help="Browser akan meminta izin lokasi. Lokasi tidak disimpan.")
