#pragma once

#include <chrono>
#include <ctime>
#include <optional>
#include <string>

namespace parking {

using Clock = std::chrono::system_clock;

// The original C program worked with whole-second UNIX timestamps, so every
// time inside the core is kept at one-second resolution.
using TimePoint = std::chrono::time_point<Clock, std::chrono::seconds>;

namespace timeutil {

TimePoint now();
TimePoint fromUnix(long long seconds);
long long toUnix(TimePoint time);

// Thread-safe conversion to the machine's local time (localtime_s/_r).
std::tm toLocalTm(TimePoint time);

// Builds a TimePoint from a local calendar date and clock time.
TimePoint makeLocal(int year, int month, int day, int hour, int minute, int second);

// "dd/mm/YYYY HH:MM:SS" - the format used by the original parking_data.csv.
std::string formatCsv(TimePoint time);
std::optional<TimePoint> parseCsv(const std::string& text);

// "YYYY-mm-dd HH:MM:SS" - used for console output.
std::string formatDisplay(TimePoint time);

}  // namespace timeutil
}  // namespace parking
