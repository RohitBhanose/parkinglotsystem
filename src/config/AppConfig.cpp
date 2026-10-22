#include "config/AppConfig.hpp"

#include <set>
#include <sstream>

#include "config/KeyValueFile.hpp"
#include "exceptions/ParkingException.hpp"
#include "util/Validation.hpp"

namespace parking {

namespace {

double parseDouble(const std::string& text, const std::string& where) {
    std::istringstream in(text);
    double value = 0.0;
    if (!(in >> value) || !(in >> std::ws).eof()) {
        throw ValidationException(where + ": '" + text + "' is not a number");
    }
    return value;
}

int parseInt(const std::string& text, const std::string& where) {
    std::istringstream in(text);
    int value = 0;
    if (!(in >> value) || !(in >> std::ws).eof()) {
        throw ValidationException(where + ": '" + text + "' is not a whole number");
    }
    return value;
}

bool parseBool(const std::string& text, const std::string& where) {
    if (text == "true" || text == "yes" || text == "1") return true;
    if (text == "false" || text == "no" || text == "0") return false;
    throw ValidationException(where + ": '" + text + "' is not true/false");
}

}  // namespace

AppConfig AppConfig::defaults() {
    AppConfig config;
    // parkinglot.c: base_rate = 0.67, peak_surcharge = 0.8 (applies to every vehicle today).
    config.rateCards_["CAR"] = {0.67, 0.80};
    // database/seed.sql pricing_rules row for BIKE.
    config.rateCards_["BIKE"] = {0.40, 0.50};
    // database/seed.sql: 30 slots in zones A-D.
    config.slotLayout_ = {
        {1, 12, 'A', 1, "STANDARD"}, {13, 18, 'B', 1, "STANDARD"}, {19, 21, 'B', 1, "COMPACT"},
        {22, 24, 'C', 2, "COMPACT"}, {25, 27, 'C', 2, "LARGE"},    {28, 30, 'D', 2, "LARGE"},
    };
    return config;
}

AppConfig AppConfig::loadFromFile(const std::string& path) {
    AppConfig config = defaults();
    bool layoutFromFile = false;
    for (const auto& entry : readKeyValueFile(path)) {
        const std::string where = path + ":" + std::to_string(entry.lineNumber);
        if (entry.key == "slots" && !layoutFromFile) {
            config.slotLayout_.clear();  // a file that lists slots replaces the default layout
            layoutFromFile = true;
        }
        config.apply(entry.key, entry.value, where);
    }
    config.source_ = path;
    config.validate();
    return config;
}

void AppConfig::apply(const std::string& key, const std::string& value, const std::string& where) {
    if (key == "lot_name") {
        lotName_ = value;
    } else if (key == "fee_strategy") {
        feeStrategy_ = value;
    } else if (key == "flat_rate_per_minute") {
        flatRatePerMinute_ = parseDouble(value, where);
    } else if (key == "peak_start_hour") {
        peakWindow_.startHour = parseInt(value, where);
    } else if (key == "peak_end_hour") {
        peakWindow_.endHour = parseInt(value, where);
    } else if (key == "weekend_is_peak") {
        peakWindow_.weekendsArePeak = parseBool(value, where);
    } else if (key.rfind("rate.", 0) == 0) {
        // rate.CAR = 0.67 0.80
        std::istringstream in(value);
        std::string base, peak;
        if (!(in >> base >> peak)) {
            throw ValidationException(where + ": expected '<base_rate> <peak_rate>'");
        }
        rateCards_[key.substr(5)] = {parseDouble(base, where), parseDouble(peak, where)};
    } else if (key == "slots") {
        // slots = 1-12 A 1 STANDARD
        std::istringstream in(value);
        std::string range, zone, floor, type;
        if (!(in >> range >> zone >> floor >> type) || zone.size() != 1 || range.find('-') == std::string::npos) {
            throw ValidationException(where + ": expected 'slots = <first>-<last> <zone> <floor> <type>'");
        }
        const auto dash = range.find('-');
        SlotRange slots;
        slots.first = parseInt(range.substr(0, dash), where);
        slots.last = parseInt(range.substr(dash + 1), where);
        slots.zone = zone[0];
        slots.floor = parseInt(floor, where);
        slots.slotType = type;
        slotLayout_.push_back(slots);
    } else if (key == "data_file") {
        dataFile_ = value;
    } else if (key == "storage_backend") {
        storageBackend_ = value;
    } else {
        throw ValidationException(where + ": unknown setting '" + key + "'");
    }
}

void AppConfig::validate() const {
    if (feeStrategy_ != "peak" && feeStrategy_ != "flat") {
        throw ValidationException("fee_strategy must be 'peak' or 'flat'");
    }
    if (storageBackend_ != "csv" && storageBackend_ != "mysql") {
        throw ValidationException("storage_backend must be 'csv' or 'mysql'");
    }
    requireInRange(peakWindow_.startHour, 0, 23, "peak_start_hour");
    requireInRange(peakWindow_.endHour, 1, 24, "peak_end_hour");
    if (peakWindow_.endHour <= peakWindow_.startHour) {
        throw ValidationException("peak_end_hour must be after peak_start_hour");
    }
    requireInRange(flatRatePerMinute_, 0.0, 1000.0, "flat_rate_per_minute");
    for (const auto& [type, card] : rateCards_) {
        requireInRange(card.baseRate, 0.0, 1000.0, "rate." + type + " base rate");
        requireInRange(card.peakRate, 0.0, 1000.0, "rate." + type + " peak rate");
    }
    if (slotLayout_.empty()) {
        throw ValidationException("The slot layout is empty");
    }
    std::set<int> seen;
    for (const auto& range : slotLayout_) {
        requireInRange(range.first, 1, 9999, "first slot number");
        requireInRange(range.last, range.first, 9999, "last slot number");
        for (int number = range.first; number <= range.last; ++number) {
            if (!seen.insert(number).second) {
                throw ValidationException("Slot " + std::to_string(number) + " is listed twice in the layout");
            }
        }
    }
}

const RateCard& AppConfig::rateFor(const std::string& vehicleType) const {
    const RateCard* card = findOrNull(rateCards_, vehicleType);
    if (card == nullptr) {
        throw ValidationException("No rate card configured for vehicle type '" + vehicleType + "'");
    }
    return *card;
}

std::vector<ParkingSlot> AppConfig::buildSlots() const {
    std::vector<ParkingSlot> slots;
    int nextId = 1;
    for (const auto& range : slotLayout_) {
        for (int number = range.first; number <= range.last; ++number) {
            slots.emplace_back(nextId++, std::to_string(number), range.zone, range.floor, range.slotType);
        }
    }
    return slots;
}

}  // namespace parking
