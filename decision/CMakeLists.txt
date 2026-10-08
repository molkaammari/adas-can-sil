cmake_minimum_required(VERSION 3.22)

project(adas_decision
    VERSION 0.1.0
    DESCRIPTION "ADAS Forward Collision Warning - ECU Decision"
    LANGUAGES CXX
)

# ---------------------------------------------------------------------------
# Standard C++
# ---------------------------------------------------------------------------

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

option(ADAS_BUILD_TESTS "Build unit tests" ON)
option(ADAS_WARNINGS_AS_ERRORS "Treat warnings as errors" OFF)

# ---------------------------------------------------------------------------
# Flags de compilation
# ---------------------------------------------------------------------------

add_compile_options(
    -Wall
    -Wextra
    -Wpedantic
    -Wshadow
    -Wconversion
    -Wsign-conversion
)

if(ADAS_WARNINGS_AS_ERRORS)
    add_compile_options(-Werror)
endif()

# ---------------------------------------------------------------------------
# Bibliothèque : decision_core
# ---------------------------------------------------------------------------

add_library(decision_core STATIC
    src/e2e.cpp
    src/ttc.cpp
    src/decoder.cpp
    src/encoder.cpp
    src/fsm.cpp
    src/can_rx.cpp
    src/can_tx.cpp
)

target_include_directories(decision_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# ---------------------------------------------------------------------------
# Exécutable : decision_main
# ---------------------------------------------------------------------------

add_executable(decision_main src/main.cpp)
target_link_libraries(decision_main PRIVATE decision_core)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if(ADAS_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
