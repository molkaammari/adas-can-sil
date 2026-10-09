/**
 * @file fsm.hpp
 * @brief Machine à états de l'ECU Decision.
 *
 * États :
 *   OFF      : sortie d'usine, pas de traitement
 *   STANDBY  : trame reçue mais pas d'alerte
 *   WARNING  : TTC < 2.0 s → alerte visuelle
 *   BRAKE    : TTC < 1.2 s → freinage d'urgence
 *   FAULT    : timeout, CRC KO, ou erreur de décodage
 *
 * Transitions principales :
 *   OFF → STANDBY         : première trame valide
 *   STANDBY → WARNING     : TTC < 2.0 s
 *   WARNING → BRAKE       : TTC < 1.2 s
 *   BRAKE → WARNING       : TTC remonte > 1.5 s (hystérésis)
 *   WARNING → STANDBY     : TTC remonte > 2.5 s (hystérésis)
 *   * → FAULT             : timeout > 100 ms, CRC KO, counter figé
 *   FAULT → STANDBY       : reset manuel ou 500 ms sans faute
 *
 * Références : REQ-DEC-005, REQ-E2E-003, REQ-E2E-004
 */

#pragma once

#include <cstdint>
#include <optional>

#include "decision/types.hpp"

namespace adas {
namespace decision {
namespace fsm {

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

/// Timeout de trame perception (ms) — REQ-E2E-004
constexpr double PERCEPTION_TIMEOUT_S = 0.100;

/// Durée après laquelle on sort de FAULT automatiquement (s)
constexpr double FAULT_RECOVERY_S = 0.500;

/// Hystérésis (s) pour éviter les oscillations WARNING ↔ BRAKE ↔ STANDBY
constexpr double HYSTERESIS_S = 0.500;

// ---------------------------------------------------------------------------
// États
// ---------------------------------------------------------------------------

/// État interne de la FSM (différent de AlertLevel — plus fin).
enum class State : std::uint8_t {
    OFF      = 0,
    STANDBY  = 1,
    WARNING  = 2,
    BRAKE    = 3,
    FAULT    = 4,
};

const char* to_string(State s) noexcept;

/// Convertit un State en AlertLevel (pour l'émission DEC_ALERT).
AlertLevel state_to_alert(State s) noexcept;

// ---------------------------------------------------------------------------
// Résultat d'un cycle FSM
// ---------------------------------------------------------------------------

struct FsmOutput {
    State       state{State::OFF};
    AlertLevel  alert{AlertLevel::OFF};
    double      ttc_s{0.0};
    bool        state_changed{false};
    const char* reason{"init"};
};

// ---------------------------------------------------------------------------
// Machine à états
// ---------------------------------------------------------------------------

class Fsm {
public:
    Fsm() noexcept = default;

    /**
     * Traite un nouvel objet perçu.
     *
     * @param obj         Objet décodé (peut être invalide)
     * @param timestamp_s Timestamp actuel (secondes monotones)
     * @return            Sortie FSM (état, alerte, TTC)
     */
    [[nodiscard]] FsmOutput update(const PerceivedObject& obj,
                                   double timestamp_s) noexcept;

    /**
     * Traite un tick sans nouvel objet (timeout detection).
     */
    [[nodiscard]] FsmOutput tick(double timestamp_s) noexcept;

    /// Retourne l'état courant.
    [[nodiscard]] State state() const noexcept { return state_; }

    /// Force un reset vers OFF.
    void reset() noexcept;

private:
    void transition_to(State new_state, const char* reason,
                       double timestamp_s) noexcept;

    State  state_{State::OFF};
    double last_valid_frame_s_{-1.0};  ///< Timestamp dernière trame valide
    double last_state_change_s_{-1.0}; ///< Timestamp dernier changement d'état
};

}  // namespace fsm
}  // namespace decision
}  // namespace adas

