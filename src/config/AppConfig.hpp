#pragma once

#include <map>
#include <string>
#include <vector>

#include "models/ParkingSlot.hpp"

namespace parking {

struct RateCard {
    double baseRate = 0.0;  // Rs per billed minute
    double peakRate = 0.0;  // Rs per billed minute during the peak window
};

// Peak window rule from parkinglot.c: all of Saturday/Sunday, plus
// [startHour, endHour) local time on every day.
struct PeakWindow {
    int startHour = 18;
    int endHour = 22;
    bool weekendsArePeak = true;
};

// A run of consecutive slot numbers sharing zone/floor/type, e.g. "1-12 A 1 STANDARD".
struct SlotRange {
    int first = 0;
    int last = 0;
    char zone = 'A';
    int floor = 1;
    std::string slotType = "STANDARD";
};

// All tunable values of the core: rates, peak window, slot layout and storage.
// The built-in defaults reproduce parkinglot.c and database/seed.sql exactly,
// so the core still behaves correctly if config/parking.cfg is missing.
class AppConfig {
public:
    static AppConfig defaults();
    // Defaults overridden by the file. Throws StorageException/ValidationException.
    static AppConfig loadFromFile(const std::string& path);

    const std::string& getLotName() const { return lotName_; }
    const std::string& getFeeStrategyName() const { return feeStrategy_; }  // "peak" or "flat"
    double getFlatRatePerMinute() const { return flatRatePerMinute_; }
    const PeakWindow& getPeakWindow() const { return peakWindow_; }
    const std::map<std::string, RateCard>& getRateCards() const { return rateCards_; }
    const RateCard& rateFor(const std::string& vehicleType) const;  // throws ValidationException
    const std::vector<SlotRange>& getSlotLayout() const { return slotLayout_; }
    const std::string& getDataFile() const { return dataFile_; }
    const std::string& getStorageBackend() const { return storageBackend_; }  // "csv" or "mysql"
    const std::string& getSource() const { return source_; }

    // One ParkingSlot per slot number in the layout, with ids 1..N.
    std::vector<ParkingSlot> buildSlots() const;

private:
    void apply(const std::string& key, const std::string& value, const std::string& where);
    void validate() const;

    std::string lotName_ = "PARK-DBMS Main Lot";
    std::string feeStrategy_ = "peak";
    double flatRatePerMinute_ = 1.0;
    PeakWindow peakWindow_;
    std::map<std::string, RateCard> rateCards_;
    std::vector<SlotRange> slotLayout_;
    std::string dataFile_ = "parking_data.csv";
    std::string storageBackend_ = "csv";
    std::string source_ = "built-in defaults";
};

}  // namespace parking
