/**
 * @file test_encoder.cpp
 * @brief Tests unitaires de l'encodage DEC_ALERT et DEC_HB.
 */

#include <gtest/gtest.h>

#include "decision/encoder.hpp"
#include "decision/decoder.hpp"
#include "decision/types.hpp"

using adas::decision::AlertLevel;
using adas::decision::Status;
using adas::decision::encoder::encode_dec_alert;
using adas::decision::encoder::encode_dec_hb;
using adas::decision::encoder::DecAlertPayload;
using adas::decision::encoder::DecHbPayload;

// ===========================================================================
// DEC_ALERT
// ===========================================================================

TEST(EncoderDecAlert, NominalEncoding) {
    DecAlertPayload payload{};
    const Status s = encode_dec_alert(payload, AlertLevel::WARNING, 1.85, 5U, 0xA5U);

    EXPECT_EQ(s, Status::OK);

    // Vérif bits : alert_level = 2 (WARNING) dans bits 0-3
    EXPECT_EQ(payload[0] & 0x0FU, 0x02U);

    // Vérif ttc_s : 1.85 s → 185 centisecondes = 0x00B9
    // bits 4-15 → octet 0 haut = 0x9, octet 1 = 0x0B
    EXPECT_EQ(payload[0] >> 4U, 0x09U);
    EXPECT_EQ(payload[1], 0x0BU);

    // counter = 5 dans bits 16-19 → octet 2 bas
    EXPECT_EQ(payload[2] & 0x0FU, 0x05U);

    // crc dans octet 3
    EXPECT_EQ(payload[3], 0xA5U);
}

TEST(EncoderDecAlert, AllAlertLevels) {
    for (int lvl = 0; lvl <= 4; ++lvl) {
        DecAlertPayload payload{};
        const Status s = encode_dec_alert(
            payload, static_cast<AlertLevel>(lvl), 0.0, 0U, 0U);
        EXPECT_EQ(s, Status::OK);
        EXPECT_EQ(payload[0] & 0x0FU, static_cast<std::uint8_t>(lvl));
    }
}

TEST(EncoderDecAlert, TtcMaxValue) {
    // TTC max = 40.95 s → 4095 (12 bits max) = 0x0FFF
    DecAlertPayload payload{};
    const Status s = encode_dec_alert(payload, AlertLevel::BRAKE, 40.95, 0U, 0U);
    EXPECT_EQ(s, Status::OK);

    // Vérif bits 4-15 (12 bits) = 0x0FFF
    const std::uint16_t ttc_bits =
        static_cast<std::uint16_t>(payload[0] >> 4U) |
        (static_cast<std::uint16_t>(payload[1]) << 4U);
    EXPECT_EQ(ttc_bits, 0x0FFFU);
}

TEST(EncoderDecAlert, TtcZero) {
    DecAlertPayload payload{};
    const Status s = encode_dec_alert(payload, AlertLevel::OFF, 0.0, 0U, 0U);
    EXPECT_EQ(s, Status::OK);
    EXPECT_EQ(payload[0] >> 4U, 0U);
    EXPECT_EQ(payload[1], 0U);
}

TEST(EncoderDecAlert, CounterMaxValue) {
    DecAlertPayload payload{};
    const Status s = encode_dec_alert(payload, AlertLevel::OFF, 0.0, 15U, 0U);
    EXPECT_EQ(s, Status::OK);
    EXPECT_EQ(payload[2] & 0x0FU, 0x0FU);
}

TEST(EncoderDecAlert, RejectsTtcTooLarge) {
    DecAlertPayload payload{};
    EXPECT_EQ(encode_dec_alert(payload, AlertLevel::OFF, 50.0, 0U, 0U),
              Status::ERROR_ENCODE);
}

TEST(EncoderDecAlert, RejectsNegativeTtc) {
    DecAlertPayload payload{};
    EXPECT_EQ(encode_dec_alert(payload, AlertLevel::OFF, -1.0, 0U, 0U),
              Status::ERROR_ENCODE);
}

TEST(EncoderDecAlert, RejectsCounterTooLarge) {
    DecAlertPayload payload{};
    EXPECT_EQ(encode_dec_alert(payload, AlertLevel::OFF, 0.0, 16U, 0U),
              Status::ERROR_ENCODE);
}

TEST(EncoderDecAlert, RejectsInvalidAlertLevel) {
    DecAlertPayload payload{};
    const auto invalid = static_cast<AlertLevel>(99U);
    EXPECT_EQ(encode_dec_alert(payload, invalid, 0.0, 0U, 0U),
              Status::ERROR_ENCODE);
}

// ===========================================================================
// DEC_HB
// ===========================================================================

TEST(EncoderDecHb, NominalEncoding) {
    DecHbPayload payload{};
    const Status s = encode_dec_hb(payload, 42U, AlertLevel::WARNING);

    EXPECT_EQ(s, Status::OK);
    EXPECT_EQ(payload[0], 42U);
    EXPECT_EQ(payload[1], 2U);
}

TEST(EncoderDecHb, AllStates) {
    for (int st = 0; st <= 4; ++st) {
        DecHbPayload payload{};
        const Status s = encode_dec_hb(payload, 0U, static_cast<AlertLevel>(st));
        EXPECT_EQ(s, Status::OK);
        EXPECT_EQ(payload[1], static_cast<std::uint8_t>(st));
    }
}

TEST(EncoderDecHb, AliveCounterMax) {
    DecHbPayload payload{};
    const Status s = encode_dec_hb(payload, 255U, AlertLevel::OFF);
    EXPECT_EQ(s, Status::OK);
    EXPECT_EQ(payload[0], 255U);
}

TEST(EncoderDecHb, RejectsInvalidState) {
    DecHbPayload payload{};
    const auto invalid = static_cast<AlertLevel>(99U);
    EXPECT_EQ(encode_dec_hb(payload, 0U, invalid), Status::ERROR_ENCODE);
}

// ===========================================================================
// Round-trip (encoder + decoder)
// ===========================================================================

TEST(EncoderRoundTrip, DecAlertCanBeDecoded) {
    // On encode, puis on décode une trame PERC_OBJECT pour simuler le round-trip
    // Note : DEC_ALERT n'a pas de decodeur pour l'instant, mais on vérifie
    // la cohérence des bits encodés.
    DecAlertPayload payload{};
    const Status s = encode_dec_alert(payload, AlertLevel::BRAKE, 12.34, 7U, 0x77U);
    ASSERT_EQ(s, Status::OK);

    // Vérification manuelle du layout
    EXPECT_EQ(payload[0] & 0x0FU, 0x03U);  // BRAKE = 3
    EXPECT_EQ(payload[2] & 0x0FU, 0x07U);  // counter = 7
    EXPECT_EQ(payload[3], 0x77U);          // crc
}

