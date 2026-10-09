/**
 * @file test_fsm.cpp
 * @brief Tests unitaires de la machine à états.
 */

#include <gtest/gtest.h>

#include "decision/fsm.hpp"
#include "decision/types.hpp"

using adas::decision::AlertLevel;
using adas::decision::PerceivedObject;
using adas::decision::fsm::Fsm;
using adas::decision::fsm::State;
using adas::decision::fsm::PERCEPTION_TIMEOUT_S;
using adas::decision::fsm::FAULT_RECOVERY_S;

namespace {

PerceivedObject make_object(double distance_m, double rel_speed_mps,
                            bool valid = true) {
    PerceivedObject obj{};
    obj.obj_id = 1;
    obj.distance_m = distance_m;
    obj.rel_speed_mps = rel_speed_mps;
    obj.ttc_s = 0.0;
    obj.valid = valid;
    return obj;
}

}  // namespace

// ===========================================================================
// État initial
// ===========================================================================

TEST(Fsm, StartsInOff) {
    Fsm fsm;
    EXPECT_EQ(fsm.state(), State::OFF);
}

// ===========================================================================
// Transitions depuis OFF
// ===========================================================================

TEST(Fsm, OffToStandbyOnFirstValidFrame) {
    Fsm fsm;
    // TTC = 50 / 5 = 10 s → safe
    const auto out = fsm.update(make_object(50.0, -5.0), 1.0);
    EXPECT_EQ(out.state, State::STANDBY);
    EXPECT_EQ(out.alert, AlertLevel::STANDBY);
    EXPECT_TRUE(out.state_changed);
}

TEST(Fsm, OffGoesDirectlyToWarningIfTtcLow) {
    Fsm fsm;
    // TTC = 3 / 2 = 1.5 s → WARNING
    const auto out = fsm.update(make_object(3.0, -2.0), 1.0);
    EXPECT_EQ(out.state, State::WARNING);
    EXPECT_EQ(out.alert, AlertLevel::WARNING);
}

TEST(Fsm, OffGoesDirectlyToBrakeIfTtcCritical) {
    Fsm fsm;
    // TTC = 2 / 5 = 0.4 s → BRAKE
    const auto out = fsm.update(make_object(2.0, -5.0), 1.0);
    EXPECT_EQ(out.state, State::BRAKE);
    EXPECT_EQ(out.alert, AlertLevel::BRAKE);
}

// ===========================================================================
// Transitions STANDBY ↔ WARNING ↔ BRAKE
// ===========================================================================

TEST(Fsm, StandbyToWarning) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);  // STANDBY
    const auto out = fsm.update(make_object(3.0, -2.0), 1.1);  // TTC=1.5 → WARNING
    EXPECT_EQ(out.state, State::WARNING);
    EXPECT_TRUE(out.state_changed);
}

TEST(Fsm, WarningToBrake) {
    Fsm fsm;
    (void)fsm.update(make_object(3.0, -2.0), 1.0);   // WARNING (TTC=1.5)
    const auto out = fsm.update(make_object(2.0, -5.0), 1.1);  // TTC=0.4 → BRAKE
    EXPECT_EQ(out.state, State::BRAKE);
    EXPECT_TRUE(out.state_changed);
}

TEST(Fsm, WarningToStandby) {
    Fsm fsm;
    (void)fsm.update(make_object(3.0, -2.0), 1.0);   // WARNING
    // TTC = 30 / 5 = 6 s → safe (bien au-dessus de 2.0 + 0.5)
    const auto out = fsm.update(make_object(30.0, -5.0), 1.1);
    EXPECT_EQ(out.state, State::STANDBY);
    EXPECT_TRUE(out.state_changed);
}

// ===========================================================================
// Hystérésis
// ===========================================================================

TEST(Fsm, WarningStaysWhenTtcInDeadBand) {
    Fsm fsm;
    (void)fsm.update(make_object(3.0, -2.0), 1.0);   // WARNING (TTC=1.5)
    // TTC = 2.4 / 1.0 = 2.4 s → dans la dead band (WARNING + 0.5 = 2.5)
    const auto out = fsm.update(make_object(2.4, -1.0), 1.1);
    EXPECT_EQ(out.state, State::WARNING);  // reste en WARNING
}

TEST(Fsm, BrakeStaysWhenTtcInDeadBand) {
    Fsm fsm;
    (void)fsm.update(make_object(2.0, -5.0), 1.0);   // BRAKE (TTC=0.4)
    // TTC = 1.6 / 1.0 = 1.6 s → dans la dead band (BRAKE + 0.5 = 1.7)
    const auto out = fsm.update(make_object(1.6, -1.0), 1.1);
    EXPECT_EQ(out.state, State::BRAKE);  // reste en BRAKE
}

TEST(Fsm, BrakeCanExitToWarningAboveHysteresis) {
    Fsm fsm;
    (void)fsm.update(make_object(2.0, -5.0), 1.0);   // BRAKE
    // TTC = 5 / 2 = 2.5 s → au-dessus de BRAKE+HYST = 1.7 → WARNING possible
    // Mais 2.5 > WARNING+HYST (2.5) aussi, donc on pourrait aller en STANDBY
    // Avec TTC=1.9 : > 1.7 (leave brake) et < 2.5 (stay warning)
    const auto out = fsm.update(make_object(1.9, -1.0), 1.1);  // TTC = 1.9
    EXPECT_EQ(out.state, State::WARNING);
}

// ===========================================================================
// FAULT
// ===========================================================================

TEST(Fsm, InvalidObjectGoesToFault) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);  // STANDBY
    const auto out = fsm.update(make_object(50.0, -5.0, /*valid=*/false), 1.1);
    EXPECT_EQ(out.state, State::FAULT);
    EXPECT_EQ(out.alert, AlertLevel::FAULT);
}

TEST(Fsm, TimeoutGoesToFault) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);  // STANDBY
    // Tick après PERCEPTION_TIMEOUT_S + marge
    const auto out = fsm.tick(1.0 + PERCEPTION_TIMEOUT_S + 0.05);
    EXPECT_EQ(out.state, State::FAULT);
}

TEST(Fsm, TickBeforeTimeoutStaysInStandby) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);  // STANDBY
    const auto out = fsm.tick(1.0 + PERCEPTION_TIMEOUT_S / 2.0);
    EXPECT_EQ(out.state, State::STANDBY);
}

TEST(Fsm, FaultRecoveryOnValidFrame) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);  // STANDBY
    (void)fsm.update(make_object(50.0, -5.0, false), 1.1);  // FAULT
    EXPECT_EQ(fsm.state(), State::FAULT);

    // Nouvelle trame valide → retour en STANDBY (ou plus si TTC bas)
    const auto out = fsm.update(make_object(50.0, -5.0), 1.2);
    EXPECT_EQ(out.state, State::STANDBY);
}

//TEST(Fsm, FaultAutoRecoveryAfterTimeout) {
 TEST(Fsm, NoAutoRecoveryFromFault) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);           // STANDBY
    (void)fsm.update(make_object(50.0, -5.0, false), 1.1);    // FAULT
    EXPECT_EQ(fsm.state(), State::FAULT);

    // Après un long tick, on reste en FAULT (pas d'auto-recovery)
    const auto out = fsm.tick(5.0);
    EXPECT_EQ(out.state, State::FAULT);
}



// ===========================================================================
// Reset
// ===========================================================================

TEST(Fsm, ResetGoesToOff) {
    Fsm fsm;
    (void)fsm.update(make_object(50.0, -5.0), 1.0);  // STANDBY
    fsm.reset();
    EXPECT_EQ(fsm.state(), State::OFF);
}

// ===========================================================================
// Stabilité
// ===========================================================================

TEST(Fsm, NoStateChangeWhenAlreadyInCorrectState) {
    Fsm fsm;
    (void)fsm.update(make_object(3.0, -2.0), 1.0);  // WARNING
    const auto out = fsm.update(make_object(3.0, -2.0), 1.1);  // toujours WARNING
    EXPECT_EQ(out.state, State::WARNING);
    EXPECT_FALSE(out.state_changed);
}

