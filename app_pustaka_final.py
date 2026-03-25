import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from PIL import Image
import requests
from io import BytesIO

# --- Konfigurasi Visual ---
TARGET_W = 180
TARGET_H = 250

# --- 1. Database Setup ---
conn = sqlite3.connect('pustaka_pribadi_v3.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS buku (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        judul TEXT,
        penulis TEXT,
        kategori TEXT,
        status TEXT,
        peminjam TEXT,
        cover_url TEXT,
        tgl_kembali TEXT,
        rating INTEGER,
        ulasan TEXT,
        harga_beli REAL,
        tgl_perolehan TEXT
    )
''')
conn.commit()

st.set_page_config(page_title="Pustaka Eko V3", layout="wide")

# --- 2. Fungsi Pendukung ---
@st.cache_data(show_spinner=False)
def get_uniform_cover(url):
    placeholder = f"https://via.placeholder.com/{TARGET_W}x{TARGET_H}?text=No+Cover"
    if not url or not url.startswith("http"):
        return placeholder
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(BytesIO(response.content))
        if img.mode in ('RGBA', 'LA'): img = img.convert('RGB')
        
        w, h = img.size
        target_ratio = TARGET_W / TARGET_H
        img_ratio = w / h
        if img_ratio > target_ratio:
            new_w = int(TARGET_H * img_ratio)
            img = img.resize((new_w, TARGET_H), Image.Resampling.LANCZOS)
            left = (new_w - TARGET_W) / 2
            img = img.crop((left, 0, left + TARGET_W, TARGET_H))
        else:
            new_h = int(TARGET_W / img_ratio)
            img = img.resize((TARGET_W, new_h), Image.Resampling.LANCZOS)
            top = (new_h - TARGET_H) / 2
            img = img.crop((0, top, TARGET_W, top + TARGET_H))
        return img
    except:
        return placeholder

# --- 3. UI & Navigasi ---
st.sidebar.title(f"📚 Pustaka Pak Eko")
menu = st.sidebar.selectbox("Pilih Menu", [
    "📖 Katalog Visual", 
    "🛒 Tambah Koleksi & Pembelian", 
    "🔄 Transaksi (Pinjam/Tukar)", 
    "⚙️ Manajemen Data"
])

# --- TAB: KATALOG VISUAL ---
if menu == "📖 Katalog Visual":
    st.header("Rak Buku Digital")
    df = pd.read_sql_query('SELECT * FROM buku WHERE status != "Wishlist"', conn)
    
    if not df.empty:
        cols = st.columns(5)
        for idx, row in df.iterrows():
            with cols[idx % 5]:
                st.image(get_uniform_cover(row['cover_url']), use_container_width=True)
                st.write(f"**{row['judul']}**")
                st.caption(f"{row['kategori']} | ⭐ {row['rating']}")
                with st.expander("Detail"):
                    st.write(f"Penulis: {row['penulis']}")
                    st.info(f"Ulasan: {row['ulasan']}" if row['ulasan'] else "Belum ada ulasan.")
    else:
        st.info("Katalog kosong.")

# --- TAB: TAMBAH KOLEKSI (DENGAN AUTO-CLEAR) ---
elif menu == "🛒 Tambah Koleksi & Pembelian":
    st.header("Input Koleksi Baru")
    
    # Kategori baru sesuai permintaan
    kategori_list = [
        "Biografi", "Keuangan", "Manajemen", "Teknologi", "IT", 
        "Pendidikan", "Sains", "Sejarah", "Agama", "Bisnis", "Fiksi", "Lainnya"
    ]
    
    # Parameter clear_on_submit=True akan menghapus isi field setelah klik simpan
    with st.form("form_tambah_buku", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            j = st.text_input("Judul Buku *")
            p = st.text_input("Penulis")
            kat = st.selectbox("Jenis/Kategori Buku", kategori_list)
        with col2:
            url = st.text_input("URL Link Cover (Opsional)")
            harga = st.number_input("Harga Beli (Rp)", min_value=0, step=1000)
            status_awal = st.radio("Status", ["Tersedia", "Wishlist"], horizontal=True)
        
        submitted = st.form_submit_button("Simpan ke Perpustakaan")
        
        if submitted:
            if j:
                tgl = datetime.now().strftime("%Y-%m-%d")
                c.execute('''INSERT INTO buku (judul, penulis, kategori, status, peminjam, cover_url, tgl_kembali, rating, ulasan, harga_beli, tgl_perolehan) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                          (j, p, kat, status_awal, "-", url, "-", 0, "", harga, tgl))
                conn.commit()
                st.success(f"🎉 Sukses! Buku '{j}' telah berhasil dicatat.")
                st.balloons()
            else:
                st.error("Judul buku tidak boleh kosong!")

# --- TAB: PINJAM & TUKAR ---
elif menu == "🔄 Transaksi (Pinjam/Tukar)":
    st.header("Layanan Peminjaman & Tukar Buku")
    df_avail = pd.read_sql_query('SELECT id, judul, status, peminjam FROM buku WHERE status != "Wishlist"', conn)
    
    if not df_avail.empty:
        pilih = st.selectbox("Pilih Judul Buku", df_avail['judul'].tolist())
        row = df_avail[df_avail['judul'] == pilih].iloc[0]
        
        st.info(f"Status Saat Ini: **{row['status']}**")
        
        with st.form("form_transaksi", clear_on_submit=True):
            opsi = st.selectbox("Jenis Transaksi", ["Kembalikan (Tersedia)", "Pinjamkan", "Tukarkan / Barter"])
            nama_kontak = st.text_input("Nama Teman / Kolega")
            
            if st.form_submit_button("Proses Transaksi"):
                mapping = {"Kembalikan (Tersedia)": "Tersedia", "Pinjamkan": "Dipinjam", "Tukarkan / Barter": "Ditukar"}
                status_final = mapping[opsi]
                peminjam_final = nama_kontak if opsi != "Kembalikan (Tersedia)" else "-"
                
                c.execute('UPDATE buku SET status=?, peminjam=? WHERE id=?', (status_final, peminjam_final, row['id']))
                conn.commit()
                st.success(f"Berhasil mengupdate status '{pilih}' menjadi {status_final}.")
    else:
        st.warning("Belum ada buku di katalog untuk diproses.")

# --- TAB: MANAJEMEN ---
elif menu == "⚙️ Manajemen Data":
    st.header("Edit & Hapus Data")
    df_edit = pd.read_sql_query('SELECT * FROM buku', conn)
    
    if not df_edit.empty:
        judul_edit = st.selectbox("Pilih Buku untuk Diedit/Hapus", df_edit['judul'].tolist())
        data_buku = df_edit[df_edit['judul'] == judul_edit].iloc[0]
        
        tab_edit, tab_hapus = st.tabs(["Edit Info", "Hapus Buku"])
        
        with tab_edit:
            with st.form("edit_buku"):
                up_j = st.text_input("Judul", value=data_buku['judul'])
                up_p = st.text_input("Penulis", value=data_buku['penulis'])
                up_rat = st.slider("Rating", 0, 5, int(data_buku['rating']))
                up_ul = st.text_area("Ulasan", value=data_buku['ulasan'])
                if st.form_submit_button("Update Data"):
                    c.execute('UPDATE buku SET judul=?, penulis=?, rating=?, ulasan=? WHERE id=?', 
                              (up_j, up_p, up_rat, up_ul, data_buku['id']))
                    conn.commit()
                    st.success("Perubahan disimpan!")
                    st.rerun()
        
        with tab_hapus:
            st.warning(f"Apakah Anda yakin ingin menghapus '{judul_edit}' secara permanen?")
            if st.button("Ya, Hapus Buku"):
                c.execute('DELETE FROM buku WHERE id=?', (data_buku['id'],))
                conn.commit()
                st.error("Buku telah dihapus.")
                st.rerun()