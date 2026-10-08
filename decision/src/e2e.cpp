/**
 * @file e2e.cpp
 * @brief Implémentation CRC8 + compteur E2E.
 */

#include "decision/e2e.hpp"

namespace adas {
namespace decision {
namespace e2e {

// ---------------------------------------------------------------------------
// CRC8
// ---------------------------------------------------------------------------

std::uint8_t crc8(const std::uint8_t* data, std::size_t len) noexcept {
    if (data == nullptr || len == 0U) {
        return 0U;
    }

    std::uint8_t crc = CRC8_INIT;

    for (std::size_t i = 0U; i < len; ++i) {
        crc ^= data[i];

        for (int bit = 0; bit < 8; ++bit) {
            if ((crc & 0x80U) != 0U) {
                crc = static_cast<std::uint8_t>((crc << 1U) ^ CRC8_POLY);
            } else {
                crc = static_cast<std::uint8_t>(crc << 1U);
            }
        }
    }

    return static_cast<std::uint8_t>(crc ^ CRC8_XOROUT);
}

// ---------------------------------------------------------------------------
// Compteur 4 bits
// ---------------------------------------------------------------------------

std::uint8_t next_counter(std::uint8_t counter) noexcept {
    return static_cast<std::uint8_t>((counter + 1U) & COUNTER_MAX);
}

}  // namespace e2e
}  // namespace decision
}  // namespace adas

