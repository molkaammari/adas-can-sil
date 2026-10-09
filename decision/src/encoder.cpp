/**
 * @file encoder.cpp
 * @brief Implémentation de l'encodage DEC_ALERT et DEC_HB.
 */

#include "decision/encoder.hpp"

#include <cmath>

namespace adas {
namespace decision {
namespace encoder {

namespace {

/// Écrit un uint16 little-endian dans un buffer.
inline void write_u16_le(std::uint8_t* p, std::uint16_t v) noexcept {
    p[0] = static_cast<std::uint8_t>(v & 0xFFU);
    p[1] = static_cast<std::uint8_t>((v >> 8U) & 0xFFU);
}

}  // namespace

// ---------------------------------------------------------------------------
// DEC_ALERT (0x200)
// ---------------------------------------------------------------------------

Status encode_dec_alert(DecAlertPayload& out,
                        AlertLevel level,
                        double ttc_s,
                        std::uint8_t counter,
                        std::uint8_t crc) noexcept {
    // ----- Validation -----
    const std::uint8_t level_u8 = static_cast<std::uint8_t>(level);
    if (level_u8 > 4U) {
        return Status::ERROR_ENCODE;
    }

    if (counter > 15U) {
        return Status::ERROR_ENCODE;
    }

    if (ttc_s < 0.0 || ttc_s > 40.95) {
        return Status::ERROR_ENCODE;
    }

    // ----- Encodage -----
    // ttc_s → uint16 en centisecondes (pour stocker les 12 bits utiles)
    const std::uint16_t ttc_raw = static_cast<std::uint16_t>(
        std::lround(ttc_s / FACTOR_DEC_TTC)
    );

    out[0] = 0x00U;
    out[1] = 0x00U;
    out[2] = 0x00U;
    out[3] = 0x00U;

    // bits 0-3 : alert_level
    out[0] = static_cast<std::uint8_t>(level_u8 & 0x0FU);

    // bits 4-15 : ttc_s (12 bits)
    //   bits 4-7  → octet 0 (haut)
    //   bits 8-15 → octet 1 (bas)
    out[0] |= static_cast<std::uint8_t>((ttc_raw & 0x000FU) << 4U);
    out[1]  = static_cast<std::uint8_t>((ttc_raw >> 4U) & 0xFFU);

    // bits 16-19 : counter (octet 2, bits bas)
    out[2] = static_cast<std::uint8_t>(counter & 0x0FU);

    // bits 24-31 : crc (octet 3)
    out[3] = crc;

    return Status::OK;
}

// ---------------------------------------------------------------------------
// DEC_HB (0x201)
// ---------------------------------------------------------------------------

Status encode_dec_hb(DecHbPayload& out,
                     std::uint8_t alive_ctr,
                     AlertLevel state) noexcept {
    const std::uint8_t state_u8 = static_cast<std::uint8_t>(state);
    if (state_u8 > 4U) {
        return Status::ERROR_ENCODE;
    }

    out[0] = alive_ctr;
    out[1] = state_u8;

    return Status::OK;
}

}  // namespace encoder
}  // namespace decision
}  // namespace adas

