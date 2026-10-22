#include "util/TimeUtils.hpp"

#include <iomanip>
#include <sstream>

#include "exceptions/ParkingException.hpp"

namespace parking {
namespace timeutil {

TimePoint now() {
    return std::chrono::time_point_cast<std::chrono::seconds>(Clock::now());
}

TimePoint fromUnix(long long seconds) {
    return TimePoint(std::chrono::seconds(seconds));
}

long long toUnix(TimePoint time) {
    return time.time_since_epoch().count();
}

std::tm toLocalTm(TimePoint time) {
    const std::time_t raw = static_cast<std::time_t>(toUnix(time));
    std::tm local{};
#ifdef _WIN32
    if (localtime_s(&local, &raw) != 0) {
        throw ValidationException("Timestamp " + std::to_string(toUnix(time)) + " is out of range");
    }
#else
    if (localtime_r(&raw, &local) == nullptr) {
        throw ValidationException("Timestamp " + std::to_string(toUnix(time)) + " is out of range");
    }
#endif
    return local;
}

TimePoint makeLocal(int year, int month, int day, int hour, int minute, int second) {
    std::tm local{};
    local.tm_year = year - 1900;
    local.tm_mon = month - 1;
    local.tm_mday = day;
    local.tm_hour = hour;
    local.tm_min = minute;
    local.tm_sec = second;
    local.tm_isdst = -1;  // let the C library decide whether DST applies
    const std::time_t raw = std::mktime(&local);
    if (raw == static_cast<std::time_t>(-1)) {
        throw ValidationException("Invalid local date/time");
    }
    return fromUnix(static_cast<long long>(raw));
}

std::string formatCsv(TimePoint time) {
    const std::tm local = toLocalTm(time);
    std::ostringstream out;
    out << std::put_time(&local, "%d/%m/%Y %H:%M:%S");
    return out.str();
}

std::optional<TimePoint> parseCsv(const std::string& text) {
    std::tm parsed{};
    std::istringstream in(text);
    in >> std::get_time(&parsed, "%d/%m/%Y %H:%M:%S");
    if (in.fail()) {
        return std::nullopt;
    }
    in >> std::ws;
    if (!in.eof()) {
        return std::nullopt;  // trailing garbage after the time
    }

    const int day = parsed.tm_mday;
    const int month = parsed.tm_mon;
    parsed.tm_isdst = -1;
    const std::time_t raw = std::mktime(&parsed);
    // mktime silently normalises impossible dates (31/02 -> 03/03); reject them.
    if (raw == static_cast<std::time_t>(-1) || parsed.tm_mday != day || parsed.tm_mon != month) {
        return std::nullopt;
    }
    return fromUnix(static_cast<long long>(raw));
}

std::string formatDisplay(TimePoint time) {
    const std::tm local = toLocalTm(time);
    std::ostringstream out;
    out << std::put_time(&local, "%Y-%m-%d %H:%M:%S");
    return out.str();
}

}  // namespace timeutil
}  // namespace parking
