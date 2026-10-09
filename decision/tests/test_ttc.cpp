/**
 * @file test_ttc.cpp
 * @brief Tests unitaires pour le calcul TTC et l'estimation de vitesse relative.
 */

#include <gtest/gtest.h>

#include <cmath>

#include "decision/ttc.hpp"

using adas::decision::ttc::compute_ttc;
using adas::decision::ttc::TimeSeriesEstimator;
using adas::decision::ttc::TTC_INFINITY_S;

// ===========================================================================
// compute_ttc
// ===========================================================================

TEST(TtcCompute, SimpleCase) {
    // 25 m à -5 m/s → TTC = 5 s
    EXPECT_NEAR(compute_ttc(25.0, -5.0), 5.0, 1e-9);
}

TEST(TtcCompute, PositiveRelSpeed) {
    // Valeur absolue : |v_rel| est utilisé
    EXPECT_NEAR(compute_ttc(30.0, 6.0), 5.0, 1e-9);
}

TEST(TtcCompute, DistanceZeroReturnsInfinity) {
    EXPECT_EQ(compute_ttc(0.0, -5.0), TTC_INFINITY_S);
}

TEST(TtcCompute, DistanceNegativeReturnsInfinity) {
    EXPECT_EQ(compute_ttc(-3.0, -5.0), TTC_INFINITY_S);
}

TEST(TtcCompute, RelSpeedNearZeroReturnsInfinity) {
    // v_rel < eps → pas de collision prévue
    EXPECT_EQ(compute_ttc(50.0, 0.0), TTC_INFINITY_S);
    EXPECT_EQ(compute_ttc(50.0, 0.05), TTC_INFINITY_S);
}

TEST(TtcCompute, RelSpeedAtEpsilon) {
    // Juste au-dessus du seuil
    const double ttc = compute_ttc(1.0, 0.2);
    EXPECT_NEAR(ttc, 5.0, 1e-9);
}

// ===========================================================================
// TimeSeriesEstimator — base
// ===========================================================================

TEST(TimeSeriesEstimator, EmptyBufferReturnsZero) {
    TimeSeriesEstimator est;
    EXPECT_EQ(est.size(), 0U);
    EXPECT_DOUBLE_EQ(est.estimate_rel_speed(), 0.0);
}

TEST(TimeSeriesEstimator, SingleSampleReturnsZero) {
    TimeSeriesEstimator est;
    est.push(25.0, 1.0);
    EXPECT_EQ(est.size(), 1U);
    EXPECT_DOUBLE_EQ(est.estimate_rel_speed(), 0.0);
}

TEST(TimeSeriesEstimator, TwoSamplesLinear) {
    // d(t) = 25 - 5*t  →  v_rel = -5 m/s
    TimeSeriesEstimator est;
    est.push(25.0, 0.00);  // d(0) = 25
    est.push(24.5, 0.10);  // d(0.1) = 24.5

    // Pente attendue : (24.5 - 25) / (0.1 - 0) = -5.0 m/s
    EXPECT_NEAR(est.estimate_rel_speed(), -5.0, 1e-6);
}

TEST(TimeSeriesEstimator, FullWindowLinear) {
    // Régression sur 5 points, pente = -5 m/s
    TimeSeriesEstimator est;
    for (int i = 0; i < 5; ++i) {
        const double t = 0.1 * static_cast<double>(i);
        const double d = 25.0 - 5.0 * t;
        est.push(d, t);
    }
    EXPECT_NEAR(est.estimate_rel_speed(), -5.0, 1e-6);
}

TEST(TimeSeriesEstimator, SlidingWindowDropsOldSamples) {
    TimeSeriesEstimator est(3U);
    est.push(30.0, 0.0);
    est.push(29.0, 0.1);
    est.push(28.0, 0.2);
    est.push(27.0, 0.3);  // Doit faire tomber (30.0, 0.0)

    EXPECT_EQ(est.size(), 3U);
}

TEST(TimeSeriesEstimator, ClearResetsBuffer) {
    TimeSeriesEstimator est;
    est.push(25.0, 0.0);
    est.push(24.0, 0.1);
    EXPECT_EQ(est.size(), 2U);

    est.clear();
    EXPECT_EQ(est.size(), 0U);
    EXPECT_DOUBLE_EQ(est.estimate_rel_speed(), 0.0);
}

// ===========================================================================
// TimeSeriesEstimator — cas dégénérés
// ===========================================================================

TEST(TimeSeriesEstimator, IdenticalTimestampsReturnsZero) {
    // Tous les timestamps identiques → dénominateur nul → 0.0
    TimeSeriesEstimator est;
    est.push(25.0, 1.0);
    est.push(24.0, 1.0);
    est.push(23.0, 1.0);

    EXPECT_DOUBLE_EQ(est.estimate_rel_speed(), 0.0);
}

TEST(TimeSeriesEstimator, NegativeSlopeForApproach) {
    // Rapprochement → vitesse relative négative
    TimeSeriesEstimator est;
    est.push(50.0, 0.0);
    est.push(45.0, 0.5);  // v = (45-50)/0.5 = -10 m/s

    EXPECT_LT(est.estimate_rel_speed(), 0.0);
    EXPECT_NEAR(est.estimate_rel_speed(), -10.0, 1e-6);
}

// ===========================================================================
// Intégration TTC + Estimator
// ===========================================================================

TEST(TtcIntegration, EstimatorFeedsTtc) {
    // Scénario : véhicule ego à 25 m, qui se rapproche de -5 m/s
    TimeSeriesEstimator est;
    est.push(25.0, 0.0);
    est.push(24.5, 0.1);

    const double v_rel = est.estimate_rel_speed();
    const double distance = 24.5;
    const double ttc = compute_ttc(distance, v_rel);

    // TTC ≈ 24.5 / 5.0 = 4.9 s
    EXPECT_NEAR(ttc, 4.9, 1e-3);
}

