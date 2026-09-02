from validation.analyse_phase2_confirmation_failure import (
    maximum_passing_exceedances_binary,
    maximum_true_rate_for_power,
)


def test_frozen_5000_sample_boundary_is_reproduced():
    assert maximum_passing_exceedances_binary(
        samples=5000,
        target_fpr=0.01,
        alpha=0.05 / 60,
    ) == 28


def test_fresh_study_margin_increases_with_sample_size():
    margins = []
    for samples in (5000, 10000, 20000, 50000):
        maximum = maximum_passing_exceedances_binary(
            samples=samples,
            target_fpr=0.01,
            alpha=0.05 / 60,
        )
        margins.append(
            maximum_true_rate_for_power(
                samples=samples,
                maximum_exceedances=maximum,
                target_power=1 - 0.05 / 60,
            )
        )
    assert margins == sorted(margins)
    assert 0.0029 < margins[0] < 0.0031
    assert 0.0073 < margins[-1] < 0.0075

