# Tests à venir (GoogleTest)
# Tests unitaires GoogleTest pour l'ECU Decision
# Tests unitaires GoogleTest pour l'ECU Decision

find_package(GTest REQUIRED)
include(GoogleTest)

# ---------------------------------------------------------------------------
# Test E2E (CRC8 + compteur)
# ---------------------------------------------------------------------------

add_executable(test_e2e test_e2e.cpp)
target_link_libraries(test_e2e
    PRIVATE
        decision_core
        GTest::gtest
        GTest::gtest_main
)
gtest_discover_tests(test_e2e)

# ---------------------------------------------------------------------------
# Test TTC (calcul + estimation vitesse)
# ---------------------------------------------------------------------------

add_executable(test_ttc test_ttc.cpp)
target_link_libraries(test_ttc
    PRIVATE
        decision_core
        GTest::gtest
        GTest::gtest_main
)
gtest_discover_tests(test_ttc)


# ---------------------------------------------------------------------------
# Test Decoder (PERC_OBJECT)
# ---------------------------------------------------------------------------

add_executable(test_decoder test_decoder.cpp)
target_link_libraries(test_decoder
    PRIVATE
        decision_core
        GTest::gtest
        GTest::gtest_main
)
gtest_discover_tests(test_decoder)


# ---------------------------------------------------------------------------
# Test Encoder (DEC_ALERT, DEC_HB)
# ---------------------------------------------------------------------------

add_executable(test_encoder test_encoder.cpp)
target_link_libraries(test_encoder
    PRIVATE
        decision_core
        GTest::gtest
        GTest::gtest_main
)
gtest_discover_tests(test_encoder)



# ---------------------------------------------------------------------------
# Test FSM (machine à états)
# ---------------------------------------------------------------------------

add_executable(test_fsm test_fsm.cpp)
target_link_libraries(test_fsm
    PRIVATE
        decision_core
        GTest::gtest
        GTest::gtest_main
)
gtest_discover_tests(test_fsm)


