#include "services/ParkingRecordManager.hpp"

#include "exceptions/ParkingException.hpp"

namespace parking {

ParkingRecordManager::ParkingRecordManager(ParkingLot& lot, ParkingRepository& repository)
    : lot_(lot), repository_(repository) {}

std::size_t ParkingRecordManager::loadTransactions() {
    const auto records = repository_.loadTransactions();
    for (const auto& record : records) {
        try {
            lot_.restoreTransaction(record);
        } catch (const ParkingException& e) {
            throw StorageException(repository_.describe() + ": transaction #" + std::to_string(record.transactionId) +
                                   " (" + record.numberPlate + ") cannot be loaded: " + e.what());
        }
    }
    return records.size();
}

void ParkingRecordManager::saveTransaction(const ParkingTransaction& transaction) {
    repository_.saveTransaction(transaction.toRecord());
}

std::optional<ParkingTransaction> ParkingRecordManager::findTransactionById(int transactionId) const {
    return lot_.findTransactionById(transactionId);
}

std::vector<ParkingTransaction> ParkingRecordManager::getParkingHistory(const std::string& numberPlate) const {
    return lot_.getParkingHistory(numberPlate);
}

ParkingTransaction ParkingRecordManager::checkIn(const std::string& numberPlate, const std::string& vehicleType,
                                                 TimePoint entryTime) {
    const auto vehicle = lot_.registerVehicle(numberPlate, vehicleType);
    ParkingTransaction transaction = lot_.parkVehicle(vehicle, entryTime);
    saveTransaction(transaction);
    return transaction;
}

ParkingTransaction ParkingRecordManager::checkOut(const std::string& numberPlate, TimePoint exitTime,
                                                  PaymentMethod method) {
    ParkingTransaction transaction = lot_.removeVehicle(numberPlate, exitTime, method);
    saveTransaction(transaction);
    return transaction;
}

ParkingTransaction ParkingRecordManager::cancel(const std::string& numberPlate, TimePoint cancelTime) {
    ParkingTransaction transaction = lot_.cancelParking(numberPlate, cancelTime);
    saveTransaction(transaction);
    return transaction;
}

}  // namespace parking
