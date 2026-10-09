/**
 * @file can_rx.cpp
 * @brief Implémentation SocketCAN RX.
 */

#include "decision/can_rx.hpp"

#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <string>
#include <utility>

#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

namespace adas {
namespace decision {
namespace can_rx {

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

namespace {

int open_can_socket(const std::string& ifname, std::uint32_t filter_id) {
    // 1. Créer le socket CAN RAW
    const int fd = ::socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (fd < 0) {
        throw std::runtime_error(
            std::string("socket(PF_CAN) échoué : ") + std::strerror(errno));
    }

    // 2. Résoudre l'index de l'interface (ex: vcan0 → ifindex)
    struct ifreq ifr {};
    std::strncpy(ifr.ifr_name, ifname.c_str(), IFNAMSIZ - 1);
    if (::ioctl(fd, SIOCGIFINDEX, &ifr) < 0) {
        const std::string err = std::strerror(errno);
        ::close(fd);
        throw std::runtime_error(
            "ioctl(SIOCGIFINDEX) échoué pour '" + ifname + "' : " + err +
            " (l'interface est-elle UP ? avez-vous lancé setup_vcan.sh ?)");
    }

    // 3. Bind
    struct sockaddr_can addr {};
    addr.can_family  = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (::bind(fd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) < 0) {
        const std::string err = std::strerror(errno);
        ::close(fd);
        throw std::runtime_error(
            "bind(CAN) échoué sur '" + ifname + "' : " + err);
    }

    // 4. Filtre optionnel sur l'ID
    if (filter_id != 0U) {
        struct can_filter filter {};
        filter.can_id   = filter_id;
        filter.can_mask = CAN_SFF_MASK;  // match exact sur 11 bits
        if (::setsockopt(fd, SOL_CAN_RAW, CAN_RAW_FILTER,
                         &filter, sizeof(filter)) < 0) {
            const std::string err = std::strerror(errno);
            ::close(fd);
            throw std::runtime_error(
                "setsockopt(CAN_RAW_FILTER) échoué : " + err);
        }
    }

    return fd;
}

}  // namespace

// ---------------------------------------------------------------------------
// CanReceiver
// ---------------------------------------------------------------------------

CanReceiver::CanReceiver(const std::string& ifname, std::uint32_t filter_id)
    : fd_(-1), ifname_(ifname), filter_id_(filter_id) {
    fd_ = open_can_socket(ifname, filter_id);
}

CanReceiver::~CanReceiver() {
    close();
}

CanReceiver::CanReceiver(CanReceiver&& other) noexcept
    : fd_(other.fd_), ifname_(std::move(other.ifname_)),
      filter_id_(other.filter_id_) {
    other.fd_ = -1;
}

CanReceiver& CanReceiver::operator=(CanReceiver&& other) noexcept {
    if (this != &other) {
        close();
        fd_ = other.fd_;
        ifname_ = std::move(other.ifname_);
        filter_id_ = other.filter_id_;
        other.fd_ = -1;
    }
    return *this;
}

void CanReceiver::close() noexcept {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

bool CanReceiver::receive(int timeout_ms, CanFrame& out) noexcept {
    if (fd_ < 0) {
        return false;
    }

    // Configurer le timeout si demandé
    if (timeout_ms > 0) {
        struct timeval tv {};
        tv.tv_sec  = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        (void)::setsockopt(fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    } else if (timeout_ms == 0) {
        // Timeout infini : désactiver
        struct timeval tv {};
        tv.tv_sec  = 0;
        tv.tv_usec = 0;
        (void)::setsockopt(fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    }

    struct can_frame raw_frame {};
    const ssize_t n = ::read(fd_, &raw_frame, sizeof(raw_frame));

    if (n < 0) {
        // Timeout (EAGAIN/EWOULDBLOCK) ou erreur
        return false;
    }

    if (n != static_cast<ssize_t>(sizeof(struct can_frame))) {
        // Trame incomplète
        return false;
    }

    out.arbitration_id = raw_frame.can_id & CAN_SFF_MASK;
    out.dlc = raw_frame.can_dlc > MAX_CAN_DLC
                  ? static_cast<std::uint8_t>(MAX_CAN_DLC)
                  : raw_frame.can_dlc;

    for (std::size_t i = 0; i < MAX_CAN_DLC; ++i) {
        out.data[i] = raw_frame.data[i];
    }

    return true;
}

}  // namespace can_rx
}  // namespace decision
}  // namespace adas

