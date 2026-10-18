"""Test Dashboard status mapping (D6, F-10)."""
from services.dashboard import map_dashboard_status


def test_intervene_is_need_support():
    """INTERVENE → Need Support."""
    assert map_dashboard_status("INTERVENE", 85, 90, 90, 90) == "Need Support"


def test_stay_is_developing():
    """STAY tanpa kriteria On Track → Developing."""
    assert map_dashboard_status("STAY", 92, 85, 85, 85) == "Developing"


def test_stay_on_track_high_accuracy_high_comp():
    """STAY + Accuracy ≥95% + semua komp ≥80% → On Track."""
    assert map_dashboard_status("STAY", 96, 85, 85, 85) == "On Track"


def test_stay_developing_if_low_accuracy():
    """STAY + Accuracy <95% → Developing."""
    assert map_dashboard_status("STAY", 94, 85, 85, 85) == "Developing"


def test_stay_developing_if_low_comprehension():
    """STAY + Accuracy ≥95% tapi ada komp <80% → Developing."""
    assert map_dashboard_status("STAY", 96, 75, 85, 85) == "Developing"


def test_promotion_candidate_is_promotion():
    """PROMOTION_CANDIDATE → Promotion."""
    assert map_dashboard_status("PROMOTION_CANDIDATE", 96, 90, 90, 90) == "Promotion"


def test_promote_is_on_track():
    """PROMOTE → On Track."""
    assert map_dashboard_status("PROMOTE", 96, 90, 90, 90) == "On Track"
