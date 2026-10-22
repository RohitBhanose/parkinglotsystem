#pragma once

// Small custom templates used across the core.
//
//   requireInRange  - generic range validation for any ordered type
//                     (int hours, double rates, long long durations ...).
//   findOrNull      - generic "look up a key, give me a pointer or nullptr"
//                     helper for std::map / std::unordered_map.

#include <sstream>
#include <string>

#include "exceptions/ParkingException.hpp"

namespace parking {

// Returns `value` unchanged when low <= value <= high, otherwise throws a
// ValidationException naming the field. Returning the value lets it be used
// directly inside constructor initialiser lists.
template <typename T>
T requireInRange(const T& value, const T& low, const T& high, const std::string& fieldName) {
    if (value < low || high < value) {
        std::ostringstream message;
        message << fieldName << " must be between " << low << " and " << high
                << " (got " << value << ")";
        throw ValidationException(message.str());
    }
    return value;
}

// Pointer to the value stored under `key`, or nullptr when the key is absent.
// Constness follows the map: a const map yields a pointer-to-const.
template <typename Map, typename Key>
auto findOrNull(Map& map, const Key& key) -> decltype(&map.find(key)->second) {
    auto it = map.find(key);
    return it == map.end() ? nullptr : &it->second;
}

}  // namespace parking
