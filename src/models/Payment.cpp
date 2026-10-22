#include "models/Payment.hpp"

#include <iomanip>
#include <ostream>

#include "exceptions/ParkingException.hpp"
#include "util/Validation.hpp"

namespace parking {

std::string toString(PaymentMethod method) {
    switch (method) {
        case PaymentMethod::Cash: return "CASH";
        case PaymentMethod::Upi: return "UPI";
        case PaymentMethod::Card: return "CARD";
    }
    return "CASH";
}

std::string toString(PaymentStatus status) {
    return status == PaymentStatus::Success ? "SUCCESS" : "PENDING";
}

PaymentMethod parsePaymentMethod(const std::string& text) {
    if (text == "CASH") return PaymentMethod::Cash;
    if (text == "UPI") return PaymentMethod::Upi;
    if (text == "CARD") return PaymentMethod::Card;
    throw ValidationException("Unknown payment method '" + text + "' (expected CASH, UPI or CARD)");
}

PaymentStatus parsePaymentStatus(const std::string& text) {
    if (text == "SUCCESS") return PaymentStatus::Success;
    if (text == "PENDING") return PaymentStatus::Pending;
    throw ValidationException("Unknown payment status '" + text + "'");
}

Payment::Payment(int paymentId, int transactionId, double amount)
    : paymentId_(paymentId),
      transactionId_(transactionId),
      amount_(requireInRange(amount, 0.0, 1.0e9, "Payment amount")) {}

void Payment::processPayment(PaymentMethod method, TimePoint paidAt) {
    if (status_ == PaymentStatus::Success) {
        throw InvalidSessionStateException("Payment #" + std::to_string(paymentId_) + " was already processed",
                                           "ALREADY_PAID");
    }
    method_ = method;
    paidAt_ = paidAt;
    status_ = PaymentStatus::Success;
}

Payment Payment::restore(int paymentId, int transactionId, double amount, PaymentMethod method,
                         PaymentStatus status, std::optional<TimePoint> paidAt) {
    Payment payment(paymentId, transactionId, amount);
    payment.method_ = method;
    payment.status_ = status;
    payment.paidAt_ = paidAt;
    return payment;
}

void Payment::displayPaymentDetails(std::ostream& out) const {
    out << "Payment #" << paymentId_ << " for transaction #" << transactionId_ << ": Rs " << std::fixed
        << std::setprecision(2) << amount_ << " via " << toString(method_) << " - " << toString(status_);
    if (paidAt_) {
        out << " at " << timeutil::formatDisplay(*paidAt_);
    }
}

}  // namespace parking
