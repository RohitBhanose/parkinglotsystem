#pragma once

#include <optional>
#include <string>
#include <vector>

#include "models/Payment.hpp"
#include "services/ParkingLot.hpp"
#include "storage/ParkingRepository.hpp"

namespace parking {

// Keeps a ParkingLot and a ParkingRepository in step: loads saved records
// into the lot at start-up and saves every entry/exit/cancel right after the
// lot accepts it. Works with any ParkingRepository (CSV or MySQL).
class ParkingRecordManager {
public:
    ParkingRecordManager(ParkingLot& lot, ParkingRepository& repository);

    // Loads every stored transaction into the lot. Returns how many were loaded.
    // Throws StorageException (naming the record) if the data is inconsistent,
    // e.g. two active sessions in the same slot.
    std::size_t loadTransactions();
    void saveTransaction(const ParkingTransaction& transaction);
    std::optional<ParkingTransaction> findTransactionById(int transactionId) const;
    std::vector<ParkingTransaction> getParkingHistory(const std::string& numberPlate = "") const;

    ParkingTransaction checkIn(const std::string& numberPlate, const std::string& vehicleType, TimePoint entryTime);
    ParkingTransaction checkOut(const std::string& numberPlate, TimePoint exitTime, PaymentMethod method);
    ParkingTransaction cancel(const std::string& numberPlate, TimePoint cancelTime);

private:
    ParkingLot& lot_;
    ParkingRepository& repository_;
};

}  // namespace parking
