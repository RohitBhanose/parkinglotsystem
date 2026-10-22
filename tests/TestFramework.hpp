#pragma once

// A deliberately tiny test framework (no external dependency).
//
//   TEST_CASE(name) { CHECK(cond); CHECK_EQ(a, b); CHECK_THROWS_AS(expr, Type); }
//
// Each test is registered automatically; tests/test_main.cpp runs them all,
// prints PASS/FAIL per test and returns a non-zero exit code on failure.

#include <cmath>
#include <filesystem>
#include <functional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace testing {

struct Failure : std::runtime_error {
    using std::runtime_error::runtime_error;
};

inline std::vector<std::pair<std::string, std::function<void()>>>& registry() {
    static std::vector<std::pair<std::string, std::function<void()>>> tests;
    return tests;
}

inline bool registerTest(const char* name, std::function<void()> test) {
    registry().emplace_back(name, std::move(test));
    return true;
}

inline void fail(const char* file, int line, const std::string& message) {
    std::ostringstream out;
    out << file << ":" << line << ": " << message;
    throw Failure(out.str());
}

// A fresh, empty directory under the system temp dir, removed on destruction.
class TempDir {
public:
    TempDir() {
        static int counter = 0;
        path_ = std::filesystem::temp_directory_path() /
                ("parking_tests_" + std::to_string(std::hash<std::string>{}(std::to_string(++counter) + __TIME__)));
        std::filesystem::remove_all(path_);
        std::filesystem::create_directories(path_);
    }
    ~TempDir() {
        std::error_code ec;
        std::filesystem::remove_all(path_, ec);
    }
    TempDir(const TempDir&) = delete;
    TempDir& operator=(const TempDir&) = delete;

    std::string file(const std::string& name) const { return (path_ / name).string(); }

private:
    std::filesystem::path path_;
};

}  // namespace testing

#define TEST_CASE(name)                                                                  \
    static void name();                                                                  \
    static const bool name##_registered = testing::registerTest(#name, name);            \
    static void name()

#define CHECK(condition)                                                                 \
    do {                                                                                 \
        if (!(condition)) testing::fail(__FILE__, __LINE__, "CHECK(" #condition ")");    \
    } while (0)

#define CHECK_EQ(actual, expected)                                                       \
    do {                                                                                 \
        const auto actual_ = (actual);                                                   \
        const auto expected_ = (expected);                                               \
        if (!(actual_ == expected_)) {                                                   \
            std::ostringstream message_;                                                 \
            message_ << "CHECK_EQ(" #actual ", " #expected "): got '" << actual_         \
                     << "', expected '" << expected_ << "'";                             \
            testing::fail(__FILE__, __LINE__, message_.str());                           \
        }                                                                                \
    } while (0)

#define CHECK_NEAR(actual, expected)                                                     \
    do {                                                                                 \
        const double actual_ = (actual);                                                 \
        const double expected_ = (expected);                                             \
        if (std::fabs(actual_ - expected_) > 1e-9) {                                     \
            std::ostringstream message_;                                                 \
            message_ << "CHECK_NEAR(" #actual "): got " << actual_ << ", expected "      \
                     << expected_;                                                       \
            testing::fail(__FILE__, __LINE__, message_.str());                           \
        }                                                                                \
    } while (0)

#define CHECK_THROWS_AS(expression, ExceptionType)                                       \
    do {                                                                                 \
        bool caught_ = false;                                                            \
        try {                                                                            \
            (void)(expression);                                                          \
        } catch (const ExceptionType&) {                                                 \
            caught_ = true;                                                              \
        } catch (const std::exception& other_) {                                         \
            testing::fail(__FILE__, __LINE__,                                            \
                          std::string("expected " #ExceptionType ", got: ") + other_.what()); \
        }                                                                                \
        if (!caught_) testing::fail(__FILE__, __LINE__, "expected " #ExceptionType " from " #expression); \
    } while (0)
