/**
 * @file test_decoder.cpp
 * @brief Tests unitaires du décodage PERC_OBJECT.
 */

#include <gtest/gtest.h>

#include <array>
#include <cstdint>

#include "decision/decoder.hpp"
#include "decision/types.hpp"

using adas::decision::Status;
using adas::decision::PerceivedObject;
using adas::decision::decoder::decode_perc_object;
using adas::decision::decoder::DLC_PERC_OBJECT;

// ===========================================================================
// Tests nominaux
// ===========================================================================

TEST(DecoderPercObject, NominalFrame) {
    // Trame générée par l'ECU Perception en Phase 2 :
    //   obj_id=1, dist=4.40m, v_rel=0.00, ttc=0.00, valid=1
    //   → 01 B8 01 10 27 00 00 01
    const std::array<std::uint8_t, 8> data = {
        0x01U, 0xB8U, 0x01U, 0x10U,
        0x27U, 0x00U, 0x00U, 0x01U
    };

    PerceivedObject obj{};
    const Status s = decode_perc_object(data.data(), data.size(), obj);

    EXPECT_EQ(s, Status::OK);
    EXPECT_EQ(obj.obj_id, 1U);
    EXPECT_NEAR(obj.distance_m, 4.40, 0.01);
    EXPECT_NEAR(obj.rel_speed_mps, 0.00, 0.01);
    EXPECT_NEAR(obj.ttc_s, 0.00, 0.01);
    EXPECT_TRUE(obj.valid);
}

TEST(DecoderPercObject, TwentyFiveMeters) {
    // 2500 → C4 09 (LE)
    const std::array<std::uint8_t, 8> data = {
        0x01U, 0xC4U, 0x09U, 0x00U,
        0x00U, 0xF4U, 0x01U, 0x01U
    };

    PerceivedObject obj{};
    ASSERT_EQ(decode_perc_object(data.data(), data.size(), obj), Status::OK);
    EXPECT_NEAR(obj.distance_m, 25.00, 0.01);
    EXPECT_NEAR(obj.ttc_s, 5.00, 0.01);
}

TEST(DecoderPercObject, NegativeRelSpeed) {
    // v_rel = -5 m/s → raw = (-5 + 100) / 0.01 = 9500 = 0x251C → 1C 25 (LE)
    const std::array<std::uint8_t, 8> data = {
        0x01U, 0xC4U, 0x09U, 0x1CU,
        0x25U, 0xF4U, 0x01U, 0x01U
    };

    PerceivedObject obj{};
    ASSERT_EQ(decode_perc_object(data.data(), data.size(), obj), Status::OK);
    EXPECT_NEAR(obj.rel_speed_mps, -5.00, 0.01);
}

TEST(DecoderPercObject, ValidFlagZero) {
    const std::array<std::uint8_t, 8> data = {
        0x00U, 0x00U, 0x00U, 0x00U,
        0x00U, 0x00U, 0x00U, 0x00U
    };

    PerceivedObject obj{};
    ASSERT_EQ(decode_perc_object(data.data(), data.size(), obj), Status::OK);
    EXPECT_FALSE(obj.valid);
}

TEST(DecoderPercObject, MaxValues) {
    // dist max = 655.35 m → 65535 = 0xFFFF
    // v_rel max = (65535 × 0.01) − 100 = 555.35 m/s
    // ttc max = 655.35 s → 65535
    const std::array<std::uint8_t, 8> data = {
        0xFFU, 0xFFU, 0xFFU, 0xFFU,
        0xFFU, 0xFFU, 0xFFU, 0x01U
    };

    PerceivedObject obj{};
    ASSERT_EQ(decode_perc_object(data.data(), data.size(), obj), Status::OK);
    EXPECT_EQ(obj.obj_id, 255U);
    EXPECT_NEAR(obj.distance_m, 655.35, 0.01);
    EXPECT_NEAR(obj.rel_speed_mps, 555.35, 0.01);
    EXPECT_NEAR(obj.ttc_s, 655.35, 0.01);
    EXPECT_TRUE(obj.valid);
}

// ===========================================================================
// Tests d'erreur
// ===========================================================================

TEST(DecoderPercObject, NullPointer) {
    PerceivedObject obj{};
    EXPECT_EQ(decode_perc_object(nullptr, 8U, obj), Status::ERROR_INVALID_DATA);
}

TEST(DecoderPercObject, BufferTooShort) {
    const std::array<std::uint8_t, 4> data = {0x01U, 0x02U, 0x03U, 0x04U};
    PerceivedObject obj{};
    EXPECT_EQ(decode_perc_object(data.data(), data.size(), obj), Status::ERROR_DECODE);
}

TEST(DecoderPercObject, EmptyBuffer) {
    const std::array<std::uint8_t, 1> data = {0x00U};
    PerceivedObject obj{};
    EXPECT_EQ(decode_perc_object(data.data(), 0U, obj), Status::ERROR_DECODE);
}

// ===========================================================================
// Test d'is_usable() (méthode du PerceivedObject)
// ===========================================================================

TEST(DecoderPercObject, IsUsableRequiresValidAndPositiveDistance) {
    PerceivedObject obj{};

    // Invalide
    obj.valid = false;
    obj.distance_m = 10.0;
    EXPECT_FALSE(obj.is_usable());

    // Valide mais distance nulle
    obj.valid = true;
    obj.distance_m = 0.0;
    EXPECT_FALSE(obj.is_usable());

    // Valide et distance positive
    obj.distance_m = 10.0;
    EXPECT_TRUE(obj.is_usable());
}

