/**
 * @file can_rx.hpp
 * @brief Réception SocketCAN (Linux natif) pour l'ECU Decision.
 *
 * Ouvre un socket CAN en mode RAW et filtre sur un ID donné.
 * Fournit une API simple : open(), receive(), close().
 *
 * Références : REQ-CAN-001, REQ-DEC-001
 */

#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace adas {
namespace decision {
namespace can_rx {

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

constexpr std::size_t MAX_CAN_DLC = 8U;

// ---------------------------------------------------------------------------
// Structures
// ---------------------------------------------------------------------------

struct CanFrame {
    std::uint32_t arbitration_id{0};
    std::uint8_t  dlc{0};
    std::uint8_t  data[MAX_CAN_DLC]{};
};

// ---------------------------------------------------------------------------
// Récepteur CAN
// ---------------------------------------------------------------------------

class CanReceiver {
public:
    /**
     * Ouvre un socket CAN sur l'interface donnée.
     *
     * @param ifname     Interface (ex: "vcan0")
     * @param filter_id  ID CAN à filtrer (0 = pas de filtre)
     * @throws std::runtime_error si l'ouverture échoue
     */
    CanReceiver(const std::string& ifname, std::uint32_t filter_id = 0);

    /// Destructeur : ferme le socket automatiquement.
    ~CanReceiver();

    // Pas de copie
    CanReceiver(const CanReceiver&) = delete;
    CanReceiver& operator=(const CanReceiver&) = delete;

    // Déplacement autorisé
    CanReceiver(CanReceiver&& other) noexcept;
    CanReceiver& operator=(CanReceiver&& other) noexcept;

    /**
     * Reçoit une trame CAN (bloquant).
     *
     * @param timeout_ms  Timeout en millisecondes (0 = infini)
     * @param out         Trame reçue (valide si retourne true)
     * @return            true si une trame a été reçue, false en cas de timeout
     */
    [[nodiscard]] bool receive(int timeout_ms, CanFrame& out) noexcept;

    /// Retourne le descripteur de fichier (pour debug / poll externe).
    [[nodiscard]] int fd() const noexcept { return fd_; }

    /// Indique si le socket est ouvert.
    [[nodiscard]] bool is_open() const noexcept { return fd_ >= 0; }

    /// Ferme le socket.
    void close() noexcept;

private:
    int fd_{-1};
    std::string ifname_;
    std::uint32_t filter_id_;
};

}  // namespace can_rx
}  // namespace decision
}  // namespace adas

