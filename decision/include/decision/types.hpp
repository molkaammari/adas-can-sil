/**
 * @file types.hpp
 * @brief Structures de données partagées de l'ECU Decision.
 *
 * Contient :
 *  - PerceivedObject : objet reçu depuis PERC_OBJECT (0x100)
 *  - AlertLevel      : niveaux d'alerte (FSM)
 *  - DecisionOutput  : sortie de l'ECU (à émettre dans DEC_ALERT)
 *  - Result          : type de retour pour la gestion d'erreurs
 */

#pragma once

#include <cstdint>
#include <string>

namespace adas {
namespace decision {

// ---------------------------------------------------------------------------
// Niveaux d'alerte (correspondent au DBC DEC_ALERT/alert_level)
// ---------------------------------------------------------------------------

enum class AlertLevel : std::uint8_t {
    OFF      = 0,
    STANDBY  = 1,
    WARNING  = 2,
    BRAKE    = 3,
    FAULT    = 4,
};

/// Retourne le nom lisible d'un AlertLevel (pour les logs).
inline const char* to_string(AlertLevel level) noexcept {
    switch (level) {
        case AlertLevel::OFF:     return "OFF";
        case AlertLevel::STANDBY: return "STANDBY";
        case AlertLevel::WARNING: return "WARNING";
        case AlertLevel::BRAKE:   return "BRAKE";
        case AlertLevel::FAULT:   return "FAULT";
    }
    return "UNKNOWN";
}

// ---------------------------------------------------------------------------
// Objet perçu (décodé depuis PERC_OBJECT 0x100)
// ---------------------------------------------------------------------------

struct PerceivedObject {
    std::uint8_t  obj_id{0};
    double        distance_m{0.0};      ///< Distance à l'objet (m)
    double        rel_speed_mps{0.0};   ///< Vitesse relative (m/s, négatif = rapprochement)
    double        ttc_s{0.0};           ///< Time-To-Collision (s)
    bool          valid{false};         ///< Flag de validité

    /// Retourne true si les champs sont cohérents pour un calcul TTC.
    [[nodiscard]] bool is_usable() const noexcept {
        return valid && distance_m > 0.0;
    }
};

// ---------------------------------------------------------------------------
// Sortie de décision (à encoder dans DEC_ALERT 0x200)
// ---------------------------------------------------------------------------

struct DecisionOutput {
    AlertLevel    level{AlertLevel::OFF};
    double        ttc_s{0.0};
    std::uint8_t  counter{0};   ///< Compteur E2E 4 bits
    std::uint8_t  crc{0};       ///< CRC8 E2E
};

// ---------------------------------------------------------------------------
// Résultat d'opération (pour éviter les exceptions en embarqué)
// ---------------------------------------------------------------------------

enum class Status : std::uint8_t {
    OK = 0,
    ERROR_DECODE,
    ERROR_ENCODE,
    ERROR_TIMEOUT,
    ERROR_INVALID_DATA,
    ERROR_CAN,
};

inline const char* to_string(Status s) noexcept {
    switch (s) {
        case Status::OK:                  return "OK";
        case Status::ERROR_DECODE:        return "ERROR_DECODE";
        case Status::ERROR_ENCODE:        return "ERROR_ENCODE";
        case Status::ERROR_TIMEOUT:       return "ERROR_TIMEOUT";
        case Status::ERROR_INVALID_DATA:  return "ERROR_INVALID_DATA";
        case Status::ERROR_CAN:           return "ERROR_CAN";
    }
    return "UNKNOWN";
}

}  // namespace decision
}  // namespace adas
