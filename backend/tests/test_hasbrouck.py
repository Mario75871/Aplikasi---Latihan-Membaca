"""Test Hasbrouck–Tindal reference (F-11, D9)."""
from services.hasbrouck import DISCLAIMER, get_percentile_position


def test_grade2_spring_between_p25_p50():
    """Contoh PRD: Kelas 2 akhir tahun P25=72 P50=100, WCPM 85 → antara."""
    result = get_percentile_position(2, "spring", 85)
    assert result["available"] is True
    assert result["position"] == "Antara P25 dan P50"
    assert result["p25"] == 72
    assert result["p50"] == 100


def test_below_p25():
    result = get_percentile_position(2, "fall", 30)
    assert result["position"] == "Di bawah P25"


def test_above_p50():
    result = get_percentile_position(2, "fall", 60)
    assert result["position"] == "Di atas P50"


def test_grade1_fall_unavailable():
    """Kelas 1 awal tahun tidak ada norma."""
    result = get_percentile_position(1, "fall", 20)
    assert result["available"] is False


def test_disclaimer_always_present():
    """Disclaimer wajib ada di semua respons."""
    for grade in [1, 2, 3]:
        for season in ["fall", "winter", "spring"]:
            result = get_percentile_position(grade, season, 50)
            assert result["disclaimer"] == DISCLAIMER


def test_todo_verify_flag():
    """Tabel perlu verifikasi (D9)."""
    result = get_percentile_position(2, "fall", 50)
    assert result["todo_verify"] is True


def test_all_table_cells():
    """Semua sel tabel P25/P50 ada."""
    expected = {
        (1, "winter"): (16, 29), (1, "spring"): (34, 60),
        (2, "fall"): (36, 50), (2, "winter"): (59, 84), (2, "spring"): (72, 100),
        (3, "fall"): (59, 83), (3, "winter"): (79, 97), (3, "spring"): (91, 112),
    }
    for (grade, season), (p25, p50) in expected.items():
        result = get_percentile_position(grade, season, 50)
        assert result["p25"] == p25
        assert result["p50"] == p50
