/**
 * @file test_can.cpp
 * @brief Tests d'intégration SocketCAN (nécessite vcan0 UP).
 *
 * Ces tests envoient et reçoivent de vraies trames sur vcan0.
 * Prérequis : `bash scripts/setup_vcan.sh` doit avoir été lancé.
 */

#include <gtest/gtest.h>

#include <array>
#include <chrono>
#include <thread>

#include "decision/can_rx.hpp"
#include "decision/can_tx.hpp"

using adas::decision::can_rx::CanReceiver;
using adas::decision::can_rx::CanFrame;
using adas::decision::can_tx::CanSender;

namespace {
constexpr const char* IFACE = "vcan0";
constexpr std::uint32_t TEST_ID = 0x123U;
}

// ===========================================================================
// Tests d'ouverture
// ===========================================================================

TEST(CanSocket, ReceiverOpensOnVcan0) {
    ASSERT_NO_THROW({
        CanReceiver rx(IFACE, TEST_ID);
        EXPECT_TRUE(rx.is_open());
    });
}

TEST(CanSocket, SenderOpensOnVcan0) {
    ASSERT_NO_THROW({
        CanSender tx(IFACE);
        EXPECT_TRUE(tx.is_open());
    });
}

TEST(CanSocket, ReceiverFailsOnInvalidInterface) {
    EXPECT_THROW(CanReceiver rx("nonexistent0", TEST_ID), std::runtime_error);
}

// ===========================================================================
// Tests d'émission / réception
// ===========================================================================

TEST(CanSocket, SendAndReceiveFrame) {
    CanReceiver rx(IFACE, TEST_ID);
    CanSender   tx(IFACE);

    const std::array<std::uint8_t, 4> payload = {0xDE, 0xAD, 0xBE, 0xEF};

    // Envoyer
    ASSERT_TRUE(tx.send(TEST_ID, payload));

    // Recevoir avec timeout 500 ms
    CanFrame frame{};
    const bool got = rx.receive(500, frame);

    ASSERT_TRUE(got) << "Aucune trame reçue dans les 500 ms";
    EXPECT_EQ(frame.arbitration_id, TEST_ID);
    EXPECT_EQ(frame.dlc, 4U);
    EXPECT_EQ(frame.data[0], 0xDE);
    EXPECT_EQ(frame.data[1], 0xAD);
    EXPECT_EQ(frame.data[2], 0xBE);
    EXPECT_EQ(frame.data[3], 0xEF);
}

TEST(CanSocket, ReceiveTimesOutWhenNothingSent) {
    CanReceiver rx(IFACE, 0x7FFU);  // ID improbable

    CanFrame frame{};
    const bool got = rx.receive(200, frame);  // 200 ms timeout

    EXPECT_FALSE(got) << "Ne devrait rien recevoir sur un ID isolé";
}

TEST(CanSocket, SendMultipleFrames) {
    CanReceiver rx(IFACE, TEST_ID);
    CanSender   tx(IFACE);

    const std::array<std::uint8_t, 8> payload = {
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08
    };

    for (int i = 0; i < 3; ++i) {
        ASSERT_TRUE(tx.send(TEST_ID, payload));
    }

    // On doit pouvoir recevoir au moins 3 trames
    int received = 0;
    for (int i = 0; i < 5; ++i) {
        CanFrame frame{};
        if (rx.receive(200, frame)) {
            EXPECT_EQ(frame.arbitration_id, TEST_ID);
            EXPECT_EQ(frame.dlc, 8U);
            ++received;
            if (received >= 3) break;
        }
    }
    EXPECT_GE(received, 3);
}

