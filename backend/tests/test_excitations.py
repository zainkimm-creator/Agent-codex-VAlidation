import pytest

from backend.excitation.generators import generate_et3m_operating_points, tension_reference_delta
from backend.excitation.profiles import SkippedExcitationError, get_profile, is_skipped_exact


T_REF = (10.0, 20.0, 30.0)


def test_et1_timing_correct():
    profile = get_profile("ET1")

    assert profile.total_duration_s == 7.0
    assert tension_reference_delta("ET1", 1.999, T_REF) == (0.0, 0.0, 0.0)
    assert tension_reference_delta("ET1", 2.0, T_REF) == (2.0, 0.0, 0.0)
    assert tension_reference_delta("ET1", 6.999, T_REF) == (2.0, 0.0, 0.0)


def test_et3_timing_correct():
    profile = get_profile("ET3")

    assert profile.total_duration_s == 17.0
    assert tension_reference_delta("ET3", 1.999, T_REF) == (0.0, 0.0, 0.0)
    assert tension_reference_delta("ET3", 2.0, T_REF) == (2.0, 0.0, 0.0)
    assert tension_reference_delta("ET3", 7.0, T_REF) == (2.0, 4.0, 0.0)
    assert tension_reference_delta("ET3", 12.0, T_REF) == (2.0, 4.0, 6.0)


def test_et6_windows_correct():
    profile = get_profile("ET6")

    assert profile.total_duration_s == 32.0
    assert tension_reference_delta("ET6", 1.999, T_REF) == (0.0, 0.0, 0.0)
    assert tension_reference_delta("ET6", 2.0, T_REF) == (2.0, 0.0, 0.0)
    assert tension_reference_delta("ET6", 7.0, T_REF) == (2.0, 4.0, 0.0)
    assert tension_reference_delta("ET6", 12.0, T_REF) == (2.0, 4.0, 6.0)
    assert tension_reference_delta("ET6", 17.0, T_REF) == (0.0, 4.0, 6.0)
    assert tension_reference_delta("ET6", 22.0, T_REF) == (0.0, 0.0, 6.0)
    assert tension_reference_delta("ET6", 27.0, T_REF) == (0.0, 0.0, 0.0)
    assert tension_reference_delta("ET6", 31.999, T_REF) == (0.0, 0.0, 0.0)


def test_et3m_returns_three_operating_points():
    points = generate_et3m_operating_points(3.0)

    assert [point.profile_name for point in points] == ["ET3", "ET3", "ET3"]
    assert [point.line_speed_multiplier for point in points] == [0.5, 1.0, 2.0]
    assert [point.v_ref_mps for point in points] == [1.5, 3.0, 6.0]


def test_ev1_and_evr_skipped_in_exact_mode():
    assert is_skipped_exact("EV1") is True
    assert is_skipped_exact("EVR") is True

    with pytest.raises(SkippedExcitationError):
        get_profile("EV1", exact_mode=True)
    with pytest.raises(SkippedExcitationError):
        get_profile("EVR", exact_mode=True)
