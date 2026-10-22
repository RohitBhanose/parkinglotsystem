#include "services/ParkingFeeStrategy.hpp"

#include <algorithm>
#include <iomanip>
#include <sstream>

#include "exceptions/ParkingException.hpp"

namespace parking {

FeeBreakdown ParkingFeeStrategy::calculateFee(TimePoint entry, TimePoint exit) const {
    if (exit <= entry) {
        throw ValidationException("Invalid time: exit must be after entry");
    }
    return computeFee(entry, exit);
}

PeakHourFeeStrategy::PeakHourFeeStrategy(RateCard rates, PeakWindow window) : rates_(rates), window_(window) {}

bool PeakHourFeeStrategy::isPeak(const std::tm& localTime) const {
    // Same test as is_peak() in parkinglot.c: Sunday (0) / Saturday (6), or 18:00-22:00.
    if (window_.weekendsArePeak && (localTime.tm_wday == 0 || localTime.tm_wday == 6)) {
        return true;
    }
    return localTime.tm_hour >= window_.startHour && localTime.tm_hour < window_.endHour;
}

FeeBreakdown PeakHourFeeStrategy::computeFee(TimePoint entry, TimePoint exit) const {
    FeeBreakdown fee;
    fee.baseRate = rates_.baseRate;
    fee.peakRate = rates_.peakRate;
    fee.totalMinutes = (exit - entry).count();

    // parkinglot.c looked at every second t in [entry, exit) and billed it as
    // one "minute" at the base or peak rate. Whether a second is peak depends
    // only on its local hour and weekday, so all seconds up to the next local
    // hour boundary are classified together - identical totals, but one
    // localtime() call per hour instead of one per second.
    TimePoint current = entry;
    while (current < exit) {
        const std::tm local = timeutil::toLocalTm(current);
        const long long secondsToNextHour = 3600 - (local.tm_min * 60LL + local.tm_sec);
        const TimePoint chunkEnd = std::min(exit, current + std::chrono::seconds(secondsToNextHour));
        const long long seconds = (chunkEnd - current).count();
        if (isPeak(local)) {
            fee.peakMinutes += seconds;
        } else {
            fee.baseMinutes += seconds;
        }
        current = chunkEnd;
    }

    fee.baseAmount = fee.baseMinutes * fee.baseRate;
    fee.peakAmount = fee.peakMinutes * fee.peakRate;
    fee.totalAmount = fee.baseAmount + fee.peakAmount;
    return fee;
}

std::string PeakHourFeeStrategy::describe() const {
    std::ostringstream out;
    out << std::fixed << std::setprecision(2) << "Rs " << rates_.baseRate << "/min base, Rs " << rates_.peakRate
        << "/min during " << (window_.weekendsArePeak ? "weekends & " : "") << std::setfill('0') << std::setw(2)
        << window_.startHour << ":00-" << std::setw(2) << window_.endHour << ":00";
    return out.str();
}

FlatRateFeeStrategy::FlatRateFeeStrategy(double ratePerMinute) : ratePerMinute_(ratePerMinute) {}

FeeBreakdown FlatRateFeeStrategy::computeFee(TimePoint entry, TimePoint exit) const {
    FeeBreakdown fee;
    fee.totalMinutes = (exit - entry).count();
    fee.baseMinutes = fee.totalMinutes;
    fee.baseRate = ratePerMinute_;
    fee.peakRate = 0.0;
    fee.baseAmount = fee.baseMinutes * ratePerMinute_;
    fee.totalAmount = fee.baseAmount;
    return fee;
}

std::string FlatRateFeeStrategy::describe() const {
    std::ostringstream out;
    out << std::fixed << std::setprecision(2) << "Rs " << ratePerMinute_ << "/min flat, no peak pricing";
    return out.str();
}

std::unique_ptr<ParkingFeeStrategy> createFeeStrategy(const AppConfig& config, const std::string& vehicleType) {
    if (config.getFeeStrategyName() == "flat") {
        return std::make_unique<FlatRateFeeStrategy>(config.getFlatRatePerMinute());
    }
    return std::make_unique<PeakHourFeeStrategy>(config.rateFor(vehicleType), config.getPeakWindow());
}

}  // namespace parking
