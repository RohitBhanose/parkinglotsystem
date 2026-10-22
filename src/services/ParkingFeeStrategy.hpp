#pragma once

#include <ctime>
#include <memory>
#include <string>

#include "config/AppConfig.hpp"
#include "models/FeeBreakdown.hpp"
#include "util/TimeUtils.hpp"

namespace parking {

// Abstract pricing policy. Callers only ever see this interface; which
// concrete policy runs is decided at runtime (config + vehicle type).
//
// calculateFee() is the public, non-virtual entry point: it validates the
// interval once for every policy and then calls the virtual computeFee().
// (The time-of-day rule needs real entry/exit times, not just a duration,
// so the interface takes both timestamps.)
class ParkingFeeStrategy {
public:
    virtual ~ParkingFeeStrategy() = default;

    FeeBreakdown calculateFee(TimePoint entry, TimePoint exit) const;

    virtual std::string getName() const = 0;
    virtual std::string describe() const = 0;

protected:
    virtual FeeBreakdown computeFee(TimePoint entry, TimePoint exit) const = 0;
};

// The rule from parkinglot.c (the current production rule):
// every billed minute inside the peak window costs peakRate, every other
// billed minute costs baseRate.
class PeakHourFeeStrategy : public ParkingFeeStrategy {
public:
    PeakHourFeeStrategy(RateCard rates, PeakWindow window);

    std::string getName() const override { return "peak-hour"; }
    std::string describe() const override;

    bool isPeak(const std::tm& localTime) const;

protected:
    FeeBreakdown computeFee(TimePoint entry, TimePoint exit) const override;

private:
    RateCard rates_;
    PeakWindow window_;
};

// The rule of the original CSV-only Streamlit app (main branch):
// one flat rate for every billed minute, no peak pricing.
// Selected with `fee_strategy = flat` in config/parking.cfg.
class FlatRateFeeStrategy : public ParkingFeeStrategy {
public:
    explicit FlatRateFeeStrategy(double ratePerMinute);

    std::string getName() const override { return "flat-rate"; }
    std::string describe() const override;

protected:
    FeeBreakdown computeFee(TimePoint entry, TimePoint exit) const override;

private:
    double ratePerMinute_;
};

// Picks the policy named in the config, priced for the given vehicle type.
std::unique_ptr<ParkingFeeStrategy> createFeeStrategy(const AppConfig& config, const std::string& vehicleType);

}  // namespace parking
