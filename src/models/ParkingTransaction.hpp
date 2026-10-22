#pragma once

#include <iosfwd>
#include <memory>
#include <optional>
#include <string>

#include "models/FeeBreakdown.hpp"
#include "models/Payment.hpp"
#include "models/Vehicle.hpp"
#include "storage/TransactionRecord.hpp"
#include "util/TimeUtils.hpp"

namespace parking {

class ParkingFeeStrategy;

// Created -> Active -> Completed, or Active -> Cancelled.
enum class TransactionStatus { Created, Active, Completed, Cancelled };

std::string toString(TransactionStatus status);
std::optional<TransactionStatus> parseTransactionStatus(const std::string& text);

// One parking session: which vehicle used which slot, when, and what it cost.
// Every state change goes through a method that checks the current state, so
// a session cannot be ended twice, billed without timestamps, and so on.
class ParkingTransaction {
public:
    ParkingTransaction(int transactionId, std::shared_ptr<const Vehicle> vehicle, std::string slotNumber);

    void startSession(TimePoint entryTime);                                 // Created  -> Active
    void endSession(TimePoint exitTime, const ParkingFeeStrategy& strategy); // Active   -> Completed
    void cancelTransaction(TimePoint cancelTime);                           // Active   -> Cancelled
    void settlePayment(PaymentMethod method, TimePoint paidAt);             // Completed, payment pending

    // Seconds between entry and exit. Needs both timestamps.
    long long calculateDuration() const;
    // Final fee for a completed session, or a running estimate up to `until`
    // for an active one.
    FeeBreakdown calculateFee(const ParkingFeeStrategy& strategy, TimePoint until) const;

    void displayTransaction(std::ostream& out) const;

    int getTransactionId() const { return transactionId_; }
    const Vehicle& getVehicle() const { return *vehicle_; }
    std::shared_ptr<const Vehicle> getVehiclePtr() const { return vehicle_; }
    const std::string& getSlotNumber() const { return slotNumber_; }
    TransactionStatus getStatus() const { return status_; }
    bool isActive() const { return status_ == TransactionStatus::Active; }
    std::optional<TimePoint> getEntryTime() const { return entryTime_; }
    std::optional<TimePoint> getExitTime() const { return exitTime_; }
    const std::optional<FeeBreakdown>& getFee() const { return fee_; }
    const std::optional<Payment>& getPayment() const { return payment_; }

    TransactionRecord toRecord() const;
    // Rebuilds a transaction from storage, validating that the stored state
    // is self-consistent. Throws ValidationException otherwise.
    static ParkingTransaction fromRecord(const TransactionRecord& record, std::shared_ptr<const Vehicle> vehicle);

private:
    void requireStatus(TransactionStatus expected, const std::string& action) const;

    int transactionId_;
    std::shared_ptr<const Vehicle> vehicle_;
    std::string slotNumber_;
    TransactionStatus status_ = TransactionStatus::Created;
    std::optional<TimePoint> entryTime_;
    std::optional<TimePoint> exitTime_;
    std::optional<FeeBreakdown> fee_;
    std::optional<Payment> payment_;
};

}  // namespace parking
