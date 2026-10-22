#pragma once

#include <iosfwd>
#include <optional>
#include <string>

#include "util/TimeUtils.hpp"

namespace parking {

enum class PaymentMethod { Cash, Upi, Card };
enum class PaymentStatus { Pending, Success };

std::string toString(PaymentMethod method);
std::string toString(PaymentStatus status);
// Both throw ValidationException for an unknown value.
PaymentMethod parsePaymentMethod(const std::string& text);
PaymentStatus parsePaymentStatus(const std::string& text);

// Records the payment for one completed parking transaction.
//
// There is no online payment gateway in this project: processPayment() records
// that the attendant collected the amount (cash, or via the static payment QR
// image the UI shows). It does not verify any bank or UPI transfer.
class Payment {
public:
    Payment(int paymentId, int transactionId, double amount);

    // Pending -> Success. Throws InvalidSessionStateException if already paid.
    void processPayment(PaymentMethod method, TimePoint paidAt);

    // Rebuilds a payment read back from storage.
    static Payment restore(int paymentId, int transactionId, double amount, PaymentMethod method,
                           PaymentStatus status, std::optional<TimePoint> paidAt);

    int getPaymentId() const { return paymentId_; }
    int getTransactionId() const { return transactionId_; }
    double getAmount() const { return amount_; }
    PaymentMethod getPaymentMethod() const { return method_; }
    PaymentStatus getPaymentStatus() const { return status_; }
    std::optional<TimePoint> getPaymentTime() const { return paidAt_; }

    void displayPaymentDetails(std::ostream& out) const;

private:
    int paymentId_;
    int transactionId_;
    double amount_;
    PaymentMethod method_ = PaymentMethod::Cash;
    PaymentStatus status_ = PaymentStatus::Pending;
    std::optional<TimePoint> paidAt_;
};

}  // namespace parking
