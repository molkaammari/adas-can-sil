/**
 * @file encoder.hpp
 * @brief Encodage des trames CAN émises par l'ECU Decision.
 *
 * Encode les messages :
 *  - DEC_ALERT (0x200) — 4 octets, alerte + TTC + CRC + compteur
 *  - DEC_HB    (0x201) — 2 octets, heartbeat (alive_ctr + state)
 *
 * Références : REQ-DEC-006, REQ-DEC-007, REQ-E2E-001
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "decision/types.hpp"

namespace adas {
namespace decision {
namespace encoder {

// ---------------------------------------------------------------------------
// Constantes DBC
// ---------------------------------------------------------------------------

constexpr std::uint32_t CAN_ID_DEC_ALERT = 0x200U;
constexpr std::uint32_t CAN_ID_DEC_HB    = 0x201U;

constexpr std::size_t DLC_DEC_ALERT = 4U;
constexpr std::size_t DLC_DEC_HB    = 2U;

// Facteurs d'échelle
constexpr double FACTOR_DEC_TTC = 0.01;  // ttc_s → centisecondes

// ---------------------------------------------------------------------------
// Types de sortie
// ---------------------------------------------------------------------------

/// Payload d'une trame DEC_ALERT (4 octets).
using DecAlertPayload = std::array<std::uint8_t, DLC_DEC_ALERT>;

/// Payload d'une trame DEC_HB (2 octets).
using DecHbPayload = std::array<std::uint8_t, DLC_DEC_HB>;

// ---------------------------------------------------------------------------
// Encodage
// ---------------------------------------------------------------------------

/**
 * Encode une trame DEC_ALERT (0x200).
 *
 * @param out  Sortie : payload 4 octets.
 * @param level  Niveau d'alerte (0..4)
 * @param ttc_s  TTC en secondes (0..40.95)
 * @param counter  Compteur E2E (0..15)
 * @param crc      CRC8 E2E (0..255)
 * @return  Status::OK ou Status::ERROR_ENCODE si valeur hors plage.
 */
[[nodiscard]] Status encode_dec_alert(DecAlertPayload& out,
                                      AlertLevel level,
                                      double ttc_s,
                                      std::uint8_t counter,
                                      std::uint8_t crc) noexcept;

/**
 * Encode une trame DEC_HB (0x201).
 *
 * @param out  Sortie : payload 2 octets.
 * @param alive_ctr  Compteur vivant (0..255)
 * @param state      État FSM (0..4, cf. AlertLevel)
 * @return  Status::OK
 */
[[nodiscard]] Status encode_dec_hb(DecHbPayload& out,
                                   std::uint8_t alive_ctr,
                                   AlertLevel state) noexcept;

}  // namespace encoder
}  // namespace decision
}  // namespace adas

