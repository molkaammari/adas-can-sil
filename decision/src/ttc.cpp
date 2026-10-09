/**
 * @file ttc.cpp
 * @brief Implémentation du calcul TTC et de l'estimation de vitesse relative.
 */

#include "decision/ttc.hpp"

#include <cmath>

namespace adas {
namespace decision {
namespace ttc {

// ---------------------------------------------------------------------------
// compute_ttc
// ---------------------------------------------------------------------------

double compute_ttc(double distance_m, double rel_speed_mps) noexcept {
    if (distance_m <= 0.0) {
        return TTC_INFINITY_S;
    }

    // On considère |v_rel| pour que le TTC soit toujours positif
    const double abs_v = std::fabs(rel_speed_mps);

    if (abs_v < REL_SPEED_EPSILON_MPS) {
        return TTC_INFINITY_S;
    }

    return distance_m / abs_v;
}

// ---------------------------------------------------------------------------
// TimeSeriesEstimator
// ---------------------------------------------------------------------------

TimeSeriesEstimator::TimeSeriesEstimator(std::size_t window) noexcept
    : window_(window > 1U ? window : 2U),
      samples_() {
    // Rien d'autre
}

void TimeSeriesEstimator::push(double distance_m, double timestamp_s) noexcept {
    samples_.push_back(Sample{distance_m, timestamp_s});

    while (samples_.size() > window_) {
        samples_.pop_front();
    }
}

void TimeSeriesEstimator::clear() noexcept {
    samples_.clear();
}

std::size_t TimeSeriesEstimator::size() const noexcept {
    return samples_.size();
}

double TimeSeriesEstimator::estimate_rel_speed() const noexcept {
    const std::size_t n = samples_.size();
    if (n < 2U) {
        return 0.0;
    }

    // Régression linéaire : d = a*t + b
    // On veut 'a' (pente) = vitesse relative (négatif = rapprochement)

    double sum_t  = 0.0;
    double sum_d  = 0.0;
    double sum_tt = 0.0;
    double sum_td = 0.0;

    for (const auto& s : samples_) {
        sum_t  += s.timestamp_s;
        sum_d  += s.distance_m;
        sum_tt += s.timestamp_s * s.timestamp_s;
        sum_td += s.timestamp_s * s.distance_m;
    }

    const double n_d = static_cast<double>(n);
    const double denom = n_d * sum_tt - sum_t * sum_t;

    // Dénominateur ~0 → timestamps identiques → pas de pente exploitable
    if (std::fabs(denom) < 1e-9) {
        return 0.0;
    }

    const double slope = (n_d * sum_td - sum_t * sum_d) / denom;
    return slope;
}

}  // namespace ttc
}  // namespace decision
}  // namespace adas

