/**
 * @file main.cpp
 * @brief Orchestrateur de l'ECU Decision (ADAS FCW SIL).
 *
 * Boucle principale :
 *   1. Réception PERC_OBJECT (0x100) sur vcan0
 *   2. Décodage → PerceivedObject
 *   3. FSM update (transition d'état selon TTC)
 *   4. Encodage DEC_ALERT (0x200) avec CRC E2E
 *   5. Émission DEC_ALERT @ 20 Hz + DEC_HB @ 10 Hz
 *   6. Détection timeout perception → FAULT
 *
 * Usage :
 *   ./decision_main [--iface vcan0] [--duration 10]
 *
 * Références : REQ-DEC-001 à 007, REQ-E2E-001 à 004
 */

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

#include "decision/can_rx.hpp"
#include "decision/can_tx.hpp"
#include "decision/decoder.hpp"
#include "decision/e2e.hpp"
#include "decision/encoder.hpp"
#include "decision/fsm.hpp"
#include "decision/types.hpp"
#include "decision/ttc.hpp"

namespace {

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

constexpr const char* DEFAULT_IFACE = "vcan0";
constexpr double ALERT_PERIOD_S = 0.050;   // 20 Hz
constexpr double HB_PERIOD_S    = 0.100;   // 10 Hz

// ---------------------------------------------------------------------------
// Signal handler global (Ctrl+C)
// ---------------------------------------------------------------------------

std::atomic<bool> g_running{true};

void signal_handler(int /*signum*/) {
    g_running.store(false);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Lit un timestamp monotone en secondes.
double now_seconds() noexcept {
    using clock = std::chrono::steady_clock;
    static const auto t0 = clock::now();
    const auto dt = clock::now() - t0;
    return std::chrono::duration<double>(dt).count();
}

/// Affiche un timestamp lisible.
void log_line(const char* tag, const std::string& msg) {
    std::cout << '[' << tag << "] " << msg << '\n';
}

// ---------------------------------------------------------------------------
// Options CLI
// ---------------------------------------------------------------------------

struct Options {
    std::string iface = DEFAULT_IFACE;
    double duration_s = 0.0;  // 0 = infini
};

Options parse_args(int argc, char** argv) {
    Options opt;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--iface" && i + 1 < argc) {
            opt.iface = argv[++i];
        } else if (arg == "--duration" && i + 1 < argc) {
            opt.duration_s = std::atof(argv[++i]);
        } else if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: " << argv[0]
                      << " [--iface vcan0] [--duration 10]\n";
            std::exit(0);
        }
    }
    return opt;
}

}  // namespace

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    const Options opt = parse_args(argc, argv);

    // Installer le handler Ctrl+C
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    std::cout << "===========================================\n";
    std::cout << " ADAS Decision ECU — v0.1.0\n";
    std::cout << " iface    : " << opt.iface << '\n';
    std::cout << " duration : " << (opt.duration_s > 0 ? std::to_string(opt.duration_s) + " s" : "infinite") << '\n';
    std::cout << "===========================================\n\n";

    // ----- Ouvrir les sockets CAN -----
    try {
        adas::decision::can_rx::CanReceiver rx(
            opt.iface, adas::decision::decoder::CAN_ID_PERC_OBJECT);
        adas::decision::can_tx::CanSender tx(opt.iface);

        log_line("INIT", std::string("CAN receiver ouvert (filtre 0x")
                  + "100)");
        log_line("INIT", "CAN sender ouvert");

        adas::decision::fsm::Fsm fsm;
        std::uint8_t e2e_counter = 0U;
        std::uint8_t alive_counter = 0U;

        double t_start = now_seconds();
        double t_last_alert = 0.0;
        double t_last_hb = 0.0;
        double t_last_tick = 0.0;

        log_line("RUN", "boucle démarrée (Ctrl+C pour arrêter)\n");

        // ----- Boucle principale -----
        while (g_running.load()) {
            const double t_now = now_seconds();

            // Arrêt sur durée
            if (opt.duration_s > 0.0 && (t_now - t_start) >= opt.duration_s) {
                log_line("STOP", "durée atteinte");
                break;
            }

            // ----- Réception (timeout 10 ms) -----
            adas::decision::can_rx::CanFrame frame{};
            const bool got_frame = rx.receive(10, frame);

            // ----- Traitement d'une trame reçue -----
            if (got_frame) {
                adas::decision::PerceivedObject obj{};
                const auto status = adas::decision::decoder::decode_perc_object(
                    frame.data, frame.dlc, obj);

                if (status == adas::decision::Status::OK) {
                    const auto out = fsm.update(obj, t_now);

                    if (out.state_changed) {
                        char buf[256];
                        std::snprintf(buf, sizeof(buf),
                            "STATE %s → %s (ttc=%.2f s, reason=%s)",
                            adas::decision::fsm::to_string(
                                static_cast<adas::decision::fsm::State>(
                                    static_cast<std::uint8_t>(out.state))),
                            adas::decision::fsm::to_string(out.state),
                            out.ttc_s,
                            out.reason);
                        // Log concis
                        log_line("FSM", std::string("transition → ") +
                                  adas::decision::fsm::to_string(out.state) +
                                  " (ttc=" + std::to_string(out.ttc_s).substr(0,5) + " s)");
                    }
                } else {
                    log_line("DECODE", std::string("erreur : ") +
                              adas::decision::to_string(status));
                }
            }

            // ----- Tick FSM (timeout detection) -----
            if ((t_now - t_last_tick) > 0.010) {
                const auto tick_out = fsm.tick(t_now);
                if (tick_out.state_changed) {
                    log_line("FSM", std::string("tick transition → ") +
                              adas::decision::fsm::to_string(tick_out.state));
                }
                t_last_tick = t_now;
            }

            // ----- Émission DEC_ALERT @ 20 Hz -----
            if ((t_now - t_last_alert) >= ALERT_PERIOD_S) {
                const auto state = fsm.state();
                const auto alert = adas::decision::fsm::state_to_alert(state);

                // CRC E2E : on calcule sur les 3 premiers octets (à venir)
                // Pour l'instant, on encode d'abord avec CRC=0, puis on recalcule
                adas::decision::encoder::DecAlertPayload payload{};
                const double ttc_for_alert = 0.0;  // sera affiné plus tard
                auto s = adas::decision::encoder::encode_dec_alert(
                    payload, alert, ttc_for_alert, e2e_counter, 0x00U);

                if (s == adas::decision::Status::OK) {
                    // Calculer le CRC sur les 3 premiers octets
                    const std::uint8_t crc =
                        adas::decision::e2e::crc8(payload.data(), 3U);
                    payload[3] = crc;

                    if (tx.send(adas::decision::encoder::CAN_ID_DEC_ALERT,
                                payload)) {
                        // OK
                    } else {
                        log_line("TX", "échec envoi DEC_ALERT");
                    }
                }

                e2e_counter = adas::decision::e2e::next_counter(e2e_counter);
                t_last_alert = t_now;
            }

            // ----- Émission DEC_HB @ 10 Hz -----
            if ((t_now - t_last_hb) >= HB_PERIOD_S) {
                adas::decision::encoder::DecHbPayload hb{};
                const auto s = adas::decision::encoder::encode_dec_hb(
                    hb, alive_counter, fsm.state() == adas::decision::fsm::State::FAULT
                        ? adas::decision::AlertLevel::FAULT
                        : adas::decision::fsm::state_to_alert(fsm.state()));

                if (s == adas::decision::Status::OK) {
                    (void)tx.send(adas::decision::encoder::CAN_ID_DEC_HB, hb);
                }

                alive_counter = static_cast<std::uint8_t>(alive_counter + 1U);
                t_last_hb = t_now;
            }
        }

        log_line("STOP", "arrêt propre");
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] " << e.what() << '\n';
        return 1;
    }
}


