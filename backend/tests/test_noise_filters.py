import numpy as np

from backend.noise.filters import apply_configured_lpf, first_order_lpf, load_lpf_cutoff_hz
from backend.noise.sensor_noise import (
    add_noise_to_measurements,
    configured_tlog_ms,
    generate_tension_noise,
    sigma_for_plant,
)


def test_sigma_values_match_tmax_fraction():
    assert sigma_for_plant("P01") == 0.003 * 40.0
    assert sigma_for_plant("P02") == 0.003 * 216.0
    assert sigma_for_plant("P08") == 0.003 * 3060.0
    assert sigma_for_plant("P10") == 0.003 * 1200.0


def test_seed_zero_is_reproducible():
    tensions = np.ones((5, 3)) * 12.0

    first = generate_tension_noise(tensions, "P01")
    second = generate_tension_noise(tensions, "P01")

    assert np.array_equal(first, second)


def test_noise_shape_matches_tension_data():
    tensions = np.zeros((7, 3))

    noise = generate_tension_noise(tensions, "P03")

    assert noise.shape == tensions.shape


def test_lpf_preserves_shape_and_uses_100hz_config():
    noisy_tensions = np.array(
        [
            [1.0, 2.0, 3.0],
            [1.5, 2.5, 3.5],
            [1.2, 2.2, 3.2],
        ]
    )

    filtered = apply_configured_lpf(noisy_tensions, sample_time_s=0.001)

    assert load_lpf_cutoff_hz() == 100.0
    assert filtered.shape == noisy_tensions.shape
    assert first_order_lpf(noisy_tensions, sample_time_s=0.001, cutoff_hz=100.0).shape == noisy_tensions.shape


def test_no_noise_added_to_torque_and_tlog_config_values():
    tensions = np.ones((4, 3)) * 12.0
    torques = np.array(
        [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
            [1.0, 1.1, 1.2],
        ]
    )

    noisy_tensions, unchanged_torques = add_noise_to_measurements(tensions, torques, "P01")

    assert noisy_tensions.shape == tensions.shape
    assert np.array_equal(unchanged_torques, torques)
    assert configured_tlog_ms(noise_enabled=True) == 20
    assert configured_tlog_ms(noise_enabled=False) == 5
