/**
 * @file ttc.hpp
 * @brief Calcul du Time-To-Collision (TTC) et de la vitesse relative.
 *
 * Le TTC est l'estimation du temps restant avant collision avec un objet
 * s'il continue sur sa trajectoire actuelle.
 *
 * Formule principale :
 *     TTC = distance / |vitesse_relative|
 *
 * Limites (voir docs/architecture.md) :
 *  - La vitesse relative est bruitée si calculée sur 2 frames seulement
 *  - Un filtrage (moyenne glissante) est nécessaire pour la stabilité
 *  - Si v_rel ≈ 0, le TTC est infini (pas de collision prévue)
 *
 * Références : REQ-DEC-002, REQ-DEC-003, REQ-DEC-004
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>

#include "decision/types.hpp"

namespace adas {
namespace decision {
namespace ttc {

// ---------------------------------------------------------------------------
// Seuils FCW (Forward Collision Warning) — définis dans docs/requirements.md
// ---------------------------------------------------------------------------

/// Seuil d'alerte WARNING (TTC < 2.0 s)
constexpr double TTC_WARNING_S = 2.0;

/// Seuil de freinage d'urgence BRAKE (TTC < 1.2 s)
constexpr double TTC_BRAKE_S = 1.2;

/// Vitesse relative en dessous de laquelle le TTC est considéré infini
constexpr double REL_SPEED_EPSILON_MPS = 0.1;

/// Valeur de TTC considérée comme "infinie" (pas de collision prévue)
constexpr double TTC_INFINITY_S = 1e9;

// ---------------------------------------------------------------------------
// Calcul direct du TTC
// ---------------------------------------------------------------------------

/**
 * Calcule le TTC à partir d'une distance et d'une vitesse relative.
 *
 * @param distance_m      Distance actuelle (m). Doit être > 0.
 * @param rel_speed_mps   Vitesse relative (m/s). Négatif = rapprochement.
 * @return                TTC en secondes, ou TTC_INFINITY_S si pas de
 *                        rapprochement significatif.
 */
[[nodiscard]] double compute_ttc(double distance_m,
                                 double rel_speed_mps) noexcept;

// ---------------------------------------------------------------------------
// Historique temporel (pour dériver v_rel depuis les distances)
// ---------------------------------------------------------------------------

/**
 * Buffer glissant qui estime la vitesse relative à partir de l'historique
 * des distances mesurées.
 *
 * Principe : on stocke les dernières mesures (distance, timestamp) et on
 * calcule la dérivée discrète sur une fenêtre glissante.
 *
 * Exemple :
 *   TimeSeriesEstimator est;
 *   est.push(25.0, 1.00);   // t=1.00 s, d=25 m
 *   est.push(24.5, 1.05);   // t=1.05 s, d=24.5 m
 *   double v = est.estimate_rel_speed();  // ≈ -10 m/s
 */
class TimeSeriesEstimator {
public:
    /// Nombre maximum de points conservés dans le buffer.
    static constexpr std::size_t DEFAULT_WINDOW = 5;

    explicit TimeSeriesEstimator(std::size_t window = DEFAULT_WINDOW) noexcept;

    /**
     * Ajoute un point (distance, timestamp).
     *
     * @param distance_m   Distance mesurée (m)
     * @param timestamp_s  Timestamp en secondes (ex: std::chrono::steady_clock)
     */
    void push(double distance_m, double timestamp_s) noexcept;

    /**
     * Efface tout l'historique (utile après un FAULT, par exemple).
     */
    void clear() noexcept;

    /**
     * Nombre de points actuellement dans le buffer.
     */
    [[nodiscard]] std::size_t size() const noexcept;

    /**
     * Estime la vitesse relative par régression linéaire simple
     * (moindres carrés) sur la fenêtre glissante.
     *
     * @return  Vitesse relative (m/s). Négatif = rapprochement.
     *          Retourne 0.0 si moins de 2 points disponibles.
     */
    [[nodiscard]] double estimate_rel_speed() const noexcept;

private:
    struct Sample {
        double distance_m;
        double timestamp_s;
    };

    std::size_t       window_;
    std::deque<Sample> samples_;
};

}  // namespace ttc
}  // namespace decision
}  // namespace adas

