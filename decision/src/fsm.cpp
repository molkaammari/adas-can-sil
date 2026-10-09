/**
 * @file fsm.cpp
 * @brief Implémentation de la machine à états.
 */

#include "decision/fsm.hpp"
#include "decision/ttc.hpp"

#include <cmath>

namespace adas {
namespace decision {
namespace fsm {

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const char* to_string(State s) noexcept {
    switch (s) {
        case State::OFF:      return "OFF";
        case State::STANDBY:  return "STANDBY";
        case State::WARNING:  return "WARNING";
        case State::BRAKE:    return "BRAKE";
        case State::FAULT:    return "FAULT";
    }
    return "UNKNOWN";
}

AlertLevel state_to_alert(State s) noexcept {
    switch (s) {
        case State::OFF:      return AlertLevel::OFF;
        case State::STANDBY:  return AlertLevel::STANDBY;
        case State::WARNING:  return AlertLevel::WARNING;
        case State::BRAKE:    return AlertLevel::BRAKE;
        case State::FAULT:    return AlertLevel::FAULT;
    }
    return AlertLevel::FAULT;
}

// ---------------------------------------------------------------------------
// Fsm
// ---------------------------------------------------------------------------

void Fsm::reset() noexcept {
    state_ = State::OFF;
    last_valid_frame_s_ = -1.0;
    last_state_change_s_ = -1.0;
}

void Fsm::transition_to(State new_state, const char* reason,
                        double timestamp_s) noexcept {
    state_ = new_state;
    last_state_change_s_ = timestamp_s;
    // 'reason' pourrait être loggé ici (pour l'instant non utilisé)
    (void)reason;
}

FsmOutput Fsm::update(const PerceivedObject& obj, double timestamp_s) noexcept {
    FsmOutput out{};
    const State prev = state_;

    // ----- Détection de FAULT (objet invalide ou données incohérentes) -----
    if (!obj.valid) {
        if (state_ != State::FAULT) {
            transition_to(State::FAULT, "invalid_object", timestamp_s);
        }
        out.state = state_;
        out.alert = state_to_alert(state_);
        out.ttc_s = 0.0;
        out.state_changed = (prev != state_);
        out.reason = "invalid_object";
        return out;
    }

    // ----- Mise à jour du timestamp de dernière trame valide -----
    last_valid_frame_s_ = timestamp_s;

    // ----- Calcul du TTC -----
    const double ttc = ttc::compute_ttc(obj.distance_m, obj.rel_speed_mps);

    // ----- Sortie de FAULT si on reçoit une trame valide -----
    if (state_ == State::FAULT) {
        transition_to(State::STANDBY, "recovery", timestamp_s);
    }

    // ----- État initial -----
    if (state_ == State::OFF) {
        transition_to(State::STANDBY, "init", timestamp_s);
    }

    // ----- Transitions selon TTC -----
    if (ttc < ttc::TTC_BRAKE_S) {
        if (state_ != State::BRAKE) {
            transition_to(State::BRAKE, "ttc_brake", timestamp_s);
        }
    } else if (ttc < ttc::TTC_WARNING_S) {
        // Hystérésis : ne redescend de BRAKE que si TTC > TTC_BRAKE + HYST
        const bool can_leave_brake =
            (state_ != State::BRAKE) ||
            (ttc > ttc::TTC_BRAKE_S + HYSTERESIS_S);

        if (state_ != State::WARNING && can_leave_brake) {
            transition_to(State::WARNING, "ttc_warning", timestamp_s);
        }
    } else {
        // TTC au-dessus des seuils
        // Hystérésis : ne redescend de WARNING que si TTC > TTC_WARNING + HYST
        const bool can_leave_warning =
            (state_ != State::WARNING) ||
            (ttc > ttc::TTC_WARNING_S + HYSTERESIS_S);

        if (state_ != State::STANDBY && can_leave_warning) {
            transition_to(State::STANDBY, "ttc_safe", timestamp_s);
        }
    }

    // ----- Sortie -----
    out.state = state_;
    out.alert = state_to_alert(state_);
    out.ttc_s = (ttc >= ttc::TTC_INFINITY_S) ? 0.0 : ttc;
    out.state_changed = (prev != state_);
    out.reason = out.state_changed ? "transition" : "stable";
    return out;
}

FsmOutput Fsm::tick(double timestamp_s) noexcept {
    FsmOutput out{};
    const State prev = state_;

    // Si aucune trame valide depuis PERCEPTION_TIMEOUT_S → FAULT
    if (state_ != State::OFF && state_ != State::FAULT) {
        if (last_valid_frame_s_ > 0.0) {
            const double elapsed = timestamp_s - last_valid_frame_s_;
            if (elapsed > PERCEPTION_TIMEOUT_S) {
                transition_to(State::FAULT, "perception_timeout", timestamp_s);
            }
        }
    }
    
    
    
    

    // Auto-recovery depuis FAULT après FAULT_RECOVERY_S
   // if (state_ == State::FAULT &&
    //    (timestamp_s - last_state_change_s_) > FAULT_RECOVERY_S) {
    //    transition_to(State::STANDBY, "auto_recovery", timestamp_s);
   // }
    
     // Pas d'auto-recovery : on reste en FAULT jusqu'à une nouvelle
    // trame valide (voir Fsm::update()). C'est plus sûr en ADAS.
    
    

    out.state = state_;
    out.alert = state_to_alert(state_);
    out.ttc_s = 0.0;
    out.state_changed = (prev != state_);
    out.reason = out.state_changed ? "tick_transition" : "tick_stable";
    return out;
}

}  // namespace fsm
}  // namespace decision
}  // namespace adas

