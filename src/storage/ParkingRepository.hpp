#pragma once

#include <optional>
#include <string>
#include <vector>

#include "storage/TransactionRecord.hpp"

namespace parking {

// Abstract storage for parking records. The rest of the core depends only on
// this interface, so the CSV file can be swapped for MySQL (or anything else)
// without touching ParkingLot or the CLI.
class ParkingRepository {
public:
    virtual ~ParkingRepository() = default;

    // Every stored transaction, oldest first.
    virtual std::vector<TransactionRecord> loadTransactions() = 0;
    // Inserts a new transaction or updates an existing one (matched by id).
    virtual void saveTransaction(const TransactionRecord& record) = 0;
    // Human-readable location, e.g. "CSV file parking_data.csv".
    virtual std::string describe() const = 0;

    // Default implementations work for any backend; a backend may override
    // them with something faster (e.g. an indexed SQL query).
    virtual std::optional<TransactionRecord> findTransactionById(int transactionId);
    virtual std::vector<TransactionRecord> getParkingHistory(const std::string& numberPlate);
    // Non-fatal problems found while loading (e.g. skipped malformed rows).
    virtual std::vector<std::string> getWarnings() const { return {}; }
};

}  // namespace parking
