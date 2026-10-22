#pragma once

namespace parking {

// Result of a fee calculation - the same fields parkinglot.c used to print.
//
// Billing unit: the original C program bills every real second as one
// "minute" (a deliberate demo time-compression), so `*Minutes` here count
// seconds of real parking time. This is preserved unchanged.
struct FeeBreakdown {
    long long totalMinutes = 0;
    long long baseMinutes = 0;
    long long peakMinutes = 0;
    double baseRate = 0.0;    // Rs per billed minute outside the peak window
    double peakRate = 0.0;    // Rs per billed minute inside the peak window
    double baseAmount = 0.0;
    double peakAmount = 0.0;
    double totalAmount = 0.0;

    bool isRushHour() const { return peakMinutes > 0; }
};

}  // namespace parking
