/**
 * @file can_tx.hpp
 * @brief Émission SocketCAN (Linux natif) pour l'ECU Decision.
 *
 * Références : REQ-CAN-001, REQ-DEC-006, REQ-DEC-007
 */

#pragma once

#include <cstdint>
#include <string>

#include "decision/can_rx.hpp"  // pour CanFrame

namespace adas {
namespace decision {
namespace can_tx {

// ---------------------------------------------------------------------------
// Émetteur CAN
// ---------------------------------------------------------------------------

class CanSender {
public:
    /**
     * Ouvre un socket CAN en écriture sur l'interface donnée.
     *
     * @param ifname  Interface (ex: "vcan0")
     * @throws std::runtime_error si l'ouverture échoue
     */
    explicit CanSender(const std::string& ifname);

    ~CanSender();

    CanSender(const CanSender&) = delete;
    CanSender& operator=(const CanSender&) = delete;

    CanSender(CanSender&& other) noexcept;
    CanSender& operator=(CanSender&& other) noexcept;

    /**
     * Envoie une trame CAN.
     *
     * @param arbitration_id  ID standard 11 bits (ex: 0x200)
     * @param data            Payload (pointeur)
     * @param dlc             Nombre d'octets (0..8)
     * @return                true si envoyé avec succès
     */
    [[nodiscard]] bool send(std::uint32_t arbitration_id,
                            const std::uint8_t* data,
                            std::uint8_t dlc) noexcept;

    /// Surcharge pratique pour std::array.
    template <std::size_t N>
    [[nodiscard]] bool send(std::uint32_t id,
                            const std::array<std::uint8_t, N>& payload) noexcept {
        return send(id, payload.data(), static_cast<std::uint8_t>(N));
    }

    [[nodiscard]] bool is_open() const noexcept { return fd_ >= 0; }
    void close() noexcept;

private:
    int fd_{-1};
    std::string ifname_;
};

}  // namespace can_tx
}  // namespace decision
}  // namespace adas

