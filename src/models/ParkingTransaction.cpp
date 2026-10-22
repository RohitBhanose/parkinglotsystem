#include "models/ParkingTransaction.hpp"

#include <iomanip>
#include <ostream>

#include "exceptions/ParkingException.hpp"
#include "services/ParkingFeeStrategy.hpp"

namespace parking {

std::string toString(TransactionStatus status) {
    switch (status) {
        case TransactionStatus::Created: return "CREATED";
        case TransactionStatus::Active: return "ACTIVE";
        case TransactionStatus::Completed: return "COMPLETED";
        case TransactionStatus::Cancelled: return "CANCELLED";
    }
    return "CREATED";
}

std::optional<TransactionStatus> parseTransactionStatus(const std::string& text) {
    if (text == "ACTIVE") return TransactionStatus::Active;
    if (text == "COMPLETED") return TransactionStatus::Completed;
    if (text == "CANCELLED") return TransactionStatus::Cancelled;
    return std::nullopt;
}

ParkingTransaction::ParkingTransaction(int transactionId, std::shared_ptr<const Vehicle> vehicle,
                                       std::string slotNumber)
    : transactionId_(transactionId), vehicle_(std::move(vehicle)), slotNumber_(std::move(slotNumber)) {
    if (transactionId_ <= 0) {
        throw ValidationException("Transaction id must be positive");
    }
    if (!vehicle_) {
        throw ValidationException("A transaction needs a vehicle");
    }
    if (slotNumber_.empty()) {
        throw ValidationException("A transaction needs a slot number");
    }
}

void ParkingTransaction::requireStatus(TransactionStatus expected, const std::string& action) const {
    if (status_ != expected) {
        throw InvalidSessionStateException("Cannot " + action + " transaction #" + std::to_string(transactionId_) +
                                           ": it is " + toString(status_) + ", expected " + toString(expected));
    }
}

void ParkingTransaction::startSession(TimePoint entryTime) {
    requireStatus(TransactionStatus::Created, "start");
    entryTime_ = entryTime;
    status_ = TransactionStatus::Active;
}

void ParkingTransaction::endSession(TimePoint exitTime, const ParkingFeeStrategy& strategy) {
    requireStatus(TransactionStatus::Active, "end");
    // calculateFee() rejects exit <= entry before anything is changed.
    FeeBreakdown fee = strategy.calculateFee(*entryTime_, exitTime);
    exitTime_ = exitTime;
    fee_ = fee;
    status_ = TransactionStatus::Completed;
    payment_.emplace(transactionId_, transactionId_, fee.totalAmount);
}

void ParkingTransaction::cancelTransaction(TimePoint cancelTime) {
    requireStatus(TransactionStatus::Active, "cancel");
    if (cancelTime < *entryTime_) {
        throw ValidationException("Cancel time is before the entry time");
    }
    // Same rule as parkinglot.c's "cancel" mode: a cancelled session costs 0.
    FeeBreakdown fee;
    fee.totalMinutes = (cancelTime - *entryTime_).count();
    exitTime_ = cancelTime;
    fee_ = fee;
    status_ = TransactionStatus::Cancelled;
}

void ParkingTransaction::settlePayment(PaymentMethod method, TimePoint paidAt) {
    requireStatus(TransactionStatus::Completed, "pay for");
    payment_->processPayment(method, paidAt);
}

long long ParkingTransaction::calculateDuration() const {
    if (!entryTime_ || !exitTime_) {
        throw InvalidSessionStateException("Transaction #" + std::to_string(transactionId_) +
                                           " has no exit time yet, so it has no final duration");
    }
    return (*exitTime_ - *entryTime_).count();
}

FeeBreakdown ParkingTransaction::calculateFee(const ParkingFeeStrategy& strategy, TimePoint until) const {
    if (status_ == TransactionStatus::Completed && fee_) {
        return *fee_;
    }
    requireStatus(TransactionStatus::Active, "estimate the fee of");
    return strategy.calculateFee(*entryTime_, until);
}

void ParkingTransaction::displayTransaction(std::ostream& out) const {
    out << "Transaction #" << transactionId_ << "  " << vehicle_->getNumberPlate() << " (" << vehicle_->getVehicleType()
        << ")  slot " << slotNumber_ << "  " << toString(status_);
    if (entryTime_) {
        out << "\n    entry: " << timeutil::formatDisplay(*entryTime_);
    }
    if (exitTime_) {
        out << "\n    exit:  " << timeutil::formatDisplay(*exitTime_) << "  (" << calculateDuration()
            << " s = billed minutes)";
    }
    if (fee_) {
        out << std::fixed << std::setprecision(2) << "\n    fee:   base " << fee_->baseMinutes << " x Rs "
            << fee_->baseRate << " = " << fee_->baseAmount << ", peak " << fee_->peakMinutes << " x Rs "
            << fee_->peakRate << " = " << fee_->peakAmount << ", total Rs " << fee_->totalAmount;
    }
    if (payment_) {
        out << "\n    ";
        payment_->displayPaymentDetails(out);
    }
}

TransactionRecord ParkingTransaction::toRecord() const {
    TransactionRecord record;
    record.transactionId = transactionId_;
    record.numberPlate = vehicle_->getNumberPlate();
    record.vehicleType = vehicle_->getVehicleType();
    record.slotNumber = slotNumber_;
    record.status = toString(status_);
    record.entryTime = entryTime_.value_or(TimePoint{});
    record.exitTime = exitTime_;
    record.fee = fee_;
    if (payment_) {
        record.paymentMethod = toString(payment_->getPaymentMethod());
        record.paymentStatus = toString(payment_->getPaymentStatus());
        record.paymentTime = payment_->getPaymentTime();
    }
    return record;
}

ParkingTransaction ParkingTransaction::fromRecord(const TransactionRecord& record,
                                                  std::shared_ptr<const Vehicle> vehicle) {
    const auto status = parseTransactionStatus(record.status);
    if (!status) {
        throw ValidationException("Unknown transaction status '" + record.status + "'");
    }
    if (*status == TransactionStatus::Active && record.exitTime) {
        throw ValidationException("An ACTIVE transaction cannot have an exit time");
    }
    if (*status != TransactionStatus::Active && !record.exitTime) {
        throw ValidationException("A " + record.status + " transaction needs an exit time");
    }
    if (record.exitTime && *record.exitTime < record.entryTime) {
        throw ValidationException("Exit time is before entry time");
    }

    ParkingTransaction transaction(record.transactionId, std::move(vehicle), record.slotNumber);
    transaction.status_ = *status;
    transaction.entryTime_ = record.entryTime;
    transaction.exitTime_ = record.exitTime;
    transaction.fee_ = record.fee;
    if (!record.paymentMethod.empty()) {
        if (*status != TransactionStatus::Completed) {
            throw ValidationException("Only a COMPLETED transaction can have a payment");
        }
        const double amount = record.fee ? record.fee->totalAmount : 0.0;
        transaction.payment_ = Payment::restore(record.transactionId, record.transactionId, amount,
                                                parsePaymentMethod(record.paymentMethod),
                                                parsePaymentStatus(record.paymentStatus), record.paymentTime);
    }
    return transaction;
}

}  // namespace parking
