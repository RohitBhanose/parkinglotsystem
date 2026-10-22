#pragma once

#include <optional>
#include <string>

#include "models/FeeBreakdown.hpp"
#include "util/TimeUtils.hpp"

namespace parking {

// Flat, storage-friendly copy of one parking transaction (plus its payment).
// Repositories read and write these; ParkingTransaction converts to and from
// them, so storage code never touches the domain objects' private state.
struct TransactionRecord {
    int transactionId = 0;
    std::string numberPlate;
    std::string vehicleType = "CAR";
    std::string slotNumber;
    std::string status;                   // ACTIVE / COMPLETED / CANCELLED
    TimePoint entryTime{};
    std::optional<TimePoint> exitTime;
    std::optional<FeeBreakdown> fee;      // empty for legacy rows that never stored a fee
    std::string paymentMethod;            // empty when there is no payment
    std::string paymentStatus;            // PENDING / SUCCESS (empty when no payment)
    std::optional<TimePoint> paymentTime;
};

}  // namespace parking
