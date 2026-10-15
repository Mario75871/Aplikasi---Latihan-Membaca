"""Seed data teks bacaan BacaLaras (F-04, v2.5).

Level 1–3 dipetakan ke jenjang B1–B3 (Perka BSKAP 030/P/2022).
Batas:
- Level 1 (B1): maks 7 kata/kalimat, maks 5 kalimat/halaman, target 25-35 kata
- Level 2 (B2): maks 9 kata/kalimat, maks 7 kalimat/halaman, target 45-63 kata
- Level 3 (B3): maks 12 kata/kalimat, maks 3 paragraf/halaman, maks 3 kalimat/paragraf,
  target 80-108 kata

Teks ditulis dengan ejaan baku dan tanda baca sederhana (sumber target_text framework).
"""
from __future__ import annotations

# Struktur: setiap teks punya id, title, content, grade, complexity, book_level,
# theme, proper_nouns, questions (3-5, label retrieve/interpret/reflect)

READING_TEXTS = [
    # ========== LEVEL 1 (B1) ==========
    {
        "id": "rd-001",
        "title": "Si Kucing Putih",
        "content": (
            "Kucing putih itu suka bermain di halaman. "
            "Ia minum susu setiap pagi bersama adik. "
            "Aku menyayangi kucing putih itu. "
            "Aku memberinya makan setiap hari. "
            "Ia tidur dekat jendela kamarku."
        ),
        "grade": 1,
        "complexity": 1,
        "book_level": "B1",
        "theme": "Hewan",
        "proper_nouns": [],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa warna kucing itu?",
             "options": [{"id": "a", "text": "Putih"}, {"id": "b", "text": "Hitam"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Apa yang diminum kucing setiap pagi?",
             "options": [{"id": "a", "text": "Susu"}, {"id": "b", "text": "Air kopi"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Di mana kucing itu tidur?",
             "options": [{"id": "a", "text": "Dekat jendela"}, {"id": "b", "text": "Di dapur"}], "answer_id": "a"},
        ],
    },
    {
        "id": "rd-002",
        "title": "Main Bola",
        "content": (
            "Aku bermain bola di lapangan dekat rumah. "
            "Rani dan Budi ikut bermain bersama. "
            "Kami bermain sampai matahari terbenam. "
            "Kami pulang dengan hati gembira. "
            "Besok kami akan bermain lagi."
        ),
        "grade": 1,
        "complexity": 1,
        "book_level": "B1",
        "theme": "Bermain",
        "proper_nouns": ["Rani", "Budi"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa yang dimainkan anak itu?",
             "options": [{"id": "a", "text": "Bola"}, {"id": "b", "text": "Kelereng"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Siapa yang ikut bermain bersama?",
             "options": [{"id": "a", "text": "Rani dan Budi"}, {"id": "b", "text": "Guru"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Bagaimana perasaan mereka saat pulang?",
             "options": [{"id": "a", "text": "Gembira"}, {"id": "b", "text": "Sedih"}], "answer_id": "a"},
        ],
    },
    {
        "id": "rd-003",
        "title": "Pagi di Rumah",
        "content": (
            "Matahari mulai terbit di ufuk timur. "
            "Ayah membaca koran di ruang tamu. "
            "Ibu menyiapkan sarapan di dapur. "
            "Aku membantu ibu menata meja makan. "
            "Kami sarapan bersama dengan gembira."
        ),
        "grade": 1,
        "complexity": 1,
        "book_level": "B1",
        "theme": "Keluarga",
        "proper_nouns": [],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa yang dibaca Ayah?",
             "options": [{"id": "a", "text": "Koran"}, {"id": "b", "text": "Buku cerita"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Apa yang disiapkan Ibu?",
             "options": [{"id": "a", "text": "Sarapan"}, {"id": "b", "text": "Pakaian"}], "answer_id": "a"},
            {"id": "q3", "competency": "reflect", "prompt": "Bagaimana suasana pagi itu?",
             "options": [{"id": "a", "text": "Gembira"}, {"id": "b", "text": "Sedih"}], "answer_id": "a"},
        ],
    },
    # ========== LEVEL 2 (B2) ==========
    {
        "id": "rd-004",
        "title": "Ke Pasar Bersama Ibu",
        "content": (
            "Ibu pergi ke pasar setiap pagi hari Minggu. "
            "Aku ikut membantu ibu membawa keranjang. "
            "Di pasar banyak pedagang menjual sayur segar. "
            "Ibu membeli bayam, wortel, dan tomat merah. "
            "Aku juga membeli buah jeruk kesukaanku. "
            "Kami pulang dengan keranjang yang penuh. "
            "Aku merasa senang bisa membantu ibu."
        ),
        "grade": 2,
        "complexity": 2,
        "book_level": "B2",
        "theme": "Keluarga",
        "proper_nouns": [],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Kapan Ibu pergi ke pasar?",
             "options": [{"id": "a", "text": "Setiap pagi Minggu"}, {"id": "b", "text": "Setiap malam"}], "answer_id": "a"},
            {"id": "q2", "competency": "retrieve", "prompt": "Apa yang dibawa anak itu?",
             "options": [{"id": "a", "text": "Keranjang"}, {"id": "b", "text": "Tas sekolah"}], "answer_id": "a"},
            {"id": "q3", "competency": "interpret", "prompt": "Apa yang dibeli Ibu di pasar?",
             "options": [{"id": "a", "text": "Bayam, wortel, dan tomat"}, {"id": "b", "text": "Buku dan pensil"}], "answer_id": "a"},
            {"id": "q4", "competency": "reflect", "prompt": "Mengapa anak itu merasa senang?",
             "options": [{"id": "a", "text": "Bisa membantu ibu"}, {"id": "b", "text": "Mendapat hadiah"}], "answer_id": "a"},
        ],
    },
    {
        "id": "rd-005",
        "title": "Kebun Pak Tani",
        "content": (
            "Pak Tani memiliki kebun sayur yang sangat luas. "
            "Setiap hari ia merawat tanamannya dengan sabar. "
            "Ia menyiram tanaman pada pagi dan sore. "
            "Tanaman tumbuh subur berkat perawatannya. "
            "Banyak tetangga membeli sayur dari kebunnya. "
            "Pak Tani bekerja keras setiap hari tanpa lelah. "
            "Ia bangga dengan hasil kerjanya sendiri."
        ),
        "grade": 2,
        "complexity": 2,
        "book_level": "B2",
        "theme": "Pekerjaan",
        "proper_nouns": ["Pak Tani"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa yang dimiliki Pak Tani?",
             "options": [{"id": "a", "text": "Kebun sayur"}, {"id": "b", "text": "Toko buku"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Kapan Pak Tani menyiram tanaman?",
             "options": [{"id": "a", "text": "Pagi dan sore"}, {"id": "b", "text": "Siang saja"}], "answer_id": "a"},
            {"id": "q3", "competency": "interpret", "prompt": "Mengapa tanaman tumbuh subur?",
             "options": [{"id": "a", "text": "Karena dirawat dengan sabar"}, {"id": "b", "text": "Karena dibiarkan saja"}], "answer_id": "a"},
            {"id": "q4", "competency": "reflect", "prompt": "Apa yang membuat Pak Tani bangga?",
             "options": [{"id": "a", "text": "Hasil kerjanya sendiri"}, {"id": "b", "text": "Hadiah dari tetangga"}], "answer_id": "a"},
        ],
    },
    {
        "id": "rd-006",
        "title": "Hujan di Sekolah",
        "content": (
            "Pagi ini hujan turun sangat deras. "
            "Aku dan Rani berteduh di serambi kelas. "
            "Kami melihat air hujan jatuh dari langit. "
            "Bu Guru menyuruh kami masuk ke kelas. "
            "Kami belajar sambil mendengar suara hujan. "
            "Saat hujan berhenti kami bermain di luar. "
            "Hari itu menjadi hari yang menyenangkan."
        ),
        "grade": 2,
        "complexity": 2,
        "book_level": "B2",
        "theme": "Sekolah",
        "proper_nouns": ["Rani"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Bagaimana hujan pagi itu?",
             "options": [{"id": "a", "text": "Sangat deras"}, {"id": "b", "text": "Gerimis"}], "answer_id": "a"},
            {"id": "q2", "competency": "interpret", "prompt": "Di mana mereka berteduh?",
             "options": [{"id": "a", "text": "Di serambi kelas"}, {"id": "b", "text": "Di kantin"}], "answer_id": "a"},
            {"id": "q3", "competency": "interpret", "prompt": "Apa yang dilakukan Bu Guru?",
             "options": [{"id": "a", "text": "Menyuruh masuk kelas"}, {"id": "b", "text": "Menyuruh pulang"}], "answer_id": "a"},
            {"id": "q4", "competency": "reflect", "prompt": "Bagaimana perasaan anak-anak hari itu?",
             "options": [{"id": "a", "text": "Menyenangkan"}, {"id": "b", "text": "Menakutkan"}], "answer_id": "a"},
        ],
    },
    # ========== LEVEL 3 (B3) ==========
    {
        "id": "rd-007",
        "title": "Lomba Lari di Sekolah",
        "content": (
            "SD Harapan mengadakan lomba lari pada hari Sabtu pagi yang cerah sekali. "
            "Semua siswa berkumpul di lapangan sekolah sejak pagi buta. "
            "Bu Guru membagi peserta lomba menjadi beberapa kelompok kecil saja.\n\n"
            "Boni mengikuti lomba lari untuk kelas tiga sekolahnya hari itu. "
            "Ia berlatih setiap sore bersama ayahnya di lapangan dekat rumah. "
            "Boni ingin menjadi juara pertama pada tahun ini dengan bangga.\n\n"
            "Peluit tanda mulai dibunyikan oleh Pak Guru segera setelah itu. "
            "Boni berlari sangat cepat mengikuti lintasan lomba yang panjang itu. "
            "Akhirnya Boni menjadi juara pertama dan merasa senang sekali hatinya."
        ),
        "grade": 3,
        "complexity": 3,
        "book_level": "B3",
        "theme": "Sekolah",
        "proper_nouns": ["Boni", "SD Harapan"],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Kapan lomba lari diadakan?",
             "options": [{"id": "a", "text": "Hari Sabtu pagi"}, {"id": "b", "text": "Hari Minggu sore"}], "answer_id": "a"},
            {"id": "q2", "competency": "retrieve", "prompt": "Untuk kelas berapa Boni mengikuti lomba?",
             "options": [{"id": "a", "text": "Kelas tiga"}, {"id": "b", "text": "Kelas satu"}], "answer_id": "a"},
            {"id": "q3", "competency": "interpret", "prompt": "Siapa yang berlatih bersama Boni?",
             "options": [{"id": "a", "text": "Ayahnya"}, {"id": "b", "text": "Gurunya"}], "answer_id": "a"},
            {"id": "q4", "competency": "interpret", "prompt": "Apa tanda lomba dimulai?",
             "options": [{"id": "a", "text": "Peluit dibunyikan"}, {"id": "b", "text": "Bel sekolah"}], "answer_id": "a"},
            {"id": "q5", "competency": "reflect", "prompt": "Apa yang dirasakan Boni setelah menang?",
             "options": [{"id": "a", "text": "Senang sekali"}, {"id": "b", "text": "Kecewa"}], "answer_id": "a"},
        ],
    },
    {
        "id": "rd-008",
        "title": "Membantu Ibu di Dapur",
        "content": (
            "Hari Minggu pagi aku membantu ibu memasak di dapur rumah. "
            "Ibu mengajarkan cara memotong sayuran dengan benar dan rapi sekali. "
            "Aku memotong wortel dan kentang dengan hati-hati sekali ya.\n\n"
            "Setelah itu ibu menumis bumbu hingga beraroma harum sekali. "
            "Aroma masakan menyebar ke seluruh ruangan rumah kami bersama. "
            "Ayah dan adik menunggu dengan sabar di meja makan besar itu.\n\n"
            "Akhirnya masakan matang dan siap untuk segera disajikan bersama. "
            "Kami makan bersama sambil bercerita tentang hari itu dengan riang. "
            "Aku senang bisa belajar memasak bersama ibu hari ini sekali."
        ),
        "grade": 3,
        "complexity": 3,
        "book_level": "B3",
        "theme": "Keluarga",
        "proper_nouns": [],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Apa yang dilakukan anak itu pada hari Minggu?",
             "options": [{"id": "a", "text": "Membantu ibu memasak"}, {"id": "b", "text": "Bermain bola"}], "answer_id": "a"},
            {"id": "q2", "competency": "retrieve", "prompt": "Sayuran apa yang dipotong?",
             "options": [{"id": "a", "text": "Wortel dan kentang"}, {"id": "b", "text": "Bayam dan kangkung"}], "answer_id": "a"},
            {"id": "q3", "competency": "interpret", "prompt": "Apa yang membuat aroma harum?",
             "options": [{"id": "a", "text": "Bumbu yang ditumis"}, {"id": "b", "text": "Nasi yang matang"}], "answer_id": "a"},
            {"id": "q4", "competency": "interpret", "prompt": "Siapa yang menunggu di meja makan?",
             "options": [{"id": "a", "text": "Ayah dan adik"}, {"id": "b", "text": "Tetangga"}], "answer_id": "a"},
            {"id": "q5", "competency": "reflect", "prompt": "Bagaimana perasaan anak itu?",
             "options": [{"id": "a", "text": "Senang bisa belajar"}, {"id": "b", "text": "Lelah sekali"}], "answer_id": "a"},
        ],
    },
    {
        "id": "rd-009",
        "title": "Menanam Pohon",
        "content": (
            "Pada hari Minggu pagi kami menanam pohon di halaman rumah. "
            "Ayah membeli bibit pohon mangga di pasar dekat rumah kami. "
            "Aku menyiapkan lubang dan tanah untuk menanamnya bersama ayah.\n\n"
            "Ibu membantu menyiram bibit dengan air secukupnya setiap hari. "
            "Kami menunggu pohon itu tumbuh besar dan berbuah manis sekali. "
            "Setiap hari aku menyiramnya dengan penuh semangat yang tinggi.\n\n"
            "Beberapa tahun kemudian pohon itu berbuah sangat lebat dan manis. "
            "Kami memetik buah mangga dan membaginya bersama tetangga dekat rumah. "
            "Menanam pohon membuat lingkungan menjadi lebih hijau dan segar."
        ),
        "grade": 3,
        "complexity": 3,
        "book_level": "B3",
        "theme": "Alam",
        "proper_nouns": [],
        "questions": [
            {"id": "q1", "competency": "retrieve", "prompt": "Pohon apa yang ditanam?",
             "options": [{"id": "a", "text": "Pohon mangga"}, {"id": "b", "text": "Pohon rambutan"}], "answer_id": "a"},
            {"id": "q2", "competency": "retrieve", "prompt": "Siapa yang membeli bibit pohon?",
             "options": [{"id": "a", "text": "Ayah"}, {"id": "b", "text": "Ibu"}], "answer_id": "a"},
            {"id": "q3", "competency": "interpret", "prompt": "Apa yang dilakukan Ibu?",
             "options": [{"id": "a", "text": "Menyiram bibit"}, {"id": "b", "text": "Memetik buah"}], "answer_id": "a"},
            {"id": "q4", "competency": "interpret", "prompt": "Apa yang dilakukan setelah pohon berbuah?",
             "options": [{"id": "a", "text": "Memetik dan membagi buah"}, {"id": "b", "text": "Menebang pohon"}], "answer_id": "a"},
            {"id": "q5", "competency": "reflect", "prompt": "Apa manfaat menanam pohon menurut teks?",
             "options": [{"id": "a", "text": "Lingkungan lebih hijau"}, {"id": "b", "text": "Rumah lebih besar"}], "answer_id": "a"},
        ],
    },
]
