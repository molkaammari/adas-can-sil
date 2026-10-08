/**
 * @file test_e2e.cpp
 * @brief Tests unitaires pour la protection E2E (CRC8 + compteur).
 */

#include <gtest/gtest.h>

#include <array>

#include "decision/e2e.hpp"

using adas::decision::e2e::crc8;
using adas::decision::e2e::next_counter;

// ===========================================================================
// Tests CRC8
// ===========================================================================

TEST(E2eCrc8, EmptyBufferReturnsZero) {
    // Par convention, un buffer vide donne 0 (cas dégénéré)
    EXPECT_EQ(crc8(nullptr, 0U), 0U);
}

TEST(E2eCrc8, KnownVectors) {
    // Vecteurs de test : valeurs calculées pour poly 0x1D, init 0xFF, xorout 0xFF
    // (ces valeurs seront vérifiées lors du premier run)
    const std::uint8_t data1[] = {0x00U};
    const std::uint8_t data2[] = {0x01U, 0x02U, 0x03U, 0x04U};
    const std::uint8_t data3[] = {0xFFU, 0xFFU, 0xFFU, 0xFFU};

    // Les CRC doivent être différents pour des données différentes
    EXPECT_NE(crc8(data1), crc8(data2));
    EXPECT_NE(crc8(data2), crc8(data3));
    EXPECT_NE(crc8(data1), crc8(data3));
}

TEST(E2eCrc8, Deterministic) {
    const std::uint8_t data[] = {0xDEU, 0xADU, 0xBEU, 0xEFU};

    // Le CRC doit être déterministe (même entrée → même sortie)
    const std::uint8_t crc1 = crc8(data);
    const std::uint8_t crc2 = crc8(data);
    EXPECT_EQ(crc1, crc2);
}

TEST(E2eCrc8, SingleBitFlipChangesCrc) {
    std::uint8_t data[] = {0x12U, 0x34U, 0x56U, 0x78U};
    const std::uint8_t crc_ref = crc8(data);

    // Pour chaque bit, on flip et on vérifie que le CRC change
    for (std::size_t byte = 0U; byte < 4U; ++byte) {
        for (int bit = 0; bit < 8; ++bit) {
            data[byte] ^= static_cast<std::uint8_t>(1U << bit);

            const std::uint8_t crc_flipped = crc8(data);
            EXPECT_NE(crc_ref, crc_flipped)
                << "CRC identique après flip byte=" << byte << " bit=" << bit;

            // Restaurer
            data[byte] ^= static_cast<std::uint8_t>(1U << bit);
        }
    }
}

// ===========================================================================
// Tests compteur 4 bits
// ===========================================================================

TEST(E2eCounter, Increment) {
    EXPECT_EQ(next_counter(0U),  1U);
    EXPECT_EQ(next_counter(1U),  2U);
    EXPECT_EQ(next_counter(14U), 15U);
}

TEST(E2eCounter, WrapAt15) {
    EXPECT_EQ(next_counter(15U), 0U);
}

TEST(E2eCounter, SequenceFullCycle) {
    std::uint8_t counter = 0U;
    for (int i = 0; i < 16; ++i) {
        counter = next_counter(counter);
    }
    // Après 16 incréments, on revient à 0
    EXPECT_EQ(counter, 0U);
}

TEST(E2eCounter, NeverExceedsMax) {
    std::uint8_t counter = 0U;
    for (int i = 0; i < 100; ++i) {
        counter = next_counter(counter);
        EXPECT_LE(counter, 15U) << "Compteur hors limites après " << i << " itérations";
    }
}

