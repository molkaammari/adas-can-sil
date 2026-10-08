#include <iostream>
#include "decision/types.hpp"

int main() {
    using adas::decision::AlertLevel;
    using adas::decision::PerceivedObject;
    using adas::decision::to_string;

    std::cout << "ADAS Decision ECU v0.1.0\n";

    // Test des types
    PerceivedObject obj{1, 25.0, -5.0, 5.0, true};
    std::cout << "Test object: id=" << static_cast<int>(obj.obj_id)
              << " dist=" << obj.distance_m << "m"
              << " valid=" << obj.valid << "\n";

    std::cout << "AlertLevel WARNING = " << to_string(AlertLevel::WARNING) << "\n";

    return 0;
}
