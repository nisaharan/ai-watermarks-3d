import math

from ai_watermarks_phase2.native import NativePositionTrace, NativeScore
from ai_watermarks_phase2.trace_validation import trace_is_consistent


def test_kgw_trace_reconstructs_score():
    traces = (
        NativePositionTrace(0, 1, (1,), False, "insufficient_context", {"green_hit": None}),
        NativePositionTrace(1, 2, (1, 2), True, None, {"green_hit": True}),
        NativePositionTrace(2, 3, (2, 3), True, None, {"green_hit": False}),
        NativePositionTrace(3, 2, (1, 2), False, "repeated_ngram", {"green_hit": None}),
    )
    expected = (1 - 0.25 * 2) / math.sqrt(2 * 0.25 * 0.75)
    score = NativeScore(
        "kgw",
        "z_score",
        expected,
        2,
        {
            "green_tokens": 1,
            "green_fraction": 0.5,
            "greenlist_ratio": 0.25,
            "window_size": 2,
        },
        traces,
    ).to_dict()
    assert trace_is_consistent(score, 4)


def test_synthid_trace_reconstructs_score():
    traces = (
        NativePositionTrace(0, 1, (1,), False, "insufficient_context", {"g_values": None}),
        NativePositionTrace(1, 2, (1, 2), True, None, {"g_values": [1, 0]}),
        NativePositionTrace(2, 3, (2, 3), True, None, {"g_values": [1, 1]}),
    )
    score = NativeScore(
        "synthid",
        "mean_g_value",
        0.75,
        2,
        {"watermarking_depth": 2, "ngram_len": 2},
        traces,
    ).to_dict()
    assert trace_is_consistent(score, 3)


def test_trace_rejects_inconsistent_eligibility_metadata():
    score = {
        "scheme": "kgw",
        "value": 0.0,
        "eligible_positions": 1,
        "auxiliary": {"green_fraction": 0.0},
        "position_traces": [
            {
                "position": 0,
                "eligible": True,
                "exclusion_reason": "should_be_null",
                "values": {"green_hit": False},
            }
        ],
    }
    assert not trace_is_consistent(score, 1)


def test_zero_eligible_kgw_trace_accepts_native_nan_score():
    score = NativeScore(
        "kgw",
        "z_score",
        float("nan"),
        0,
        {
            "green_tokens": 0,
            "green_fraction": float("nan"),
            "greenlist_ratio": 0.25,
        },
        (
            NativePositionTrace(
                0, 1, (1,), False, "insufficient_context", {"green_hit": None}
            ),
        ),
    ).to_dict()

    assert trace_is_consistent(score, 1)


def test_trace_rejects_corrupted_redundant_audit_fields():
    score = NativeScore(
        "kgw",
        "z_score",
        1.0 / math.sqrt(0.25 * 0.75),
        1,
        {
            "green_tokens": 0,
            "green_fraction": 1.0,
            "greenlist_ratio": 0.25,
        },
        (NativePositionTrace(0, 1, (1,), True, None, {"green_hit": True}),),
    ).to_dict()

    assert not trace_is_consistent(score, 1)


def test_trace_consistency_returns_false_for_malformed_reported_value():
    score = {
        "scheme": "synthid",
        "value": None,
        "eligible_positions": 0,
        "auxiliary": {"watermarking_depth": 2},
        "position_traces": [],
    }

    assert not trace_is_consistent(score, 0)
