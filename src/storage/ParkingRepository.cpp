#include "storage/ParkingRepository.hpp"

#include <algorithm>

namespace parking {

std::optional<TransactionRecord> ParkingRepository::findTransactionById(int transactionId) {
    const auto records = loadTransactions();
    auto it = std::find_if(records.begin(), records.end(),
                           [transactionId](const TransactionRecord& r) { return r.transactionId == transactionId; });
    if (it == records.end()) {
        return std::nullopt;
    }
    return *it;
}

std::vector<TransactionRecord> ParkingRepository::getParkingHistory(const std::string& numberPlate) {
    std::vector<TransactionRecord> history;
    for (const auto& record : loadTransactions()) {
        if (numberPlate.empty() || record.numberPlate == numberPlate) {
            history.push_back(record);
        }
    }
    return history;
}

}  // namespace parking
