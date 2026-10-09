/**
 * @file can_tx.cpp
 * @brief Implémentation SocketCAN TX.
 */

#include "decision/can_tx.hpp"

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
#include <unistd.h>

namespace adas {
namespace decision {
namespace can_tx {

namespace {

int open_can_socket(const std::string& ifname) {
    const int fd = ::socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (fd < 0) {
        throw std::runtime_error(
            std::string("socket(PF_CAN) échoué : ") + std::strerror(errno));
    }

    struct ifreq ifr {};
    std::strncpy(ifr.ifr_name, ifname.c_str(), IFNAMSIZ - 1);
    if (::ioctl(fd, SIOCGIFINDEX, &ifr) < 0) {
        const std::string err = std::strerror(errno);
        ::close(fd);
        throw std::runtime_error(
            "ioctl(SIOCGIFINDEX) échoué pour '" + ifname + "' : " + err);
    }

    struct sockaddr_can addr {};
    addr.can_family  = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (::bind(fd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) < 0) {
        const std::string err = std::strerror(errno);
        ::close(fd);
        throw std::runtime_error("bind(CAN) échoué sur '" + ifname + "' : " + err);
    }

    return fd;
}

}  // namespace

// ---------------------------------------------------------------------------
// CanSender
// ---------------------------------------------------------------------------

CanSender::CanSender(const std::string& ifname)
    : fd_(-1), ifname_(ifname) {
    fd_ = open_can_socket(ifname);
}

CanSender::~CanSender() {
    close();
}

CanSender::CanSender(CanSender&& other) noexcept
    : fd_(other.fd_), ifname_(std::move(other.ifname_)) {
    other.fd_ = -1;
}

CanSender& CanSender::operator=(CanSender&& other) noexcept {
    if (this != &other) {
        close();
        fd_ = other.fd_;
        ifname_ = std::move(other.ifname_);
        other.fd_ = -1;
    }
    return *this;
}

void CanSender::close() noexcept {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

bool CanSender::send(std::uint32_t arbitration_id,
                     const std::uint8_t* data,
                     std::uint8_t dlc) noexcept {
    if (fd_ < 0 || data == nullptr || dlc > 8U) {
        return false;
    }

    struct can_frame frame {};
    frame.can_id  = arbitration_id & CAN_SFF_MASK;
    frame.can_dlc = dlc;

    for (std::uint8_t i = 0; i < dlc; ++i) {
        frame.data[i] = data[i];
    }

    const ssize_t n = ::write(fd_, &frame, sizeof(frame));
    return n == static_cast<ssize_t>(sizeof(frame));
}

}  // namespace can_tx
}  // namespace decision
}  // namespace adas

