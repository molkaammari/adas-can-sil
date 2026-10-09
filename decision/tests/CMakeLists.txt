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

