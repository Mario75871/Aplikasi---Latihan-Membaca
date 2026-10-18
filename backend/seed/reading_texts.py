"""Seed data teks bacaan BacaLaras (F-04, v2.5 "target panjang 2x").

Level 1-3 dipetakan ke jenjang B1-B3 (Perka BSKAP 030/P/2022).
Batas (lihat seed/validator.py, satu-satunya penegaknya):
- Level 1 (B1): maks 7 kata/kalimat, maks 10 kalimat, maks 2 paragraf, 50-70 kata
- Level 2 (B2): maks 9 kata/kalimat, maks 14 kalimat, maks 2 paragraf, 90-126 kata
- Level 3 (B3): maks 12 kata/kalimat, maks 21 kalimat, maks 7 paragraf,
  maks 3 kalimat/paragraf, 160-216 kata

Teks ditulis dengan ejaan baku dan tanda baca sederhana (sumber target_text framework).
"""
from __future__ import annotations

# Struktur: setiap teks punya id, title, content, grade, complexity, book_level,
# theme, proper_nouns, questions (3-5, label retrieve/interpret/reflect)
#
# UUID tetap (Fase 1): id memakai uuid statis deterministik agar bentuk data
# in-memory == Supabase. Alias "rd-00N" tetap diekspor lewat SEED_IDS supaya
# test & loader merujuk SIMBOL, bukan literal uuid yang tersebar.
SEED_IDS = {
    "reading_1": "00000000-0000-0000-0000-000000000001",
    "reading_2": "00000000-0000-0000-0000-000000000002",
    "reading_3": "00000000-0000-0000-0000-000000000003",
    "reading_4": "00000000-0000-0000-0000-000000000004",
    "reading_5": "00000000-0000-0000-0000-000000000005",
    "reading_6": "00000000-0000-0000-0000-000000000006",
    "reading_7": "00000000-0000-0000-0000-000000000007",
    "reading_8": "00000000-0000-0000-0000-000000000008",
    "reading_9": "00000000-0000-0000-0000-000000000009",
    # Classes (uuid tetap)
    "class_1a": "00000000-0000-0000-0000-000000000101",
    "class_2a": "00000000-0000-0000-0000-000000000102",
    "class_3a": "00000000-0000-0000-0000-000000000103",
    # Students (uuid tetap)
    "student_dika": "00000000-0000-0000-0000-000000000201",
    "student_sari": "00000000-0000-0000-0000-000000000202",
    "student_boni": "00000000-0000-0000-0000-000000000203",
    "student_rani": "00000000-0000-0000-0000-000000000204",
    # Guru (uuid tetap) — pemilik data seed (integrasi #3, D3). Bukan auth.users
    # nyata; dipakai agar kelas/siswa seed punya pemilik yang konsisten di demo.
    "teacher_demo": "00000000-0000-0000-0000-000000000301",
}

#: Pemetaan alias lama → uuid (kompatibilitas & dokumentasi).
LEGACY_ID_MAP = {
    "rd-001": SEED_IDS["reading_1"],
    "rd-002": SEED_IDS["reading_2"],
    "rd-003": SEED_IDS["reading_3"],
    "rd-004": SEED_IDS["reading_4"],
    "rd-005": SEED_IDS["reading_5"],
    "rd-006": SEED_IDS["reading_6"],
    "rd-007": SEED_IDS["reading_7"],
    "rd-008": SEED_IDS["reading_8"],
    "rd-009": SEED_IDS["reading_9"],
    "cls-1a": SEED_IDS["class_1a"],
    "cls-2a": SEED_IDS["class_2a"],
    "cls-3a": SEED_IDS["class_3a"],
    "std-001": SEED_IDS["student_dika"],
    "std-002": SEED_IDS["student_sari"],
    "std-003": SEED_IDS["student_boni"],
    "std-004": SEED_IDS["student_rani"],
}

#: Definisi classes & students seed (uuid tetap; FK konsisten).
#: teacher_id (D3, integrasi #3): kelas/siswa seed dimiliki guru demo tetap.
_TEACHER_DEMO = SEED_IDS["teacher_demo"]

SEED_CLASSES = [
    {"id": SEED_IDS["class_1a"], "name": "Kelas 1A", "grade": 1, "teacher_id": _TEACHER_DEMO},
    {"id": SEED_IDS["class_2a"], "name": "Kelas 2A", "grade": 2, "teacher_id": _TEACHER_DEMO},
    {"id": SEED_IDS["class_3a"], "name": "Kelas 3A", "grade": 3, "teacher_id": _TEACHER_DEMO},
]

SEED_STUDENTS = [
    {"id": SEED_IDS["student_dika"], "name": "Dika Pratama", "grade": 2, "class_id": SEED_IDS["class_2a"], "teacher_id": _TEACHER_DEMO},
    {"id": SEED_IDS["student_sari"], "name": "Sari Anggraini", "grade": 2, "class_id": SEED_IDS["class_2a"], "teacher_id": _TEACHER_DEMO},
    {"id": SEED_IDS["student_boni"], "name": "Boni Santoso", "grade": 3, "class_id": SEED_IDS["class_3a"], "teacher_id": _TEACHER_DEMO},
    {"id": SEED_IDS["student_rani"], "name": "Rani Wulandari", "grade": 1, "class_id": SEED_IDS["class_1a"], "teacher_id": _TEACHER_DEMO},
]


#: Catatan konvensi pertanyaan:
#: - `competency` ∈ retrieve | interpret | reflect.
#: - `options` selalu TEPAT 2 (satu kunci, satu pengecoh) karena Mode Siswa
#:   hanya merender pilihan ganda dan skoring backend mencocokkan `answer_id`.
#: - `answer_id` sengaja disebar antara "a" dan "b" (seed lama selalu "a",
#:   sehingga siswa bisa menebak dengan memilih opsi pertama).
#: - Pertanyaan `reflect` tetap pilihan ganda: kunci aslinya ("jawaban terbuka
#:   yang masuk akal") tidak bisa dinilai otomatis oleh skoring yang ada.
READING_TEXTS = [
    # ========== LEVEL 1 (B1) ==========
    {
        "id": SEED_IDS["reading_1"],
        "title": "Sita Bersiap ke Sekolah",
        "content": (
            "Pagi ini, Sita bangun lebih awal. "
            "Ia merapikan tempat tidurnya. "
            "Ibu menyiapkan nasi dan telur. "
            "Sita sarapan bersama adik di dapur. "
            "Setelah itu, mereka berangkat sekolah.\n\n"
            "Di jalan, Sita melihat bunga merah. "
            "Kupu-kupu kecil hinggap dekat pagar. "
            "Adik mengingatkan agar mereka berjalan lagi. "
            "Sesampainya di kelas, Sita menyimpan tas. "
            "Ia senang karena datang tepat waktu."
        ),
        "grade": 1,
        "complexity": 1,
        "book_level": "B1",
        "theme": "Keluarga",
        "proper_nouns": ["Sita"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa yang disiapkan Ibu untuk sarapan?",
             "options": [{"id": "a", "text": "Nasi dan telur"}, {"id": "b", "text": "Roti dan susu"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa Sita melanjutkan perjalanan setelah melihat kupu-kupu?",
             "options": [{"id": "a", "text": "Karena ia ingin bermain di jalan"}, {"id": "b", "text": "Agar tidak terlambat sampai di sekolah"}], "answer_id": "b"},
            {"id": "q3", "competency": "reflect", "prompt": "Apa yang kamu siapkan sebelum berangkat sekolah?",
             "options": [{"id": "a", "text": "Menyiapkan tas dan buku pelajaran"}, {"id": "b", "text": "Menonton televisi sampai pagi"}], "answer_id": "a"},
        ],
    },
    {
        "id": SEED_IDS["reading_2"],
        "title": "Kucing Bernama Miko",
        "content": (
            "Beni punya kucing bernama Miko. "
            "Bulu Miko putih dan lembut. "
            "Miko suka tidur dekat jendela. "
            "Beni memberi Miko ikan setiap sore. "
            "Mereka bermain bersama setelah makan.\n\n"
            "Suatu hari, Miko tidak terlihat. "
            "Beni mencari di bawah meja. "
            "Ia mendengar suara dari belakang lemari. "
            "Miko bersembunyi karena takut petir. "
            "Setelah hujan reda, Miko bermain lagi."
        ),
        "grade": 1,
        "complexity": 1,
        "book_level": "B1",
        "theme": "Hewan",
        "proper_nouns": ["Miko", "Beni"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa nama kucing milik Beni?",
             "options": [{"id": "a", "text": "Milo"}, {"id": "b", "text": "Miko"}], "answer_id": "b"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa Miko bersembunyi di belakang lemari?",
             "options": [{"id": "a", "text": "Karena Miko takut suara petir"}, {"id": "b", "text": "Karena Miko sedang lapar"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Bagaimana cara merawat hewan peliharaan?",
             "options": [{"id": "a", "text": "Membiarkannya di luar tanpa makan"}, {"id": "b", "text": "Memberi makan dan minum setiap hari"}], "answer_id": "b"},
        ],
    },
    {
        "id": SEED_IDS["reading_3"],
        "title": "Hujan Pagi",
        "content": (
            "Hari ini hujan turun deras. "
            "Rani memakai jas hujan kuning. "
            "Ia membawa payung biru ke sekolah. "
            "Di jalan, Rani melihat genangan air. "
            "Ia berjalan pelan agar tidak jatuh.\n\n"
            "Di halte, Rani melihat seorang anak. "
            "Anak itu tidak membawa payung. "
            "Mereka berteduh sampai hujan mereda. "
            "Rani mengajak anak itu berjalan bersama. "
            "Ia senang karena telah membantu teman."
        ),
        "grade": 1,
        "complexity": 1,
        "book_level": "B1",
        "theme": "Sekolah",
        "proper_nouns": ["Rani"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa warna jas hujan Rani?",
             "options": [{"id": "a", "text": "Biru"}, {"id": "b", "text": "Kuning"}], "answer_id": "b"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa Rani mengajak anak itu berteduh?",
             "options": [{"id": "a", "text": "Karena anak itu tidak membawa payung"}, {"id": "b", "text": "Karena anak itu membawa banyak barang"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Apa yang kamu lakukan saat melihat teman kesulitan ketika hujan?",
             "options": [{"id": "a", "text": "Menolongnya agar tidak kehujanan"}, {"id": "b", "text": "Pura-pura tidak melihatnya"}], "answer_id": "a"},
        ],
    },
    # ========== LEVEL 2 (B2) ==========
    {
        "id": SEED_IDS["reading_4"],
        "title": "Kebun Kecil Danu",
        "content": (
            "Setiap sore, Danu membantu ayah menyiram tanaman di halaman. "
            "Ia memakai gayung kecil untuk mengambil air dari ember. "
            "Daun cabai tampak segar setelah disiram dengan hati-hati. "
            "Ayah mengajari Danu mencabut rumput liar di sekitar pot. "
            "Mereka bekerja bersama sampai halaman terlihat rapi dan bersih. "
            "Danu senang melihat tanaman tumbuh sehat setiap hari. "
            "Pada hari Sabtu, Danu melihat daun cabai mulai menguning.\n\n"
            "Ia segera menunjukkan keadaan itu kepada ayah. "
            "Ayah memeriksa tanah dan menemukan pot terlalu basah. "
            "Mereka memindahkan pot ke tempat yang lebih cerah. "
            "Danu membuat jadwal sederhana untuk merawat tanaman. "
            "Ia menyiram saat tanah mulai terasa kering. "
            "Beberapa hari kemudian, tanaman itu terlihat lebih segar. "
            "Danu belajar bahwa tanaman membutuhkan perawatan yang sesuai."
        ),
        "grade": 2,
        "complexity": 2,
        "book_level": "B2",
        "theme": "Alam",
        "proper_nouns": ["Danu"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Tanaman apa yang daunnya mulai menguning?",
             "options": [{"id": "a", "text": "Tanaman tomat"}, {"id": "b", "text": "Tanaman cabai"}], "answer_id": "b"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa ayah memindahkan pot ke tempat lebih cerah?",
             "options": [{"id": "a", "text": "Agar pot lebih dekat ke rumah"}, {"id": "b", "text": "Agar tanaman mendapat sinar matahari"}], "answer_id": "b"},
            {"id": "q3", "competency": "reflect", "prompt": "Bagaimana kamu merawat tanaman agar tidak kelebihan air?",
             "options": [{"id": "a", "text": "Menyiram saat tanah mulai kering"}, {"id": "b", "text": "Menyiram tanaman setiap saat"}], "answer_id": "a"},
        ],
    },
    {
        "id": SEED_IDS["reading_5"],
        "title": "Buku dari Perpustakaan",
        "content": (
            "Mira pergi ke perpustakaan sekolah saat waktu istirahat tiba. "
            "Ia mencari buku menarik tentang hewan laut. "
            "Petugas membantu Mira menemukan buku bergambar di rak belakang. "
            "Mira membaca tentang penyu yang bertelur di pantai. "
            "Ia menceritakan isi buku kepada teman sekelasnya. "
            "Temannya ikut tertarik dan ingin membaca buku itu. "
            "Keesokan harinya, Mira meminjam buku dengan izin guru.\n\n"
            "Ia membaca tentang perjalanan anak penyu menuju laut. "
            "Mira mengetahui bahwa plastik dapat membahayakan hewan laut. "
            "Ia berdiskusi dengan teman tentang cara menjaga pantai. "
            "Mira mengusulkan agar kelas membuat poster sederhana. "
            "Poster itu mengajak orang membuang sampah pada tempatnya. "
            "Guru menyambut ide tersebut dan membagi tugas kelompok. "
            "Mira senang karena buku memberi pengetahuan dan ide baru."
        ),
        "grade": 2,
        "complexity": 2,
        "book_level": "B2",
        "theme": "Sekolah",
        "proper_nouns": ["Mira"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Hewan apa yang dibaca Mira dalam bukunya?",
             "options": [{"id": "a", "text": "Penyu"}, {"id": "b", "text": "Lumba-lumba"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa Mira mengusulkan pembuatan poster?",
             "options": [{"id": "a", "text": "Karena ia ingin menghias dinding kelas"}, {"id": "b", "text": "Karena plastik dapat membahayakan hewan laut"}], "answer_id": "b"},
            {"id": "q3", "competency": "reflect", "prompt": "Pesan apa yang ingin kamu sampaikan lewat poster lingkungan?",
             "options": [{"id": "a", "text": "Membuang sampah pada tempatnya"}, {"id": "b", "text": "Membuang sampah ke sungai"}], "answer_id": "a"},
        ],
    },
    {
        "id": SEED_IDS["reading_6"],
        "title": "Sampah di Taman",
        "content": (
            "Pada Minggu pagi, Arga dan kakaknya bersepeda ke taman. "
            "Mereka membawa dua botol air minum di tas. "
            "Di taman, Arga melihat anak menjatuhkan bungkus makanan. "
            "Arga meminta anak itu membuang sampah ke tempatnya. "
            "Anak itu mengambil bungkus lalu memasukkannya ke tempat sampah. "
            "Mereka kemudian bermain bola bersama sampai sore. "
            "Saat beristirahat, Arga melihat sampah lain dekat bangku.\n\n"
            "Kakaknya mengajak Arga mengumpulkan sampah dengan sarung tangan. "
            "Mereka tidak menyentuh benda tajam dan meminta bantuan petugas. "
            "Setelah selesai, mereka mencuci tangan memakai sabun. "
            "Petugas berterima kasih karena taman menjadi lebih bersih. "
            "Ia menjelaskan bahwa taman bersih membuat orang nyaman bermain. "
            "Arga berjanji membawa kantong kecil saat piknik berikutnya. "
            "Mereka juga mengajak teman membawa botol minum sendiri."
        ),
        "grade": 2,
        "complexity": 2,
        "book_level": "B2",
        "theme": "Alam",
        "proper_nouns": ["Arga"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa yang dibawa Arga dan kakaknya ke taman?",
             "options": [{"id": "a", "text": "Dua kantong sampah"}, {"id": "b", "text": "Dua botol air minum"}], "answer_id": "b"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa mereka memakai sarung tangan saat mengumpulkan sampah?",
             "options": [{"id": "a", "text": "Agar tangan terlindungi saat mengambil sampah"}, {"id": "b", "text": "Agar tangan mereka tetap hangat"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Apa kebiasaan yang bisa kamu lakukan agar taman tetap bersih?",
             "options": [{"id": "a", "text": "Membuang sampah ke tempat sampah"}, {"id": "b", "text": "Meninggalkan bungkus di bangku taman"}], "answer_id": "a"},
        ],
    },
    # ========== LEVEL 3 (B3) ==========
    {
        "id": SEED_IDS["reading_7"],
        "title": "Belajar di Kebun Sekolah",
        "content": (
            "Pagi itu, kelas Lani mengunjungi kebun sekolah bersama Bu Rina. "
            "Setiap kelompok mengamati tanaman berbeda dan mencatat perubahan kecil. "
            "Lani memilih tanaman tomat lalu menggambar bentuk daunnya.\n\n"
            "Bu Rina menjelaskan kebutuhan air, cahaya, dan tanah subur. "
            "Lani mencatat penjelasan itu dengan teliti. "
            "Kelompok lain menemukan bunga kecil pada tanaman cabai.\n\n"
            "Minggu berikutnya, siswa kembali untuk membandingkan hasil pengamatan. "
            "Lani melihat tanaman tomat tumbuh lebih tinggi. "
            "Tanaman itu juga memiliki beberapa daun baru.\n\n"
            "Ia melihat tanah di pot lain sangat kering. "
            "Kelompoknya berdiskusi tentang jadwal penyiraman yang tepat. "
            "Sebelum kembali ke kelas, semua siswa menyiram tanaman secukupnya.\n\n"
            "Mereka berbagi temuan dan membandingkan catatan dengan teman. "
            "Lani ingin merawat tanaman tomat bersama kelompoknya setiap minggu. "
            "Bu Rina meminta setiap kelompok menyampaikan pelajaran yang didapat.\n\n"
            "Lani menjelaskan bahwa tanaman membutuhkan air dan perhatian sesuai. "
            "Teman-temannya menyarankan untuk mencatat tinggi tanaman secara teratur. "
            "Kegiatan itu membuat mereka lebih teliti dan kompak.\n\n"
            "Mereka menyimpan buku pengamatan di rak kelas. "
            "Pada pertemuan berikutnya, setiap kelompok akan membagikan catatannya. "
            "Lani ingin mengetahui tanaman mana yang tumbuh paling cepat."
        ),
        "grade": 3,
        "complexity": 3,
        "book_level": "B3",
        "theme": "Sekolah",
        "proper_nouns": ["Lani", "Bu Rina"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Tanaman apa yang dipilih Lani untuk diamati?",
             "options": [{"id": "a", "text": "Tanaman tomat"}, {"id": "b", "text": "Tanaman cabai"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa siswa membandingkan hasil pengamatan dari minggu ke minggu?",
             "options": [{"id": "a", "text": "Untuk mengganti tanaman yang rusak"}, {"id": "b", "text": "Untuk mengetahui perubahan pertumbuhan tanaman"}], "answer_id": "b"},
            {"id": "q3", "competency": "reflect", "prompt": "Tanaman apa yang ingin kamu amati dan bagaimana mencatat perkembangannya?",
             "options": [{"id": "a", "text": "Mengamati tanaman lalu mencatat tinggi dan jumlah daunnya"}, {"id": "b", "text": "Mengamati tanaman sekali saja tanpa catatan"}], "answer_id": "a"},
        ],
    },
    {
        "id": SEED_IDS["reading_8"],
        "title": "Dompet yang Ditemukan",
        "content": (
            "Raka menemukan dompet di dekat gerbang sekolah saat pulang. "
            "Ia mencari kartu nama pemilik tanpa mengambil uang di dalam. "
            "Lalu, Raka menyerahkan dompet itu kepada Pak Dedi.\n\n"
            "Pak Dedi memeriksa kartu perpustakaan dan memanggil pemiliknya. "
            "Fajar datang dengan wajah cemas tidak lama kemudian. "
            "Ia kehilangan dompet saat turun dari kendaraan pagi tadi.\n\n"
            "Fajar memeriksa isi dompet dan memastikan semuanya masih lengkap. "
            "Ia berterima kasih kepada Raka karena sudah menolongnya. "
            "Pak Dedi memuji keputusan Raka yang jujur dan bertanggung jawab.\n\n"
            "Beberapa hari kemudian, sekolah mengadakan kegiatan tentang kejujuran. "
            "Pak Dedi meminta siswa berbagi pengalaman menemukan barang. "
            "Raka menceritakan kejadian itu kepada seluruh kelas.\n\n"
            "Ia menjelaskan bahwa dirinya meminta bantuan orang dewasa. "
            "Teman-temannya mendengarkan cerita Raka dengan saksama. "
            "Seorang siswa bertanya apakah barang temuan boleh disimpan.\n\n"
            "Pak Dedi menjelaskan bahwa barang itu tetap milik orang lain. "
            "Siswa sebaiknya menyerahkannya kepada guru atau petugas sekolah. "
            "Raka senang karena kejadian itu menjadi pelajaran bagi kelas.\n\n"
            "Guru mengingatkan semua siswa agar menjaga barang pribadi. "
            "Fajar kemudian menyimpan dompetnya di tempat yang aman. "
            "Raka merasa lega karena pemilik dompet telah menemukannya kembali."
        ),
        "grade": 3,
        "complexity": 3,
        "book_level": "B3",
        "theme": "Sekolah",
        "proper_nouns": ["Raka", "Pak Dedi", "Fajar"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Kepada siapa Raka menyerahkan dompet yang ditemukan?",
             "options": [{"id": "a", "text": "Fajar"}, {"id": "b", "text": "Pak Dedi"}], "answer_id": "b"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa Pak Dedi memakai pengalaman Raka dalam kegiatan kelas?",
             "options": [{"id": "a", "text": "Agar siswa belajar tentang kejujuran dan tanggung jawab"}, {"id": "b", "text": "Agar Raka mendapat hadiah dari sekolah"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Apa yang kamu lakukan jika menemukan barang milik orang lain?",
             "options": [{"id": "a", "text": "Menyerahkannya kepada guru atau petugas"}, {"id": "b", "text": "Menyimpannya untuk diri sendiri"}], "answer_id": "a"},
        ],
    },
    {
        "id": SEED_IDS["reading_9"],
        "title": "Kompos dari Daun Kering",
        "content": (
            "Di desa Naya, warga sering membakar daun kering setelah membersihkan halaman. "
            "Suatu hari, asap dari beberapa rumah membuat udara tidak nyaman. "
            "Naya bertanya kepada kakeknya tentang cara lain mengolah daun.\n\n"
            "Kakek mengajak Naya mengumpulkan daun di sudut kebun. "
            "Mereka mencampurnya dengan sisa sayuran dan sedikit tanah. "
            "Kakek menjelaskan bahwa campuran itu dapat berubah menjadi kompos.\n\n"
            "Naya membantu mengumpulkan bahan organik setiap sore. "
            "Mereka menaruh campuran di tempat khusus agar tidak berserakan. "
            "Kakek mengingatkan Naya untuk mengaduk campuran sesekali.\n\n"
            "Naya mencatat perubahan warna dan tekstur daun di buku kecil. "
            "Beberapa minggu kemudian, daun berubah menjadi kompos gelap dan rapuh. "
            "Warga memakai kompos untuk menyuburkan tanaman di halaman.\n\n"
            "Naya senang karena kebiasaan baru membuat udara lebih nyaman. "
            "Kakek mengajak Naya menjelaskan cara membuat kompos kepada tetangga. "
            "Naya menunjukkan bahan yang digunakan dan menjelaskan manfaatnya.\n\n"
            "Beberapa warga tertarik mencoba cara itu di rumah. "
            "Mereka sepakat mengolah daun jika caranya aman dan memungkinkan. "
            "Sejak itu, Naya dan kakeknya terus merawat tempat kompos.\n\n"
            "Mereka menggunakan hasilnya untuk tanaman sayur dan bunga. "
            "Naya belajar bahwa kebiasaan kecil dapat membantu lingkungan."
        ),
        "grade": 3,
        "complexity": 3,
        "book_level": "B3",
        "theme": "Alam",
        "proper_nouns": ["Naya"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Bahan apa yang dicampurkan dengan daun kering?",
             "options": [{"id": "a", "text": "Sisa sayuran dan sedikit tanah"}, {"id": "b", "text": "Plastik dan pecahan kaca"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Mengapa warga mulai mengolah daun menjadi kompos?",
             "options": [{"id": "a", "text": "Untuk menambah asap di desa"}, {"id": "b", "text": "Untuk memanfaatkan sampah organik dan mengurangi asap"}], "answer_id": "b"},
            {"id": "q3", "competency": "reflect", "prompt": "Apa yang dapat dilakukan di rumah untuk mengurangi sampah organik?",
             "options": [{"id": "a", "text": "Mengolah sisa sayuran menjadi kompos"}, {"id": "b", "text": "Membakar semua sampah setiap hari"}], "answer_id": "a"},
        ],
    },
]
