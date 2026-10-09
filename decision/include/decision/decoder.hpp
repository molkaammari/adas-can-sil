/**
 * @file decoder.hpp
 * @brief Décodage manuel des trames CAN pour l'ECU Decision.
 *
 * Décodage bas niveau des trames (sans cantools) :
 *  - PERC_OBJECT (0x100) — 8 octets, little-endian
 *
 * Principe : extraction directe des champs par masques et décalages.
 *
 * Références : REQ-DEC-001, REQ-CAN-002, REQ-CAN-004
 */

#pragma once

#include <cstddef>
#include <cstdint>

#include "decision/types.hpp"

namespace adas {
namespace decision {
namespace decoder {

// ---------------------------------------------------------------------------
// Constantes DBC
// ---------------------------------------------------------------------------

/// ID CAN du message PERC_OBJECT (0x100)
constexpr std::uint32_t CAN_ID_PERC_OBJECT = 0x100U;

/// DLC attendu pour PERC_OBJECT
constexpr std::size_t DLC_PERC_OBJECT = 8U;

/// Facteurs d'échelle (issus du DBC)
constexpr double FACTOR_DIST_M      = 0.01;
constexpr double FACTOR_REL_SPEED   = 0.01;
constexpr double OFFSET_REL_SPEED   = -100.0;
constexpr double FACTOR_TTC_S       = 0.01;

// ---------------------------------------------------------------------------
// Décodage
// ---------------------------------------------------------------------------

/**
 * Décode une trame PERC_OBJECT (8 octets) en PerceivedObject.
 *
 * @param data  Pointeur vers le payload (au moins 8 octets)
 * @param len   Taille du payload
 * @param out   Structure de sortie (écrite si Status::OK)
 * @return      Status::OK en cas de succès, sinon un code d'erreur.
 */
[[nodiscard]] Status decode_perc_object(const std::uint8_t* data,
                                        std::size_t len,
                                        PerceivedObject& out) noexcept;

}  // namespace decoder
}  // namespace decision
}  // namespace adas

