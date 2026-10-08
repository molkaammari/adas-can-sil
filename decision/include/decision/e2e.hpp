/**
 * @file e2e.hpp
 * @brief Protection End-to-End (E2E) des trames DEC_ALERT.
 *
 * Implémente :
 *  - CRC8 avec polynôme 0x1D (AUTOSAR E2E Profile 1)
 *  - Compteur 4 bits wrap 15 -> 0
 *
 * Référence : REQ-E2E-001, REQ-E2E-002
 */

#pragma once

#include <cstdint>

namespace adas {
namespace decision {
namespace e2e {

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

/// Polynôme CRC8 (AUTOSAR E2E Profile 1, aussi SAE J1850)
constexpr std::uint8_t CRC8_POLY = 0x1D;

/// Valeur initiale du CRC8
constexpr std::uint8_t CRC8_INIT = 0xFF;

/// XOR final (xorout)
constexpr std::uint8_t CRC8_XOROUT = 0xFF;

/// Nombre maximum du compteur (4 bits → 0..15)
constexpr std::uint8_t COUNTER_MAX = 15;

// ---------------------------------------------------------------------------
// CRC8
// ---------------------------------------------------------------------------

/**
 * Calcule le CRC8 d'un buffer.
 *
 * @param data  Pointeur vers les données
 * @param len   Nombre d'octets
 * @return      CRC8 (poly 0x1D, init 0xFF, xorout 0xFF)
 */
[[nodiscard]] std::uint8_t crc8(const std::uint8_t* data,
                                std::size_t len) noexcept;

/**
 * Surcharge pratique pour un tableau de taille fixe.
 */
template <std::size_t N>
[[nodiscard]] inline std::uint8_t crc8(const std::uint8_t (&data)[N]) noexcept {
    return crc8(data, N);
}

// ---------------------------------------------------------------------------
// Compteur 4 bits
// ---------------------------------------------------------------------------

/**
 * Incrémente un compteur 4 bits avec wrap 15 → 0.
 *
 * @param counter  Valeur courante (0..15)
 * @return         Valeur suivante (0..15)
 */
[[nodiscard]] std::uint8_t next_counter(std::uint8_t counter) noexcept;

}  // namespace e2e
}  // namespace decision
}  // namespace adas
