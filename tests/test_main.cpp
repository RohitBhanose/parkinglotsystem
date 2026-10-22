// Runs every TEST_CASE registered by the other test_*.cpp files.

#include <iostream>

#include "TestFramework.hpp"

int main() {
    int failed = 0;
    for (const auto& [name, test] : testing::registry()) {
        try {
            test();
            std::cout << "[PASS] " << name << '\n';
        } catch (const testing::Failure& failure) {
            ++failed;
            std::cout << "[FAIL] " << name << "\n       " << failure.what() << '\n';
        } catch (const std::exception& e) {
            ++failed;
            std::cout << "[FAIL] " << name << "\n       unexpected exception: " << e.what() << '\n';
        }
    }
    const auto total = testing::registry().size();
    std::cout << '\n' << (total - failed) << "/" << total << " tests passed\n";
    return failed == 0 ? 0 : 1;
}
