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
    if c1.button("📍 Pakai lokasi saya sekarang", key=f"{sk}_gps", help="Browser akan meminta izin lokasi."):
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
