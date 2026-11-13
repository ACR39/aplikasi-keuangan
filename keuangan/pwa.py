"""Pasang aplikasi di layar utama HP (PWA).

Streamlit tidak membiarkan kita mengubah <head> halaman, jadi manifest dan ikon dipasang lewat komponen tak terlihat
(pola yang sama dengan cookie sesi di akses.py). Ikon diambil dari folder static/pwa, yang dilayani Streamlit kalau
`enableStaticServing = true` di .streamlit/config.toml. Tanpa itu aplikasi tetap jalan normal, hanya tanpa ikon khusus.

Tidak ada service worker: aplikasi Streamlit selalu butuh koneksi ke server, jadi mode offline memang tidak mungkin.
"""
import streamlit as st
import streamlit.components.v1 as components

NAMA = "Pelacak Keuangan"
NAMA_PENDEK = "Keuangan"
WARNA = "#256b4a"

_JS = """<script>
(function () {
  try {
    const app = window.parent;                       // dokumen aplikasi Streamlit
    let atas = app;                                  // halaman paling atas (bisa pembungkus di hosting tertentu)
    try { void window.top.document.title; atas = window.top; } catch (e) { atas = app; }
    const doc = atas.document;
    const asal = app.location.origin;
    const dasar = asal + app.location.pathname.replace(/\\/+$/, '') + '/app/static/pwa/';
    const mulai = atas.location.origin + atas.location.pathname;

    const manifest = {
      name: "__NAMA__", short_name: "__PENDEK__",
      description: "Catat pemasukan, pengeluaran, anggaran, dan target keuangan pribadi.",
      lang: "id", dir: "ltr",
      start_url: mulai, scope: atas.location.origin + "/", id: mulai,
      display: "standalone", orientation: "portrait",
      background_color: "#ffffff", theme_color: "__WARNA__",
      icons: [
        { src: dasar + "icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
        { src: dasar + "icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
        { src: dasar + "icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
      ]
    };

    function pasang(tag, atribut, id) {
      let el = id ? doc.getElementById(id) : null;
      if (!el) { el = doc.createElement(tag); if (id) el.id = id; doc.head.appendChild(el); }
      for (const k in atribut) el.setAttribute(k, atribut[k]);
      return el;
    }
    const url = atas.URL.createObjectURL(new atas.Blob([JSON.stringify(manifest)], { type: 'application/manifest+json' }));
    pasang('link', { rel: 'manifest', href: url }, 'pwa-manifest');
    pasang('link', { rel: 'apple-touch-icon', href: dasar + 'apple-touch-icon.png' }, 'pwa-apple-icon');
    pasang('meta', { name: 'theme-color', content: '__WARNA__' }, 'pwa-warna');
    pasang('meta', { name: 'mobile-web-app-capable', content: 'yes' }, 'pwa-mwac');
    pasang('meta', { name: 'apple-mobile-web-app-capable', content: 'yes' }, 'pwa-amwac');
    pasang('meta', { name: 'apple-mobile-web-app-title', content: '__PENDEK__' }, 'pwa-judul');
    pasang('meta', { name: 'apple-mobile-web-app-status-bar-style', content: 'default' }, 'pwa-status');
  } catch (e) { /* PWA hanya tambahan, jangan sampai mengganggu aplikasi */ }
})();
</script>"""


def _sisipkan(html: str):
    """Jalankan skrip lewat iframe tak terlihat. st.iframe dipakai di Streamlit baru (components.html sudah
    ditandai akan dihapus), dan components.html dipakai kalau versinya lama."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(html, height=1)
            return
        except Exception:
            pass
    components.html(html, height=0)


def pasang_pwa():
    """Sisipkan manifest dan ikon satu kali per sesi."""
    if st.session_state.get("pwa_terpasang"):
        return
    st.session_state.pwa_terpasang = True
    _sisipkan(_JS.replace("__NAMA__", NAMA).replace("__PENDEK__", NAMA_PENDEK).replace("__WARNA__", WARNA))


_JS_SAMBUNG = """<script>
(function () {
  try {
    const app = window.parent, doc = app.document;
    if (app.__sambungUlang) return;
    app.__sambungUlang = true;
    let sembunyiSejak = 0, memeriksa = false;

    // Streamlit menampilkan dialog "Connection error" atau status "Connecting" saat koneksi ke server putus
    function keadaan() {
      const teks = (doc.body && doc.body.innerText) || '';
      if (/connection error|is streamlit still running/i.test(teks)) return 'galat';
      const st = doc.querySelector('[data-testid="stConnectionStatus"]');
      if (st && /connect/i.test(st.innerText || '')) return 'menyambung';
      return 'baik';
    }
    function muatUlang() { try { app.location.reload(); } catch (e) {} }

    function periksa() {
      if (memeriksa) return;
      memeriksa = true;
      const lama = Date.now() - sembunyiSejak;
      if (sembunyiSejak && lama > 30 * 60 * 1000) { muatUlang(); return; }   // terlalu lama di belakang: sesi server pasti sudah habis
      let n = 0, baik = 0, menyambung = 0;
      const t = setInterval(function () {                                      // beri waktu 20 detik untuk tersambung sendiri
        n++;
        const k = keadaan();
        if (k === 'galat' && n >= 3) { clearInterval(t); muatUlang(); return; }
        menyambung = k === 'menyambung' ? menyambung + 1 : 0;
        if (menyambung >= 8) { clearInterval(t); muatUlang(); return; }
        baik = k === 'baik' ? baik + 1 : 0;
        if (baik >= 4 || n >= 20) { clearInterval(t); memeriksa = false; }
      }, 1000);
    }
    doc.addEventListener('visibilitychange', function () {
      if (doc.visibilityState === 'hidden') { sembunyiSejak = Date.now(); }
      else { periksa(); }
    });
    app.addEventListener('pageshow', function (e) { if (e.persisted) periksa(); });
    app.addEventListener('online', periksa);
  } catch (e) { /* hanya tambahan */ }
})();
</script>"""


def pasang_sambung_ulang():
    """Bila HP kembali dari latar belakang dan koneksi ke server sudah putus, muat ulang halaman otomatis (tanpa disuruh refresh manual)."""
    if st.session_state.get("sambung_terpasang"):
        return
    st.session_state.sambung_terpasang = True
    _sisipkan(_JS_SAMBUNG)
