/**
 * @file decoder.cpp
 * @brief Implémentation du décodage PERC_OBJECT.
 */

#include "decision/decoder.hpp"

namespace adas {
namespace decision {
namespace decoder {

namespace {

/// Lit un uint16 little-endian depuis un buffer d'octets.
inline std::uint16_t read_u16_le(const std::uint8_t* p) noexcept {
    return static_cast<std::uint16_t>(
        static_cast<std::uint16_t>(p[0]) |
        (static_cast<std::uint16_t>(p[1]) << 8U)
    );
}

}  // namespace

Status decode_perc_object(const std::uint8_t* data,
                          std::size_t len,
                          PerceivedObject& out) noexcept {
    if (data == nullptr) {
        return Status::ERROR_INVALID_DATA;
    }

    if (len < DLC_PERC_OBJECT) {
        return Status::ERROR_DECODE;
    }

    // ----- obj_id (octet 0) -----
    out.obj_id = data[0];

    // ----- dist_m (octets 1-2, LE, facteur 0.01) -----
    const std::uint16_t raw_dist = read_u16_le(&data[1]);
    out.distance_m = static_cast<double>(raw_dist) * FACTOR_DIST_M;

    // ----- rel_speed_mps (octets 3-4, LE, facteur 0.01, offset -100) -----
    const std::uint16_t raw_speed = read_u16_le(&data[3]);
    out.rel_speed_mps =
        static_cast<double>(raw_speed) * FACTOR_REL_SPEED + OFFSET_REL_SPEED;

    // ----- ttc_s (octets 5-6, LE, facteur 0.01) -----
    const std::uint16_t raw_ttc = read_u16_le(&data[5]);
    out.ttc_s = static_cast<double>(raw_ttc) * FACTOR_TTC_S;

    // ----- valid (bit 0 de l'octet 7) -----
    out.valid = (data[7] & 0x01U) != 0U;

    return Status::OK;
}

}  // namespace decoder
}  // namespace decision
}  // namespace adas

